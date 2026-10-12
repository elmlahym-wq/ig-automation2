"""Regression tests use an isolated database and mocked Instagram calls."""
import hashlib
import logging
import hmac
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

_TEMP = tempfile.TemporaryDirectory()
os.environ['DATABASE_URL'] = f"sqlite:///{Path(_TEMP.name) / 'test.db'}"

from fastapi.testclient import TestClient
from app.main import app
from app import instagram
from app.database import Base, SessionLocal, engine
from app.models import Campaign, Config, ProcessedComment
from app.routes import auth, webhook
logging.getLogger("httpx").setLevel(logging.WARNING)


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            'DASHBOARD_PASSWORD': 'test-only-password',
            'DASHBOARD_USER': 'admin',
            'FACEBOOK_APP_SECRET': 'test-only-app-secret',
            'WEBHOOK_VERIFY_TOKEN': 'test-only-verify-token',
            'INSTAGRAM_ACCESS_TOKEN': '',
            'INSTAGRAM_BUSINESS_ACCOUNT_ID': '',
            'APP_ORIGIN': 'http://testserver',
        })
        self.environment.start()
        auth._fails.clear()
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        self.client = TestClient(app)
        self.credentials = ('admin', 'test-only-password')

    def tearDown(self):
        self.client.close()
        self.environment.stop()

    def signature(self, body):
        return 'sha256=' + hmac.new(b'test-only-app-secret', body, hashlib.sha256).hexdigest()

    def test_no_password_fails_closed_even_locally(self):
        with patch.dict(os.environ, {'DASHBOARD_PASSWORD': ''}):
            self.assertEqual(self.client.get('/api/config').status_code, 503)
            self.assertEqual(self.client.get('/dashboard/campaigns').status_code, 503)
        self.assertEqual(self.client.get('/health').status_code, 200)

    def test_authentication_required_and_failure_rate_limited(self):
        self.assertEqual(self.client.get('/api/config').status_code, 401)
        for _ in range(9):
            self.assertEqual(self.client.get('/api/config', auth=('admin', 'wrong')).status_code, 401)
        self.assertEqual(self.client.get('/api/config', auth=self.credentials).status_code, 429)

    def test_credentials_not_returned_and_private_responses_not_cached(self):
        token = 'test-only-sensitive-token'
        self.client.put('/api/config', auth=self.credentials, json={'access_token': token})
        response = self.client.get('/api/config', auth=self.credentials)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['token_set'])
        self.assertNotIn(token, response.text)
        self.assertNotIn('token_hint', response.json())
        self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_docs_not_public(self):
        for path in ['/docs', '/redoc', '/openapi.json']:
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_dashboard_and_campaign_crud(self):
        self.assertEqual(self.client.get('/dashboard/campaigns', auth=self.credentials).status_code, 200)
        self.assertEqual(self.client.get('/dashboard/settings', auth=self.credentials).status_code, 200)
        body = {'name': 'Demo', 'post_id': '123', 'keywords': 'guide', 'comment_reply': 'Thanks', 'dm_message': 'Hello {username}'}
        response = self.client.post('/api/campaigns', json=body, auth=self.credentials)
        self.assertEqual(response.status_code, 201)
        cid = response.json()['id']
        self.assertFalse(self.client.post(f'/api/campaigns/{cid}/toggle', auth=self.credentials).json()['active'])
        self.assertEqual(self.client.delete(f'/api/campaigns/{cid}', auth=self.credentials).status_code, 204)

    def test_cross_origin_changes_rejected(self):
        response = self.client.put('/api/config', auth=self.credentials, json={}, headers={'Origin': 'https://untrusted.example'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.put('/api/config', auth=self.credentials, json={}, headers={'Origin': 'http://testserver'}).status_code, 200)

    def test_webhook_requires_signature(self):
        self.assertEqual(self.client.post('/webhook/instagram', json={}).status_code, 403)
        body = b'{"entry": []}'
        self.assertEqual(self.client.post('/webhook/instagram', content=body, headers={'X-Hub-Signature-256': self.signature(body)}).status_code, 200)
        self.assertFalse(webhook._valid_signature(body, 'sha256=wrong'))

    def test_webhook_streaming_limit(self):
        response = self.client.post('/webhook/instagram', content=iter([b'x' * 128000, b'x' * 128001]))
        self.assertEqual(response.status_code, 413)

    def test_signed_invalid_json_and_structure(self):
        for body in [b'{', b'[]', b'{"entry": [null]}', b'{"entry": [{"changes": [null]}]}']:
            response = self.client.post('/webhook/instagram', content=body, headers={'X-Hub-Signature-256': self.signature(body)})
            self.assertEqual(response.status_code, 400)

    def test_webhook_verification(self):
        response = self.client.get('/webhook/instagram', params={'hub.mode': 'subscribe', 'hub.verify_token': 'test-only-verify-token', 'hub.challenge': 'example-challenge'})
        self.assertEqual(response.text, 'example-challenge')
        self.assertEqual(self.client.get('/webhook/instagram').status_code, 403)

    def test_graph_credentials_in_header_and_not_logs(self):
        import httpx
        token = 'test-only-sensitive-token'
        response = httpx.Response(200, json={'access_token': token}, request=httpx.Request('GET', 'https://example.com'))
        with patch('app.instagram.httpx.get', return_value=response) as send, self.assertLogs('instagram', level='INFO') as logs:
            instagram._request('GET', '123', token)
        self.assertEqual(send.call_args.kwargs['headers']['Authorization'], f'Bearer {token}')
        self.assertNotIn('access_token', send.call_args.kwargs['params'])
        self.assertNotIn(token, str(logs.output))

    def test_graph_error_message_redacted(self):
        import httpx
        response = httpx.Response(400, json={'error': {'message': 'test-only-sensitive-token', 'code': 190}})
        with patch('app.instagram._send', return_value=response):
            with self.assertRaises(instagram.InstagramError) as error:
                instagram._request('POST', '123/replies', 'test-only-token')
        self.assertNotIn('test-only-sensitive-token', str(error.exception))

    def test_duplicate_comment_sends_only_once(self):
        with SessionLocal() as db:
            db.add(Config(access_token='test-only-token', ig_account_id='456'))
            db.add(Campaign(post_id='123', keywords='guide', comment_reply='Thanks', dm_message='Hello {username}'))
            db.commit()
        value = {'id': '789', 'text': 'GUIDE please', 'media': {'id': '123'}, 'from': {'id': '100', 'username': 'example-user'}}
        with patch('app.instagram.reply_to_comment') as reply, patch('app.instagram.send_dm') as dm:
            webhook.handle_comment(value)
            webhook.handle_comment(value)
        self.assertEqual(reply.call_count, 1)
        self.assertEqual(dm.call_count, 1)
        with SessionLocal() as db:
            self.assertEqual(db.query(ProcessedComment).count(), 1)

    def test_environment_token_takes_priority(self):
        from app.models import get_credentials
        with SessionLocal() as db:
            db.add(Config(access_token='test-only-legacy-token'))
            db.commit()
            with patch.dict(os.environ, {'INSTAGRAM_ACCESS_TOKEN': 'test-only-env-token'}):
                self.assertEqual(get_credentials(db)['access_token'], 'test-only-env-token')


if __name__ == '__main__':
    unittest.main()
