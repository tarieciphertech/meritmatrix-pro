"""Secure provisioning and first-time activation for guardian phone accounts."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission, _permission_names, SYSTEM_ADMIN_PERMISSION
from app.database import get_db
from app.models.guardian import Guardian
from app.models.guardian_activation import GuardianActivation
from app.models.role import Role
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.security import hash_password, verify_password, DUMMY_PASSWORD_HASH, WeakPasswordError
from app.utils.errors import AppError, ConflictError, NotFoundError, UnauthorizedError

router = APIRouter(prefix="/api/v1/guardian-accounts", tags=["guardian-accounts"])


def _phone(value: str) -> str:
    value = "".join(ch for ch in value.strip() if ch.isdigit() or ch == "+")
    if not value or value == "+" or value.count("+") > 1 or ("+" in value and not value.startswith("+")):
        raise AppError("Enter a valid phone number.", code="INVALID_PHONE", status_code=422)
    return value


def _verify_school_access(db: Session, user: User, guardian: Guardian) -> None:
    if SYSTEM_ADMIN_PERMISSION in _permission_names(user):
        return
    from app.services.user_school_service import UserSchoolService
    if not UserSchoolService(db).is_user_member_of_school(user.id, guardian.school_id):
        from app.utils.errors import ForbiddenError
        raise ForbiddenError("You do not have access to this school.", code="SCHOOL_ACCESS_DENIED")


class ActivationResponse(BaseModel):
    guardian_name: str
    phone: str
    activation_code: str
    expires_at: datetime
    instructions: str


class ActivateRequest(BaseModel):
    activation_code: str = Field(min_length=12, max_length=128)
    password: str = Field(min_length=8, max_length=128)


class ActivationComplete(BaseModel):
    message: str


@router.post("/{guardian_id}/create", response_model=ActivationResponse, status_code=201)
def create_guardian_account(
    guardian_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("guardians.update")),
):
    """Provision a disabled account. Admin must verify guardian identity in person before sharing code."""
    guardian = db.get(Guardian, guardian_id)
    if guardian is None or not guardian.is_active:
        raise NotFoundError("Active guardian record not found.", code="GUARDIAN_NOT_FOUND")
    _verify_school_access(db, admin, guardian)

    users = UserRepository(db)
    if db.execute(select(User).where(User.guardian_id == guardian.id)).scalar_one_or_none():
        raise ConflictError("This guardian already has a login account.", code="GUARDIAN_ACCOUNT_EXISTS")

    phone = _phone(guardian.phone)
    existing = users.get_by_phone(phone)
    if existing is not None:
        raise ConflictError("This phone number is already attached to another account.", code="PHONE_ALREADY_REGISTERED")

    # Random placeholder password; the account stays disabled until the guardian
    # redeems the one-time code and chooses a password.
    placeholder = secrets.token_urlsafe(48)
    user = User(
        email=None, phone=phone, guardian_id=guardian.id,
        password_hash=hash_password(placeholder),
        first_name=guardian.first_name, last_name=guardian.last_name,
        is_active=False, is_verified=False,
    )
    role = db.execute(select(Role).where(Role.name == "GUARDIAN")).scalar_one_or_none()
    if role is None:
        role = Role(name="GUARDIAN", description="Guardian portal access")
        db.add(role)
        db.flush()
    user.roles.append(role)
    db.add(user)
    db.flush()

    raw_code = secrets.token_urlsafe(24)
    expires = datetime.now(timezone.utc) + timedelta(hours=24)
    activation = GuardianActivation(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_code.encode("utf-8")).hexdigest(),
        expires_at=expires,
        created_by_user_id=admin.id,
    )
    db.add(activation)
    db.commit()
    return ActivationResponse(
        guardian_name=f"{guardian.first_name} {guardian.last_name}".strip(),
        phone=phone,
        activation_code=raw_code,
        expires_at=expires,
        instructions="Verify the guardian's identity in person before sharing this one-time code. It expires in 24 hours and can only be used once.",
    )


@router.post("/activate", response_model=ActivationComplete)
def activate_guardian_account(
    payload: ActivateRequest,
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(payload.activation_code.strip().encode("utf-8")).hexdigest()
    activation = db.execute(
        select(GuardianActivation).where(GuardianActivation.token_hash == token_hash).with_for_update()
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if activation is None or activation.used_at is not None:
        verify_password(payload.password, DUMMY_PASSWORD_HASH)
        raise UnauthorizedError("Activation code is invalid or expired.", code="INVALID_ACTIVATION_CODE")
    expiry = activation.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry <= now:
        raise UnauthorizedError("Activation code is invalid or expired.", code="INVALID_ACTIVATION_CODE")

    user = db.get(User, activation.user_id)
    if user is None or user.is_active:
        raise UnauthorizedError("Activation code is invalid or expired.", code="INVALID_ACTIVATION_CODE")
    try:
        user.password_hash = hash_password(payload.password)
    except WeakPasswordError as exc:
        raise AppError(str(exc), code="WEAK_PASSWORD", status_code=422) from exc

    user.is_active = True
    user.is_verified = True
    activation.used_at = now
    db.commit()
    return ActivationComplete(message="Account activated. You can now sign in using your phone number and password.")
