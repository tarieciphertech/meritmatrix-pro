"""
Authentication service.

Keeps all cryptographic and session logic out of route handlers:
    - authenticate_user()
    - create_access_token()
    - create_refresh_token()
    - rotate_refresh_token()
    - revoke_refresh_token()
    - revoke_user_sessions()
    - get_current_user()
"""
import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.services import jwt_service
from app.services.security import DUMMY_PASSWORD_HASH, verify_password
from app.utils.audit_events import AuditEvent
from app.utils.errors import UnauthorizedError

logger = logging.getLogger("meritmatrix.auth")

GENERIC_LOGIN_ERROR = "Invalid email or password."
GENERIC_REFRESH_ERROR = "Invalid or expired refresh token."


def _hash_token(raw_token: str) -> str:
    # Refresh tokens are high-entropy random values (not user-chosen secrets
    # like passwords), so a fast cryptographic hash is the correct tool here
    # — it gives us unlinkability from the raw token at rest without the
    # deliberate slowness that password hashing needs.
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _generate_raw_refresh_token() -> str:
    return secrets.token_urlsafe(64)


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.users = UserRepository(db)
        self.refresh_tokens = RefreshTokenRepository(db)

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    def authenticate_user(self, email: str, password: str) -> User:
        """Validate credentials. Raises UnauthorizedError with a generic
        message on any failure so callers can't distinguish 'no such user'
        from 'wrong password' from 'account inactive'."""
        user = self.users.get_by_email(email)

        if user is None:
            # Run a real hash verification against a dummy hash anyway, so
            # the response time for an unknown email is similar to a known
            # one — this reduces (does not eliminate) timing-based
            # user-enumeration.
            verify_password(password, DUMMY_PASSWORD_HASH)
            logger.info("Login failed: unknown email. event=%s", AuditEvent.LOGIN_FAILED)
            raise UnauthorizedError(GENERIC_LOGIN_ERROR, code="INVALID_CREDENTIALS")

        if not user.is_active or not verify_password(password, user.password_hash):
            logger.info(
                "Login failed for user_id=%s. event=%s", user.id, AuditEvent.LOGIN_FAILED
            )
            raise UnauthorizedError(GENERIC_LOGIN_ERROR, code="INVALID_CREDENTIALS")

        logger.info("Login succeeded for user_id=%s. event=%s", user.id, AuditEvent.LOGIN_SUCCESS)
        return user

    # ------------------------------------------------------------------
    # Token issuance
    # ------------------------------------------------------------------
    def create_access_token(self, user: User) -> str:
        return jwt_service.create_access_token(user.id)

    def create_refresh_token(
        self,
        user: User,
        *,
        family_id: Optional[uuid.UUID] = None,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[str, RefreshToken]:
        raw_token = _generate_raw_refresh_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            days=self.settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
        record = RefreshToken(
            user_id=user.id,
            token_hash=_hash_token(raw_token),
            family_id=family_id or uuid.uuid4(),
            expires_at=expires_at,
            user_agent=(user_agent or "")[:255] or None,
            ip_address=(ip_address or "")[:64] or None,
        )
        self.refresh_tokens.create(record)
        return raw_token, record

    def issue_token_pair(
        self,
        user: User,
        *,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[str, str]:
        access_token = self.create_access_token(user)
        raw_refresh, _record = self.create_refresh_token(
            user, user_agent=user_agent, ip_address=ip_address
        )
        return access_token, raw_refresh

    # ------------------------------------------------------------------
    # Refresh-token rotation
    # ------------------------------------------------------------------
    def rotate_refresh_token(
        self,
        raw_token: str,
        *,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[str, str, User]:
        """Validate and rotate a refresh token.

        Returns (new_access_token, new_raw_refresh_token, user).
        Raises UnauthorizedError on any invalid/expired/revoked/reused token.
        """
        token_hash = _hash_token(raw_token)

        # Catch any database errors during token lookup and convert to
        # UnauthorizedError so the API never returns a 500 for invalid tokens.
        try:
            record = self.refresh_tokens.get_by_hash(token_hash)
        except Exception:
            logger.warning("Database error during refresh token lookup. event=%s", AuditEvent.LOGIN_FAILED)
            raise UnauthorizedError(GENERIC_REFRESH_ERROR, code="INVALID_REFRESH_TOKEN")

        if record is None:
            raise UnauthorizedError(GENERIC_REFRESH_ERROR, code="INVALID_REFRESH_TOKEN")

        now = datetime.now(timezone.utc)

        if record.revoked_at is not None:
            # The token has already been rotated/revoked once before, yet is
            # being presented again: this looks like token theft/replay.
            # Revoke the entire rotation family and commit immediately so
            # this protective action persists even though we raise below.
            try:
                self.refresh_tokens.revoke_family(record.family_id)
                self.db.commit()
            except Exception:
                self.db.rollback()
            logger.warning(
                "Refresh token reuse detected, family revoked. family_id=%s event=%s",
                record.family_id,
                AuditEvent.TOKEN_REVOKED,
            )
            raise UnauthorizedError(
                "This refresh token has already been used. All sessions in "
                "this session family have been revoked for safety.",
                code="REFRESH_TOKEN_REUSE_DETECTED",
            )

        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at < now:
            raise UnauthorizedError(GENERIC_REFRESH_ERROR, code="REFRESH_TOKEN_EXPIRED")

        user = self.users.get_by_id(record.user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError(GENERIC_REFRESH_ERROR, code="INVALID_REFRESH_TOKEN")

        # Rotate: revoke the presented token, issue a fresh one in the same family.
        record.last_used_at = now
        self.refresh_tokens.revoke(record)
        new_raw_refresh, _new_record = self.create_refresh_token(
            user,
            family_id=record.family_id,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        new_access_token = self.create_access_token(user)

        logger.info(
            "Refresh token rotated for user_id=%s. event=%s", user.id, AuditEvent.TOKEN_REFRESH
        )
        return new_access_token, new_raw_refresh, user

    # ------------------------------------------------------------------
    # Revocation
    # ------------------------------------------------------------------
    def revoke_refresh_token(self, raw_token: str) -> None:
        token_hash = _hash_token(raw_token)
        try:
            record = self.refresh_tokens.get_by_hash(token_hash)
        except Exception:
            # Database error — treat as already revoked for logout idempotency.
            return
        if record is None or record.revoked_at is not None:
            # Logout is idempotent: an unknown or already-revoked token is
            # treated as "already logged out", not an error.
            return
        self.refresh_tokens.revoke(record)
        logger.info(
            "Refresh token revoked (logout) for user_id=%s. event=%s",
            record.user_id,
            AuditEvent.LOGOUT,
        )

    def revoke_user_sessions(self, user_id: uuid.UUID) -> None:
        self.refresh_tokens.revoke_all_for_user(user_id)
        logger.info(
            "All refresh sessions revoked for user_id=%s. event=%s",
            user_id,
            AuditEvent.TOKEN_REVOKED,
        )

    # ------------------------------------------------------------------
    # Current user resolution (used by the auth dependency)
    # ------------------------------------------------------------------
    def get_current_user(self, access_token: str) -> User:
        try:
            payload = jwt_service.decode_access_token(access_token)
        except jwt_service.TokenError as exc:
            raise UnauthorizedError(
                "Invalid or expired access token.", code="INVALID_ACCESS_TOKEN"
            ) from exc

        raw_user_id = payload.get("sub")
        if not raw_user_id:
            raise UnauthorizedError("Invalid access token.", code="INVALID_ACCESS_TOKEN")

        try:
            user_id = uuid.UUID(raw_user_id)
        except (ValueError, TypeError) as exc:
            raise UnauthorizedError(
                "Invalid access token.", code="INVALID_ACCESS_TOKEN"
            ) from exc

        user = self.users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid access token.", code="INVALID_ACCESS_TOKEN")

        return user
