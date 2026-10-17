"""User endpoints. All administrative operations enforce permissions server-side."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.assignment_access import deny_linked_staff_management
from app.auth.dependencies import get_current_active_user, require_permission
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.get("", response_model=List[UserResponse])
def list_users(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.read")),
):
    deny_linked_staff_management(db, current_user, "list platform user accounts")
    service = UserService(db)
    return service.list_users(limit=limit, offset=offset)


@router.post("", response_model=UserResponse, status_code=201)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.create")),
):
    deny_linked_staff_management(db, current_user, "create platform user accounts")
    service = UserService(db)
    user = service.create_user(payload)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def read_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.read")),
):
    deny_linked_staff_management(db, current_user, "read platform user accounts")
    service = UserService(db)
    return service.get_user(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.update")),
):
    deny_linked_staff_management(db, current_user, "update platform user accounts")
    service = UserService(db)
    user = service.update_user(user_id, payload)
    db.commit()
    db.refresh(user)
    return user
