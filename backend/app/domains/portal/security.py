"""邀请码与门户令牌工具：明文仅短暂返回，持久化只存哈希。"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta


def hash_secret(value: str, *, pepper: str = "bidplat-m6-portal") -> str:
    return hmac.new(pepper.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def generate_invite_code() -> tuple[str, str, str]:
    """返回 (raw_code, hash, masked)。"""
    raw = secrets.token_urlsafe(24)
    masked = f"{raw[:4]}****{raw[-4:]}"
    return raw, hash_secret(raw), masked


def generate_portal_access_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    return raw, hash_secret(raw)


def default_invite_expiry(*, now: datetime | None = None, days: int = 14) -> datetime:
    base = now or datetime.now(UTC)
    return base + timedelta(days=days)


def default_portal_token_expiry(*, now: datetime | None = None, minutes: int = 30) -> datetime:
    base = now or datetime.now(UTC)
    return base + timedelta(minutes=minutes)
