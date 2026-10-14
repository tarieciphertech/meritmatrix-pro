"""Read-only guardian portal endpoints.

New phone accounts use their bound guardian_id. Legacy email-linked accounts keep their existing access until migrated.
No caller-supplied guardian or school ID is trusted for discovery.
"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.database import get_db
from app.models.guardian import Guardian
from app.models.student import Student
from app.models.student_guardian import StudentGuardian
from app.models.user import User

router = APIRouter(prefix="/api/v1/guardian-portal", tags=["guardian-portal"])


@router.get("/students", response_model=List[dict])
def list_my_students(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return students linked to the bound guardian, with legacy email fallback."""
    if current_user.guardian_id:
        guardian_filter = Guardian.id == current_user.guardian_id
    elif current_user.email:
        guardian_filter = func.lower(func.trim(Guardian.email)) == current_user.email.strip().lower()
    else:
        return []

    rows = (
        db.query(Student, StudentGuardian, Guardian)
        .join(StudentGuardian, StudentGuardian.student_id == Student.id)
        .join(Guardian, Guardian.id == StudentGuardian.guardian_id)
        .filter(
            guardian_filter,
            Guardian.is_active.is_(True),
            Student.is_active.is_(True),
        )
        .order_by(Student.last_name.asc(), Student.first_name.asc())
        .all()
    )

    return [
        {
            "student_id": str(student.id),
            "student_number": student.student_number,
            "first_name": student.first_name,
            "middle_name": student.middle_name,
            "last_name": student.last_name,
            "status": student.status.value if hasattr(student.status, "value") else student.status,
            "school_id": str(student.school_id),
            "guardian_name": f"{guardian.first_name} {guardian.last_name}".strip(),
            "relationship_type": relationship.relationship_type.value
            if hasattr(relationship.relationship_type, "value")
            else relationship.relationship_type,
            "is_primary": relationship.is_primary,
            "receives_notifications": relationship.receives_notifications,
        }
        for student, relationship, guardian in rows
    ]
