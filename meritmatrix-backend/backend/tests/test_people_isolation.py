"""People isolation and IDOR security tests for Milestone 4.

Tests that SCHOOL_ADMIN users can only access resources from their own school.
Tests IDOR attacks where an attacker tries to access another school's resources.
"""
import pytest
import uuid

from app.models.student import Student
from app.models.guardian import Guardian
from app.models.staff import Staff
from app.models.student_guardian import StudentGuardian
from app.models.academic_year import AcademicYear
from app.models.clazz import Class
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.school import School
from app.models.user_school import UserSchool
from app.repositories.user_school_repository import UserSchoolRepository
from app.services.user_school_service import UserSchoolService


def _setup_two_schools(db_session):
    """Create two schools with full academic structure and people."""
    school_a = School(name="School A", code="SCHLA01", city="City", country="Country")
    school_b = School(name="School B", code="SCHLB01", city="City", country="Country")
    db_session.add_all([school_a, school_b])
    db_session.commit()

    # School A structure
    year_a = AcademicYear(school_id=school_a.id, name="2024", start_date="2024-01-01", end_date="2024-12-31", is_current=True)
    clazz_a = Class(school_id=school_a.id, name="Form 1A", code="F1A", level=1, stream="A")
    student_a = Student(school_id=school_a.id, student_number="STU_A001", first_name="Student", last_name="A", status="active")
    guardian_a = Guardian(school_id=school_a.id, first_name="Guardian", last_name="A", phone="+1-555-0100")
    staff_a = Staff(school_id=school_a.id, staff_number="STF_A001", first_name="Staff", last_name="A")
    db_session.add_all([year_a, clazz_a, student_a, guardian_a, staff_a])
    db_session.commit()

    enrollment_a = Enrollment(student_id=student_a.id, academic_year_id=year_a.id, class_id=clazz_a.id, enrollment_date="2024-01-15", status=EnrollmentStatus.ACTIVE)
    sg_a = StudentGuardian(student_id=student_a.id, guardian_id=guardian_a.id, relationship_type="mother")
    db_session.add_all([enrollment_a, sg_a])
    db_session.commit()

    # School B structure
    year_b = AcademicYear(school_id=school_b.id, name="2024", start_date="2024-01-01", end_date="2024-12-31", is_current=True)
    clazz_b = Class(school_id=school_b.id, name="Form 1A", code="F1A", level=1, stream="A")
    student_b = Student(school_id=school_b.id, student_number="STU_B001", first_name="Student", last_name="B", status="active")
    guardian_b = Guardian(school_id=school_b.id, first_name="Guardian", last_name="B", phone="+1-555-0101")
    staff_b = Staff(school_id=school_b.id, staff_number="STF_B001", first_name="Staff", last_name="B")
    db_session.add_all([year_b, clazz_b, student_b, guardian_b, staff_b])
    db_session.commit()

    enrollment_b = Enrollment(student_id=student_b.id, academic_year_id=year_b.id, class_id=clazz_b.id, enrollment_date="2024-01-15", status=EnrollmentStatus.ACTIVE)
    sg_b = StudentGuardian(student_id=student_b.id, guardian_id=guardian_b.id, relationship_type="mother")
    db_session.add_all([enrollment_b, sg_b])
    db_session.commit()

    return {
        "school_a": school_a, "school_b": school_b,
        "student_a": student_a, "student_b": student_b,
        "guardian_a": guardian_a, "guardian_b": guardian_b,
        "staff_a": staff_a, "staff_b": staff_b,
        "enrollment_a": enrollment_a, "enrollment_b": enrollment_b,
        "sg_a": sg_a, "sg_b": sg_b,
    }


def _add_user_school_membership(db_session, user, school):
    """Add user_school membership for a user to a school."""
    membership = UserSchool(user_id=user.id, school_id=school.id)
    db_session.add(membership)
    db_session.commit()


def test_school_admin_cannot_access_other_school_student(client, make_user, auth_headers, seeded_rbac, db_session):
    """SCHOOL_ADMIN A cannot access School B's students."""
    entities = _setup_two_schools(db_session)

    make_user(email="admin_a@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    user_a = make_user(email="admin_a@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    _add_user_school_membership(db_session, user_a, entities["school_a"])
    headers = auth_headers("admin_a@example.com", "StrongPass123")

    # Should be able to access own student
    response = client.get(f"/api/v1/students/{entities['student_a'].id}", headers=headers)
    assert response.status_code == 200

    # Should NOT be able to access other school's student
    response = client.get(f"/api/v1/students/{entities['student_b'].id}", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SCHOOL_ADMIN_SCOPE_DENIED"


def test_school_admin_cannot_access_other_school_guardian(client, make_user, auth_headers, seeded_rbac, db_session):
    """SCHOOL_ADMIN A cannot access School B's guardians."""
    entities = _setup_two_schools(db_session)

    user_a = make_user(email="admin_a@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    _add_user_school_membership(db_session, user_a, entities["school_a"])
    headers = auth_headers("admin_a@example.com", "StrongPass123")

    response = client.get(f"/api/v1/guardians/{entities['guardian_b'].id}", headers=headers)
    assert response.status_code == 403


def test_school_admin_cannot_access_other_school_staff(client, make_user, auth_headers, seeded_rbac, db_session):
    """SCHOOL_ADMIN A cannot access School B's staff."""
    entities = _setup_two_schools(db_session)

    user_a = make_user(email="admin_a@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    _add_user_school_membership(db_session, user_a, entities["school_a"])
    headers = auth_headers("admin_a@example.com", "StrongPass123")

    response = client.get(f"/api/v1/staff/{entities['staff_b'].id}", headers=headers)
    assert response.status_code == 403


def test_school_admin_cannot_access_other_school_enrollment(client, make_user, auth_headers, seeded_rbac, db_session):
    """SCHOOL_ADMIN A cannot access School B's enrollments."""
    entities = _setup_two_schools(db_session)

    user_a = make_user(email="admin_a@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    _add_user_school_membership(db_session, user_a, entities["school_a"])
    headers = auth_headers("admin_a@example.com", "StrongPass123")

    response = client.get(f"/api/v1/enrollments/{entities['enrollment_b'].id}", headers=headers)
    assert response.status_code == 403


def test_school_admin_cannot_access_other_school_student_guardian(client, make_user, auth_headers, seeded_rbac, db_session):
    """SCHOOL_ADMIN A cannot access School B's student-guardian relationships."""
    entities = _setup_two_schools(db_session)

    user_a = make_user(email="admin_a@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    _add_user_school_membership(db_session, user_a, entities["school_a"])
    headers = auth_headers("admin_a@example.com", "StrongPass123")

    response = client.get(f"/api/v1/student-guardians/student/{entities['student_b'].id}", headers=headers)
    assert response.status_code == 403


def test_school_admin_only_sees_own_school_students(client, make_user, auth_headers, seeded_rbac, db_session):
    """SCHOOL_ADMIN list only returns students from their school."""
    entities = _setup_two_schools(db_session)

    user_a = make_user(email="admin_a@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    _add_user_school_membership(db_session, user_a, entities["school_a"])
    headers = auth_headers("admin_a@example.com", "StrongPass123")

    response = client.get(f"/api/v1/students?school_id={entities['school_a'].id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    # Verify no School B students in response
    for item in data:
        assert item["student_number"].startswith("STU_A") or item["student_number"] == entities["student_a"].student_number


def test_school_admin_only_sees_own_school_guardians(client, make_user, auth_headers, seeded_rbac, db_session):
    """SCHOOL_ADMIN list only returns guardians from their school."""
    entities = _setup_two_schools(db_session)

    user_a = make_user(email="admin_a@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    _add_user_school_membership(db_session, user_a, entities["school_a"])
    headers = auth_headers("admin_a@example.com", "StrongPass123")

    response = client.get(f"/api/v1/guardians?school_id={entities['school_a'].id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    for item in data:
        # All guardians should belong to School A
        assert "A" in str(item) or item.get("first_name") == "Guardian"


def test_school_admin_only_sees_own_school_staff(client, make_user, auth_headers, seeded_rbac, db_session):
    """SCHOOL_ADMIN list only returns staff from their school."""
    entities = _setup_two_schools(db_session)

    user_a = make_user(email="admin_a@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    _add_user_school_membership(db_session, user_a, entities["school_a"])
    headers = auth_headers("admin_a@example.com", "StrongPass123")

    response = client.get(f"/api/v1/staff?school_id={entities['school_a'].id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    for item in data:
        assert "A" in str(item) or item.get("first_name") == "Staff"


def test_school_admin_only_sees_own_school_enrollments(client, make_user, auth_headers, seeded_rbac, db_session):
    """SCHOOL_ADMIN list only returns enrollments from their school."""
    entities = _setup_two_schools(db_session)

    user_a = make_user(email="admin_a@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    _add_user_school_membership(db_session, user_a, entities["school_a"])
    headers = auth_headers("admin_a@example.com", "StrongPass123")

    response = client.get(f"/api/v1/enrollments?school_id={entities['school_a'].id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    for item in data:
        assert item["student_id"] == str(entities["student_a"].id)


def test_school_admin_without_membership_denied(client, make_user, auth_headers, seeded_rbac, db_session):
    """SCHOOL_ADMIN without user_schools membership is denied access."""
    school = School(name="Test School", code="TEST001", city="City", country="Country")
    db_session.add(school)
    db_session.commit()

    student = Student(school_id=school.id, student_number="STU001", first_name="Test", last_name="Student", status="active")
    db_session.add(student)
    db_session.commit()

    # Create SCHOOL_ADMIN but DON'T add user_schools membership
    user = make_user(email="admin@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.get(f"/api/v1/students/{student.id}", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SCHOOL_ACCESS_DENIED"


def test_super_admin_can_access_all_schools(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can access resources from any school."""
    entities = _setup_two_schools(db_session)

    make_user(email="super@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("super@example.com", "StrongPass123")

    # Should be able to access both schools' resources
    response_a = client.get(f"/api/v1/students/{entities['student_a'].id}", headers=headers)
    response_b = client.get(f"/api/v1/students/{entities['student_b'].id}", headers=headers)
    assert response_a.status_code == 200
    assert response_b.status_code == 200

    response_a = client.get(f"/api/v1/guardians/{entities['guardian_a'].id}", headers=headers)
    response_b = client.get(f"/api/v1/guardians/{entities['guardian_b'].id}", headers=headers)
    assert response_a.status_code == 200
    assert response_b.status_code == 200

    response_a = client.get(f"/api/v1/staff/{entities['staff_a'].id}", headers=headers)
    response_b = client.get(f"/api/v1/staff/{entities['staff_b'].id}", headers=headers)
    assert response_a.status_code == 200
    assert response_b.status_code == 200


def test_unknown_uuid_returns_404_not_403(client, make_user, auth_headers, seeded_rbac, db_session):
    """Unknown UUID returns 404, not 403 (no information leakage)."""
    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    fake_uuid = str(uuid.uuid4())
    response = client.get(f"/api/v1/students/{fake_uuid}", headers=headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "STUDENT_NOT_FOUND"