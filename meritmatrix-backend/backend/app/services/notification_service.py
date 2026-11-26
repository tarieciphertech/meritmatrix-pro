"""Create in-app notifications for guardians linked to affected students."""
from datetime import date
from typing import Any, Iterable
import uuid

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.guardian import Guardian
from app.models.student import Student
from app.models.student_guardian import StudentGuardian
from app.models.user import User
from app.models.role import Role
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
        # Only guardian/legacy-parent identities may receive school-family
        # notifications. Email equality alone must not notify a staff account
        # that happens to share a guardian record's email address.
        users = (
            db.query(User)
            .join(User.roles)
            .filter(
                User.is_active.is_(True),
                Role.name.in_({"GUARDIAN", "PARENT"}),
                or_(*identity_filters),
            )
            .distinct()
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

def notify_users(
    db: Session,
    *,
    school_id: uuid.UUID,
    recipient_user_ids: Iterable[uuid.UUID],
    notification_type: str,
    title: str,
    message: str,
    data: dict[str, Any] | None = None,
    exclude_user_id: uuid.UUID | None = None,
) -> int:
    """Create school-scoped in-app notifications for active school members."""
    from app.models.user_school import UserSchool

    target_ids = {uuid.UUID(str(value)) for value in recipient_user_ids if value is not None}
    if exclude_user_id:
        target_ids.discard(uuid.UUID(str(exclude_user_id)))
    if not target_ids:
        return 0
    users = (
        db.query(User.id)
        .join(UserSchool, UserSchool.user_id == User.id)
        .filter(
            User.id.in_(target_ids),
            User.is_active.is_(True),
            UserSchool.school_id == school_id,
        )
        .distinct()
        .all()
    )
    for (user_id,) in users:
        db.add(UserNotification(
            recipient_user_id=user_id,
            school_id=school_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
        ))
    return len(users)


def notify_school_roles(
    db: Session,
    *,
    school_id: uuid.UUID,
    role_names: Iterable[str],
    notification_type: str,
    title: str,
    message: str,
    data: dict[str, Any] | None = None,
    exclude_user_id: uuid.UUID | None = None,
) -> int:
    """Notify active members of a school who hold one of the requested roles."""
    from app.models.user_school import UserSchool

    users = (
        db.query(User.id)
        .join(User.roles)
        .join(UserSchool, UserSchool.user_id == User.id)
        .filter(
            User.is_active.is_(True),
            UserSchool.school_id == school_id,
            Role.name.in_(set(role_names)),
        )
        .distinct()
        .all()
    )
    return notify_users(
        db,
        school_id=school_id,
        recipient_user_ids=[row[0] for row in users],
        notification_type=notification_type,
        title=title,
        message=message,
        data=data,
        exclude_user_id=exclude_user_id,
    )


def notify_teaching_staff(
    db: Session,
    *,
    school_id: uuid.UUID,
    class_subject_id: uuid.UUID,
    notification_type: str,
    title: str,
    message: str,
    data: dict[str, Any] | None = None,
    exclude_user_id: uuid.UUID | None = None,
    effective_on: date | None = None,
) -> int:
    """Notify linked teachers assigned to the class-subject on the relevant date."""
    from app.models.staff import Staff
    from app.models.teaching_assignment import TeachingAssignment

    relevant_date = effective_on or date.today()
    user_ids = (
        db.query(Staff.user_id)
        .join(TeachingAssignment, TeachingAssignment.staff_id == Staff.id)
        .filter(
            TeachingAssignment.school_id == school_id,
            TeachingAssignment.class_subject_id == class_subject_id,
            TeachingAssignment.is_active.is_(True),
            TeachingAssignment.start_date <= relevant_date,
            (TeachingAssignment.end_date.is_(None) | (TeachingAssignment.end_date >= relevant_date)),
            Staff.school_id == school_id,
            Staff.is_active.is_(True),
            Staff.employment_status == "active",
            Staff.user_id.isnot(None),
        )
        .distinct()
        .all()
    )
    return notify_users(
        db,
        school_id=school_id,
        recipient_user_ids=[row[0] for row in user_ids],
        notification_type=notification_type,
        title=title,
        message=message,
        data=data,
        exclude_user_id=exclude_user_id,
    )

