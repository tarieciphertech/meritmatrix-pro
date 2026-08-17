"""Data-access layer for RefreshToken records."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, token: RefreshToken) -> RefreshToken:
        self.db.add(token)
        self.db.flush()
        return token

    def get_by_hash(self, token_hash: str) -> Optional[RefreshToken]:
        stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        return self.db.execute(stmt).scalar_one_or_none()

    def revoke(self, token: RefreshToken) -> None:
        token.revoked_at = datetime.now(timezone.utc)
        self.db.flush()

    def revoke_family(self, family_id: uuid.UUID) -> None:
        """Revoke every still-active token in a rotation family (reuse detected)."""
        stmt = select(RefreshToken).where(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at.is_(None),
        )
        now = datetime.now(timezone.utc)
        for token in self.db.execute(stmt).scalars().all():
            token.revoked_at = now
        self.db.flush()

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
        now = datetime.now(timezone.utc)
        for token in self.db.execute(stmt).scalars().all():
            token.revoked_at = now
        self.db.flush()
