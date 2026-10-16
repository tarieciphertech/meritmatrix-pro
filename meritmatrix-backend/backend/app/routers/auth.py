"""Authentication endpoints: login, refresh, logout, current-user, password change."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user, get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.services.security import WeakPasswordError, hash_password, verify_password
from app.utils.errors import AppError, UnauthorizedError

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _client_ip(request: Request) -> Optional[str]:
    return request.client.host if request.client else None


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    service = AuthService(db)

    user = service.authenticate_user(payload.identifier or str(payload.email or ""), payload.password)
    access_token, refresh_token = service.issue_token_pair(
        user,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        must_change_password=user.must_change_password,
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    service = AuthService(db)

    access_token, refresh_token, user = service.rotate_refresh_token(
        payload.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        must_change_password=user.must_change_password,
    )


@router.post("/change-password", response_model=TokenResponse)
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change a password and revoke all existing refresh sessions."""
    if not verify_password(payload.current_password, current_user.password_hash):
        raise UnauthorizedError(
            "The current password is incorrect.",
            code="CURRENT_PASSWORD_INVALID",
        )
    try:
        new_hash = hash_password(payload.new_password)
    except WeakPasswordError as exc:
        raise AppError(str(exc), code="WEAK_PASSWORD", status_code=422) from exc

    current_user.password_hash = new_hash
    current_user.must_change_password = False
    service = AuthService(db)
    service.revoke_user_sessions(current_user.id)
    access_token, refresh_token = service.issue_token_pair(
        current_user,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_ip(request),
    )
    db.commit()
    settings = get_settings()
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        must_change_password=False,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    service = AuthService(db)
    service.revoke_refresh_token(payload.refresh_token)
    db.commit()
    return None


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_active_user)):
    return current_user
