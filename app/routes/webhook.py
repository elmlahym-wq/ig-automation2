import hashlib
import hmac
import logging
import os
import json
import re
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.exc import IntegrityError

from app import instagram
from app.database import SessionLocal
from app.models import Campaign, ProcessedComment, get_credentials

log = logging.getLogger("webhook")
router = APIRouter()


@router.get("/webhook/instagram")
def verify(mode: str = Query(None, alias="hub.mode"), token: str = Query(None, alias="hub.verify_token"),
           challenge: str = Query(None, alias="hub.challenge")):
    expected = os.getenv("WEBHOOK_VERIFY_TOKEN")
    # bytes compare: str compare raises TypeError (-> 500) on non-ASCII input
    if mode == "subscribe" and challenge is not None and expected and hmac.compare_digest(
            (token or "").encode("utf-8"), expected.encode("utf-8")):
        return PlainTextResponse(challenge)
    raise HTTPException(403, "Verification failed")


def _valid_signature(body: bytes, header: str | None) -> bool:
    secret = os.getenv("FACEBOOK_APP_SECRET", "")
    if not secret or not header or not header.startswith("sha256="):
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest.encode(), header.split("=", 1)[1].encode("utf-8"))


@router.post("/webhook/instagram")
async def receive(request: Request, background: BackgroundTasks):
    # Reject oversized payloads BEFORE reading them into memory:
    # the signature check protects against forgery, not against resource exhaustion.
    _max = 256_000
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > _max:
        raise HTTPException(413, "Payload too large")
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > _max:
            raise HTTPException(413, "Payload too large")
        body.extend(chunk)
    body = bytes(body)
    if not _valid_signature(body, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(403, "Invalid signature")
    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(400, "Invalid JSON payload")
    if not isinstance(payload, dict) or not isinstance(payload.get("entry", []), list):
        raise HTTPException(400, "Invalid webhook structure")
    events = []
    for entry in payload.get("entry", []):
        if not isinstance(entry, dict) or not isinstance(entry.get("changes", []), list):
            raise HTTPException(400, "Invalid webhook structure")
        for change in entry.get("changes", []):
            if not isinstance(change, dict) or not isinstance(change.get("value", {}), dict):
                raise HTTPException(400, "Invalid webhook structure")
            if change.get("field") == "comments":
                events.append(change.get("value", {}))
    for event in events:
        background.add_task(handle_comment, event)
    return {"status": "received"}  # respond fast; work happens in background


def handle_comment(v: dict):
    comment_id, text = v.get("id"), (v.get("text") or "")
    author = v.get("from") or {}
    media = v.get("media") or {}
    if not isinstance(author, dict) or not isinstance(media, dict) or not isinstance(text, str):
        return
    post_id = media.get("id")
    if not (re.fullmatch(r"\d+(?:_\d+)?", str(comment_id or "")) and re.fullmatch(r"\d+(?:_\d+)?", str(post_id or ""))):
        return
    db = SessionLocal()
    try:
        creds = get_credentials(db)
        if author.get("id") and author.get("id") == creds["ig_account_id"]:
            return  # ignore our own replies (prevents loops)
        text_l = text.lower()
        campaign = next((c for c in db.query(Campaign).filter_by(post_id=str(post_id), active=True).all()
                         if any(k in text_l for k in c.keyword_list)), None)
        if not campaign:
            return
        # Deduplication: unique constraint makes this atomic
        record = ProcessedComment(comment_id=comment_id, campaign_id=campaign.id, status="processing")
        db.add(record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            log.info("Comment %s already processed", comment_id)
            return
        if not creds["access_token"] or not creds["ig_account_id"]:
            record.status = "error: credentials not configured"
            db.commit()
            return
        username = author.get("username", "")
        fmt = lambda s: s.replace("{username}", username)
        results = []
        for label, fn in (
            ("reply", lambda: instagram.reply_to_comment(comment_id, fmt(campaign.comment_reply), creds["access_token"])),
            ("dm", lambda: instagram.send_dm(creds["ig_account_id"], fmt(campaign.dm_message),
                                             creds["access_token"], comment_id=comment_id)),
        ):
            try:
                fn()
                results.append(f"{label}:ok")
            except Exception:  # one failure should not block the other action
                log.error("Instagram %s action failed", label)
                results.append(f"{label}:error")
        record.status = " ".join(results)
        db.commit()
    finally:
        db.close()
