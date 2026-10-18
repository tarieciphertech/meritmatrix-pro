"""Defense-in-depth tests for staff-linked account management boundaries."""
import pytest

from app.auth.assignment_access import (
    assigned_class_ids,
    assigned_class_subject_ids,
    deny_linked_staff_management,
    require_staff_school_scope,
)
from app.models.school import School
from app.models.staff import Staff
from app.models.user_school import UserSchool
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


def test_linked_teacher_cannot_cross_employing_school_even_with_extra_membership(
    make_user, seeded_rbac, db_session
):
    first = School(name="Teacher Home School", code="THSCOPE01", city="Gaborone", country="Botswana")
    second = School(name="Other School", code="THSCOPE02", city="Gaborone", country="Botswana")
    db_session.add_all([first, second])
    db_session.flush()

    teacher = make_user(email="scope-teacher@example.com", role_name="TEACHER")
    db_session.add(
        Staff(
            school_id=first.id,
            staff_number="T-SCOPE-01",
            first_name="Teacher",
            last_name="Scoped",
            email=teacher.email,
            user_id=teacher.id,
            employment_status="active",
            is_active=True,
        )
    )
    # Even a stray membership row must not widen a linked teacher's access.
    db_session.add(UserSchool(user_id=teacher.id, school_id=second.id))
    db_session.commit()

    require_staff_school_scope(db_session, teacher, first.id)
    with pytest.raises(ForbiddenError) as exc:
        require_staff_school_scope(db_session, teacher, second.id)

    assert exc.value.code == "STAFF_SCHOOL_SCOPE_DENIED"


def test_inactive_or_terminated_staff_cannot_access_employing_school(
    make_user, seeded_rbac, db_session
):
    school = School(name="Former Teacher School", code="THSCOPE03", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    teacher = make_user(email="former-teacher@example.com", role_name="TEACHER")
    db_session.add(
        Staff(
            school_id=school.id,
            staff_number="T-SCOPE-02",
            first_name="Former",
            last_name="Teacher",
            email=teacher.email,
            user_id=teacher.id,
            employment_status="terminated",
            is_active=False,
        )
    )
    db_session.commit()

    with pytest.raises(ForbiddenError) as exc:
        require_staff_school_scope(db_session, teacher, school.id)

    assert exc.value.code == "STAFF_SCHOOL_SCOPE_DENIED"



def test_teacher_without_employment_profile_cannot_use_school_membership(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    """A TEACHER role and a stray membership cannot substitute for employment."""
    school = School(name="Unlinked Teacher School", code="UNLINKED01", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    teacher = make_user(email="unlinked-teacher@example.com", password="StrongPass123", role_name="TEACHER")
    db_session.add(UserSchool(user_id=teacher.id, school_id=school.id))
    db_session.commit()

    response = client.get("/api/v1/schools?limit=200", headers=auth_headers("unlinked-teacher@example.com", "StrongPass123"))
    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "STAFF_EMPLOYMENT_REQUIRED"

    with pytest.raises(ForbiddenError) as exc:
        require_staff_school_scope(db_session, teacher, school.id)
    assert exc.value.code == "STAFF_EMPLOYMENT_REQUIRED"

    # Assignment-aware endpoints must fail closed rather than treat this account
    # as an unrestricted non-staff user.
    assert assigned_class_ids(db_session, teacher, school.id) == set()
    assert assigned_class_subject_ids(db_session, teacher, school.id) == set()

    with pytest.raises(ForbiddenError) as management_exc:
        deny_linked_staff_management(db_session, teacher, "edit student profiles")
    assert management_exc.value.code == "STAFF_EMPLOYMENT_REQUIRED"
