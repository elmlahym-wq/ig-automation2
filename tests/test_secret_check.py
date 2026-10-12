"""Verify the working-tree guard catches secrets without echoing them."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

_SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/check_secrets.py'
_SPEC = importlib.util.spec_from_file_location('secret_check', _SCRIPT)
scanner = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(scanner)


class SecretCheckTests(unittest.TestCase):
    def check(self, name, content):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / name
            path.write_text(content)
            output = io.StringIO()
            with patch.object(scanner, 'ROOT', root), patch.object(scanner, 'candidates', return_value=[path]), contextlib.redirect_stdout(output):
                status = scanner.main()
            return status, output.getvalue()

    def test_empty_example_fields_allowed(self):
        status, _ = self.check('.env.example', 'DASHBOARD_PASSWORD=\nFACEBOOK_APP_SECRET=\nWEBHOOK_VERIFY_TOKEN=\n')
        self.assertEqual(status, 0)

    def test_literal_secret_blocked_without_printing_value(self):
        value = 'synthetic-sensitive-value'
        status, output = self.check('config.py', 'FACEBOOK_APP_SECRET="' + value + '"\n')
        self.assertEqual(status, 1)
        self.assertNotIn(value, output)

    def test_real_env_file_blocked(self):
        status, _ = self.check('.env.production', '')
        self.assertEqual(status, 1)

    def test_database_password_blocked(self):
        value = 'synthetic-sensitive-value'
        status, output = self.check('notes.md', 'postgresql://operator:' + value + '@db.invalid/database')
        self.assertEqual(status, 1)
        self.assertNotIn('synthetic-sensitive-value', output)
