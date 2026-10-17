"""Defense-in-depth tests for staff-linked account management boundaries."""
import pytest

from app.auth.assignment_access import deny_linked_staff_management
from app.models.school import School
from app.models.staff import Staff
from app.utils.errors import ForbiddenError


def test_linked_teacher_cannot_manage_school_administration_records(
    make_user, seeded_rbac, db_session
):
    school = School(name="Boundary School", code="BOUNDARY01", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()

    teacher = make_user(email="boundary-teacher@example.com", role_name="TEACHER")
    staff = Staff(
        school_id=school.id,
        staff_number="T-001",
        first_name="Teacher",
        last_name="One",
        email=teacher.email,
        user_id=teacher.id,
        employment_status="active",
        is_active=True,
    )
    db_session.add(staff)
    db_session.commit()

    with pytest.raises(ForbiddenError) as exc:
        deny_linked_staff_management(db_session, teacher, "edit student profiles")

    assert exc.value.code == "STAFF_MANAGEMENT_RESTRICTED"


def test_super_admin_override_is_preserved_for_management_records(
    make_user, seeded_rbac, db_session
):
    school = School(name="Admin Boundary School", code="BOUNDARY02", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()

    admin = make_user(email="boundary-admin@example.com", role_name="SUPER_ADMIN")
    db_session.add(
        Staff(
            school_id=school.id,
            staff_number="A-001",
            first_name="Admin",
            last_name="Linked",
            email=admin.email,
            user_id=admin.id,
            employment_status="active",
            is_active=True,
        )
    )
    db_session.commit()

    # Explicit system-admin authority must continue to override the staff guard.
    deny_linked_staff_management(db_session, admin, "edit student profiles")
