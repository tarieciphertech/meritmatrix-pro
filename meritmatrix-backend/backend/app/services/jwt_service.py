"""
JWT access-token issuance and verification.

Access tokens are short-lived and carry only the minimal claims needed
to identify the session: subject (user id), token type, issued-at,
expiration, and a token identifier. No personal information is embedded
in the token payload.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt

from app.config import get_settings

ACCESS_TOKEN_TYPE = "access"


class TokenError(Exception):
    """Raised when a token is missing, malformed, expired, or of the wrong type."""


def create_access_token(user_id: uuid.UUID, *, extra_claims: Optional[dict] = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise TokenError("Invalid or expired token.") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise TokenError("Invalid token type.")

    return payload
