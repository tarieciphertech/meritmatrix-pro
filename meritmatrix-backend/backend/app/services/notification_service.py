"""Create in-app notifications for guardians linked to affected students."""
from typing import Any, Iterable
import uuid

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.guardian import Guardian
from app.models.student import Student
from app.models.student_guardian import StudentGuardian
from app.models.user import User
from app.models.user_notification import UserNotification


def notify_guardians(
    db: Session,
    *,
    school_id: uuid.UUID,
    student_ids: Iterable[uuid.UUID],
    notification_type: str,
    title: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> int:
    """Queue a notification for each active linked guardian account; caller commits."""
    target_ids = {uuid.UUID(str(value)) for value in student_ids if value is not None}
    if not target_ids:
        return 0

    links = (
        db.query(StudentGuardian.student_id, Guardian.id, Guardian.email)
        .join(Guardian, Guardian.id == StudentGuardian.guardian_id)
        .join(Student, Student.id == StudentGuardian.student_id)
        .filter(
            StudentGuardian.student_id.in_(target_ids),
            StudentGuardian.receives_notifications.is_(True),
            Guardian.school_id == school_id,
            Guardian.is_active.is_(True),
            Student.school_id == school_id,
            Student.is_active.is_(True),
        )
        .all()
    )
    if not links:
        return 0

    users_by_guardian: dict[uuid.UUID, list[User]] = {}
    for _student_id, guardian_id, guardian_email in links:
        if guardian_id in users_by_guardian:
            continue
        identity_filters = [User.guardian_id == guardian_id]
        if guardian_email and guardian_email.strip():
            identity_filters.append(func.lower(func.trim(User.email)) == guardian_email.strip().lower())
        users = (
            db.query(User)
            .filter(User.is_active.is_(True), or_(*identity_filters))
            .all()
        )
        users_by_guardian[guardian_id] = users

    count = 0
    base_data = data or {}
    seen: set[tuple[uuid.UUID, uuid.UUID]] = set()
    for student_id, guardian_id, _guardian_email in links:
        for user in users_by_guardian.get(guardian_id, []):
            key = (user.id, student_id)
            if key in seen:
                continue
            seen.add(key)
            db.add(UserNotification(
                recipient_user_id=user.id,
                school_id=school_id,
                student_id=student_id,
                notification_type=notification_type,
                title=title,
                message=message,
                data={**base_data, "student_id": str(student_id)},
            ))
            count += 1
    return count
