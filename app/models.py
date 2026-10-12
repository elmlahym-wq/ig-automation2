import os
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.database import Base


def _utcnow():
    """Naive UTC timestamp (SQLite- and Postgres-compatible, not deprecated)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Config(Base):
    __tablename__ = "config"
    id = Column(Integer, primary_key=True)
    access_token = Column(Text, default="")
    page_id = Column(String(64), default="")
    ig_account_id = Column(String(64), default="")
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"
    id = Column(Integer, primary_key=True)
    name = Column(String(120), default="")
    post_id = Column(String(64), index=True, nullable=False)
    keywords = Column(Text, nullable=False)  # comma-separated
    comment_reply = Column(Text, nullable=False)
    dm_message = Column(Text, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)
    owner = Column(String(64), nullable=False, default="")

    @property
    def keyword_list(self):
        return [k.strip().lower() for k in (self.keywords or "").split(",") if k.strip()]


class ProcessedComment(Base):
    __tablename__ = "processed_comments"
    id = Column(Integer, primary_key=True)
    comment_id = Column(String(64), unique=True, index=True, nullable=False)
    campaign_id = Column(Integer, nullable=True)
    status = Column(String(255), default="")
    processed_at = Column(DateTime, default=_utcnow)


def get_credentials(db):
    """Environment credentials take priority over legacy dashboard storage."""
    c = db.query(Config).first()
    return {
        "access_token": (os.getenv("INSTAGRAM_ACCESS_TOKEN", "") or (c.access_token if c else "")),
        "page_id": (c.page_id if c else "") or "",
        "ig_account_id": (os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "") or (c.ig_account_id if c else "")),
    }
