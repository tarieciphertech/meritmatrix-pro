"""
Development-only seed data.

Seeds the default permission set, default roles, role→permission
mappings, one demo user per role, a demo school, and associated
academic structure. This module refuses to run against a production
environment.

Usage:
    cd backend
    python -m app.seed
"""
import logging
import os
import secrets
import sys
from datetime import date

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User
from app.models.school import School
from app.models.academic_year import AcademicYear
from app.models.term import Term
from app.models.clazz import Class
from app.models.subject import Subject
from app.models.class_subject import ClassSubject
from app.models.user_school import UserSchool
from app.repositories.permission_repository import PermissionRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.repositories.school_repository import SchoolRepository
from app.services.security import hash_password

logger = logging.getLogger("meritmatrix.seed")

DEFAULT_PERMISSIONS: dict[str, str] = {
    # Milestone 2: Users & Authentication
    "users.read": "View user accounts",
    "users.create": "Create new user accounts",
    "users.update": "Update user accounts",
    "users.delete": "Deactivate user accounts",
    "roles.read": "View roles",
    "roles.create": "Create roles",
    "roles.update": "Update roles",
    "permissions.read": "View permissions",
    # Milestone 3: Schools & Academic Structure
    "schools.read": "View schools",
    "schools.create": "Create schools",
    "schools.update": "Update schools",
    "academic_years.read": "View academic years",
    "academic_years.create": "Create academic years",
    "academic_years.update": "Update academic years",
    "terms.read": "View terms",
    "terms.create": "Create terms",
    "terms.update": "Update terms",
    "classes.read": "View classes",
    "classes.create": "Create classes",
    "classes.update": "Update classes",
    "subjects.read": "View subjects",
    "subjects.create": "Create subjects",
    "subjects.update": "Update subjects",
    "class_subjects.read": "View class-subject assignments",
    "class_subjects.create": "Create class-subject assignments",
    "class_subjects.delete": "Remove class-subject assignments",
    # Milestone 4: People & Enrollment
    "students.read": "View students",
    "students.create": "Create students",
    "students.update": "Update students",
    "students.delete": "Archive students",
    "guardians.read": "View guardians",
    "guardians.create": "Create guardians",
    "guardians.update": "Update guardians",
    "guardians.delete": "Archive guardians",
    "student_guardians.read": "View student-guardian relationships",
    "student_guardians.create": "Create student-guardian relationships",
    "student_guardians.delete": "Remove student-guardian relationships",
    "staff.read": "View staff",
    "staff.create": "Create staff",
    "staff.update": "Update staff",
    "staff.delete": "Archive staff",
    "enrollments.read": "View enrollments",
    "enrollments.create": "Create enrollments",
    "enrollments.update": "Update enrollments",
    "attendance.read": "View class attendance registers",
    "attendance.create": "Record and update attendance registers",
    # System
    "system.admin": "Full platform administrative access (implies all other permissions)",
}

DEFAULT_ROLES: dict[str, str] = {
    "SUPER_ADMIN": "Complete platform access",
    "SCHOOL_ADMIN": "Manages a single school's students, staff, and academic data",
    "TEACHER": "Manages assigned classes, subjects, and marks",
    "PARENT": "Views linked children's academic records",
    "STUDENT": "Views their own academic records",
}

# Additional domain permissions (students, classes, results, etc.) are added
# in later milestones alongside those domains.
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "SUPER_ADMIN": list(DEFAULT_PERMISSIONS.keys()),
    # SCHOOL_ADMIN manages a single school's people and academic data.
    # Platform-level operations (schools.create/update, roles management,
    # users.delete, system.admin) remain reserved for SUPER_ADMIN.
    # School-scoped access is additionally enforced by membership checks.
    "SCHOOL_ADMIN": [
        "users.read", "users.create", "users.update", "roles.read",
        "schools.read",
        "academic_years.read", "academic_years.create", "academic_years.update",
        "terms.read", "terms.create", "terms.update",
        "classes.read", "classes.create", "classes.update",
        "subjects.read", "subjects.create", "subjects.update",
        "class_subjects.read", "class_subjects.create", "class_subjects.delete",
        "students.read", "students.create", "students.update", "students.delete",
        "guardians.read", "guardians.create", "guardians.update", "guardians.delete",
        "student_guardians.read", "student_guardians.create", "student_guardians.delete",
        "staff.read", "staff.create", "staff.update", "staff.delete",
        "enrollments.read", "enrollments.create", "enrollments.update",
        "attendance.read", "attendance.create",
    ],
    "TEACHER": ["users.read"],
    "PARENT": ["users.read"],
    "STUDENT": ["users.read"],
}

# Demo/dev users: one per role. Passwords are sourced from environment
# variables (SEED_<ROLE>_PASSWORD) so no real credential is ever
# hard-coded; if unset, a random password is generated per run and
# printed once to stdout (never persisted in plaintext, never logged).
DEMO_USERS: dict[str, dict[str, str]] = {
    "SUPER_ADMIN": {"email": "super.admin@meritmatrix.dev", "first_name": "Super", "last_name": "Admin"},
    "SCHOOL_ADMIN": {"email": "school.admin@meritmatrix.dev", "first_name": "School", "last_name": "Admin"},
    "TEACHER": {"email": "teacher@meritmatrix.dev", "first_name": "Demo", "last_name": "Teacher"},
    "PARENT": {"email": "parent@meritmatrix.dev", "first_name": "Demo", "last_name": "Parent"},
    "STUDENT": {"email": "student@meritmatrix.dev", "first_name": "Demo", "last_name": "Student"},
}


def seed_permissions(db: Session) -> dict[str, Permission]:
    repo = PermissionRepository(db)
    result: dict[str, Permission] = {}
    for name, description in DEFAULT_PERMISSIONS.items():
        existing = repo.get_by_name(name)
        if existing is None:
            existing = repo.create(Permission(name=name, description=description))
        result[name] = existing
    return result


def seed_roles(db: Session) -> dict[str, Role]:
    repo = RoleRepository(db)
    result: dict[str, Role] = {}
    for name, description in DEFAULT_ROLES.items():
        existing = repo.get_by_name(name)
        if existing is None:
            existing = repo.create(Role(name=name, description=description))
        result[name] = existing
    return result


def assign_role_permissions(db: Session) -> None:
    permission_repo = PermissionRepository(db)
    role_repo = RoleRepository(db)

    for role_name, permission_names in ROLE_PERMISSIONS.items():
        role = role_repo.get_by_name(role_name)
        if role is None:
            continue
        existing_names = {p.name for p in role.permissions}
        for permission_name in permission_names:
            if permission_name in existing_names:
                continue
            permission = permission_repo.get_by_name(permission_name)
            if permission is not None:
                role.permissions.append(permission)
    db.flush()


def seed_demo_users(db: Session) -> dict[str, tuple[User, str]]:
    """Create one demo user per role. Returns {role_name: (user, plaintext_password_used)}."""
    settings = get_settings()
    if settings.is_production:
        raise RuntimeError("Refusing to seed demo users when ENVIRONMENT=production.")

    user_repo = UserRepository(db)
    role_repo = RoleRepository(db)
    created: dict[str, tuple[User, str]] = {}

    for role_name, info in DEMO_USERS.items():
        existing = user_repo.get_by_email(info["email"])
        if existing is not None:
            continue

        env_var = f"SEED_{role_name}_PASSWORD"
        # Append a fixed digit+symbol suffix so the generated password
        # reliably satisfies minimum strength rules regardless of what
        # characters the random token happens to contain.
        password = os.environ.get(env_var) or f"{secrets.token_urlsafe(12)}-9!"

        user = User(
            email=info["email"].lower(),
            first_name=info["first_name"],
            last_name=info["last_name"],
            password_hash=hash_password(password),
            is_active=True,
            is_verified=True,
        )
        role = role_repo.get_by_name(role_name)
        if role is not None:
            user.roles.append(role)

        user_repo.create(user)
        created[role_name] = (user, password)

    return created


def seed_demo_school(db: Session) -> tuple:
    """Seed a demo school with academic structure for development.
    
    Returns:
        Tuple of (school, academic_year, terms, classes, subjects)
    """
    settings = get_settings()
    if settings.is_production:
        raise RuntimeError("Refusing to seed demo school when ENVIRONMENT=production.")

    school_repo = SchoolRepository(db)
    
    # Check if demo school already exists
    existing = school_repo.get_by_code("DEMO001")
    if existing is not None:
        logger.info("Demo school already exists, skipping school seeding.")
        return None

    # Create demo school
    school = School(
        name="MeritMatrix Demo School",
        code="DEMO001",
        address="123 Education Street",
        city="Learning City",
        country="Knowledge Land",
        phone="+1-555-0100",
        email="info@demo.meritmatrix.dev",
        website="https://demo.meritmatrix.dev",
        timezone="UTC",
        currency="USD",
        is_active=True,
    )
    db.add(school)
    db.flush()
    logger.info(f"Created demo school: {school.name} ({school.code})")

    # Create current academic year
    current_year = date.today().year
    academic_year = AcademicYear(
        school_id=school.id,
        name=f"{current_year} Academic Year",
        start_date=date(current_year, 1, 1),
        end_date=date(current_year, 12, 31),
        is_current=True,
        is_active=True,
    )
    db.add(academic_year)
    db.flush()
    logger.info(f"Created academic year: {academic_year.name}")

    # Create terms
    terms = []
    term_data = [
        ("Term 1", 1, date(current_year, 1, 1), date(current_year, 4, 30), False),
        ("Term 2", 2, date(current_year, 5, 1), date(current_year, 8, 31), False),
        ("Term 3", 3, date(current_year, 9, 1), date(current_year, 12, 31), True),  # Current term
    ]
    for name, num, start, end, is_current in term_data:
        term = Term(
            academic_year_id=academic_year.id,
            name=name,
            term_number=num,
            start_date=start,
            end_date=end,
            is_current=is_current,
            is_active=True,
        )
        db.add(term)
        terms.append(term)
    db.flush()
    logger.info(f"Created {len(terms)} terms")

    # Create classes
    classes = []
    class_data = [
        ("Form 1A", "F1A", 1, "A", "First year, stream A"),
        ("Form 1B", "F1B", 1, "B", "First year, stream B"),
        ("Form 2A", "F2A", 2, "A", "Second year, stream A"),
        ("Form 2B", "F2B", 2, "B", "Second year, stream B"),
        ("Form 3A", "F3A", 3, "A", "Third year, stream A"),
    ]
    for name, code, level, stream, desc in class_data:
        clazz = Class(
            school_id=school.id,
            name=name,
            code=code,
            level=level,
            stream=stream,
            description=desc,
            is_active=True,
        )
        db.add(clazz)
        classes.append(clazz)
    db.flush()
    logger.info(f"Created {len(classes)} classes")

    # Create subjects
    subjects = []
    subject_data = [
        ("Mathematics", "MAT101", "Core mathematics course"),
        ("English", "ENG101", "English language and literature"),
        ("Science", "SCI101", "General science"),
        ("Geography", "GEO101", "Physical and human geography"),
        ("History", "HIS101", "World history"),
        ("Computer Studies", "COM101", "Introduction to computing"),
    ]
    for name, code, desc in subject_data:
        subject = Subject(
            school_id=school.id,
            name=name,
            code=code,
            description=desc,
            is_active=True,
        )
        db.add(subject)
        subjects.append(subject)
    db.flush()
    logger.info(f"Created {len(subjects)} subjects")

    # Create class-subject assignments (Form 1A gets all subjects)
    if classes and subjects:
        form1a = classes[0]  # Form 1A
        for subject in subjects[:4]:  # First 4 subjects for Form 1A
            cs = ClassSubject(class_id=form1a.id, subject_id=subject.id)
            db.add(cs)
        db.flush()
        logger.info("Created class-subject assignments for Form 1A")

    return school, academic_year, terms, classes, subjects


def run() -> None:
    settings = get_settings()
    if settings.is_production:
        print(
            "Refusing to run development seed data against ENVIRONMENT=production.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Ensure tables exist (idempotent) — real deployments should use
    # `alembic upgrade head` instead, but this keeps the script usable
    # standalone in a fresh dev environment.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_permissions(db)
        seed_roles(db)
        assign_role_permissions(db)
        created = seed_demo_users(db)
        # Capture display data before commit/close expire/detach the ORM
        # objects, so nothing outside the session boundary touches them.
        summary = [(role_name, user.email, password) for role_name, (user, password) in created.items()]
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    print("\n=== MeritMatrix Pro — DEVELOPMENT seed data ===")
    print("These credentials are for local development ONLY. Never use in production.\n")
    if not summary:
        print("Demo users already existed; no new credentials were generated.")
    for role_name, email, password in summary:
        print(f"  {role_name:<13} {email}  password: {password}")
    print()


if __name__ == "__main__":
    run()
