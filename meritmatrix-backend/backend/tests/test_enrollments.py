"""Enrollment CRUD and authorization tests including cross-school security and historical integrity."""
import pytest
from datetime import date

from app.models.student import Student
from app.models.academic_year import AcademicYear
from app.models.clazz import Class
from app.models.enrollment import Enrollment, EnrollmentStatus
from app.models.school import School


def test_create_enrollment(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can create an enrollment."""
    school = School(name="Test School", code="TEST001", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU001", first_name="John", last_name="Doe", status="active")
    academic_year = AcademicYear(school_id=school.id, name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), is_current=True)
    clazz = Class(school_id=school.id, name="Form 1A", code="F1A", level=1, stream="A")
    db_session.add_all([student, academic_year, clazz])
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "student_id": str(student.id),
        "academic_year_id": str(academic_year.id),
        "class_id": str(clazz.id),
        "enrollment_date": "2024-01-15",
        "status": "active",
    }
    response = client.post("/api/v1/enrollments", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["student_id"] == str(student.id)
    assert data["status"] == "active"


def test_duplicate_active_enrollment_rejected(client, make_user, auth_headers, seeded_rbac, db_session):
    """Cannot create duplicate active enrollment for same student/year."""
    school = School(name="Test School", code="TEST002", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU002", first_name="John", last_name="Doe", status="active")
    academic_year = AcademicYear(school_id=school.id, name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), is_current=True)
    clazz = Class(school_id=school.id, name="Form 1A", code="F1A", level=1, stream="A")
    db_session.add_all([student, academic_year, clazz])
    db_session.commit()

    # Create first enrollment
    enrollment = Enrollment(student_id=student.id, academic_year_id=academic_year.id, class_id=clazz.id, enrollment_date=date(2024, 1, 15), status=EnrollmentStatus.ACTIVE)
    db_session.add(enrollment)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "student_id": str(student.id),
        "academic_year_id": str(academic_year.id),
        "class_id": str(clazz.id),
        "enrollment_date": "2024-02-01",
        "status": "active",
    }
    response = client.post("/api/v1/enrollments", headers=headers, json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_ACTIVE_ENROLLMENT"


def test_historical_enrollment_preserved(client, make_user, auth_headers, seeded_rbac, db_session):
    """Historical enrollments remain after creating new enrollment."""
    school = School(name="Test School", code="TEST003", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU003", first_name="John", last_name="Doe", status="active")
    year_2024 = AcademicYear(school_id=school.id, name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), is_current=False)
    year_2025 = AcademicYear(school_id=school.id, name="2025", start_date=date(2025, 1, 1), end_date=date(2025, 12, 31), is_current=True)
    clazz = Class(school_id=school.id, name="Form 1A", code="F1A", level=1, stream="A")
    db_session.add_all([student, year_2024, year_2025, clazz])
    db_session.commit()

    # Create completed 2024 enrollment
    enrollment_2024 = Enrollment(student_id=student.id, academic_year_id=year_2024.id, class_id=clazz.id, enrollment_date=date(2024, 1, 15), status=EnrollmentStatus.COMPLETED)
    db_session.add(enrollment_2024)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    # Create active 2025 enrollment
    payload = {
        "student_id": str(student.id),
        "academic_year_id": str(year_2025.id),
        "class_id": str(clazz.id),
        "enrollment_date": "2025-01-15",
        "status": "active",
    }
    response = client.post("/api/v1/enrollments", headers=headers, json=payload)
    assert response.status_code == 201

    # Verify both exist
    all_enrollments = db_session.query(Enrollment).filter_by(student_id=student.id).all()
    assert len(all_enrollments) == 2


def test_cross_school_enrollment_rejected_student(client, make_user, auth_headers, seeded_rbac, db_session):
    """Cannot create enrollment with student from different school."""
    school_a = School(name="School A", code="SCHLA01", city="City", country="Country")
    school_b = School(name="School B", code="SCHLB01", city="City", country="Country")
    db_session.add_all([school_a, school_b])
    db_session.commit()

    student_a = Student(school_id=school_a.id, student_number="STU001", first_name="John", last_name="Doe", status="active")
    year_b = AcademicYear(school_id=school_b.id, name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), is_current=True)
    clazz_b = Class(school_id=school_b.id, name="Form 1A", code="F1A", level=1, stream="A")
    db_session.add_all([student_a, year_b, clazz_b])
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "student_id": str(student_a.id),
        "academic_year_id": str(year_b.id),
        "class_id": str(clazz_b.id),
        "enrollment_date": "2024-01-15",
        "status": "active",
    }
    response = client.post("/api/v1/enrollments", headers=headers, json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CROSS_SCHOOL_ENROLLMENT_DENIED"


def test_cross_school_enrollment_rejected_year(client, make_user, auth_headers, seeded_rbac, db_session):
    """Cannot create enrollment with academic year from different school."""
    school_a = School(name="School A", code="SCHLA02", city="City", country="Country")
    school_b = School(name="School B", code="SCHLB02", city="City", country="Country")
    db_session.add_all([school_a, school_b])
    db_session.commit()

    student_a = Student(school_id=school_a.id, student_number="STU002", first_name="John", last_name="Doe", status="active")
    year_a = AcademicYear(school_id=school_a.id, name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), is_current=True)
    clazz_b = Class(school_id=school_b.id, name="Form 1A", code="F1A", level=1, stream="A")
    db_session.add_all([student_a, year_a, clazz_b])
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "student_id": str(student_a.id),
        "academic_year_id": str(year_a.id),
        "class_id": str(clazz_b.id),
        "enrollment_date": "2024-01-15",
        "status": "active",
    }
    response = client.post("/api/v1/enrollments", headers=headers, json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CROSS_SCHOOL_ENROLLMENT_DENIED"


def test_enrollment_date_before_academic_year_rejected(client, make_user, auth_headers, seeded_rbac, db_session):
    """Enrollment date before academic year is rejected."""
    school = School(name="Test School", code="TEST004", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU004", first_name="John", last_name="Doe", status="active")
    academic_year = AcademicYear(school_id=school.id, name="2024", start_date=date(2024, 6, 1), end_date=date(2024, 12, 31), is_current=True)
    clazz = Class(school_id=school.id, name="Form 1A", code="F1A", level=1, stream="A")
    db_session.add_all([student, academic_year, clazz])
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "student_id": str(student.id),
        "academic_year_id": str(academic_year.id),
        "class_id": str(clazz.id),
        "enrollment_date": "2024-01-15",  # Before academic year start
        "status": "active",
    }
    response = client.post("/api/v1/enrollments", headers=headers, json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ENROLLMENT_DATE_OUT_OF_RANGE"


def test_enrollment_date_after_academic_year_rejected(client, make_user, auth_headers, seeded_rbac, db_session):
    """Enrollment date after academic year is rejected."""
    school = School(name="Test School", code="TEST005", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU005", first_name="John", last_name="Doe", status="active")
    academic_year = AcademicYear(school_id=school.id, name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 6, 30), is_current=True)
    clazz = Class(school_id=school.id, name="Form 1A", code="F1A", level=1, stream="A")
    db_session.add_all([student, academic_year, clazz])
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "student_id": str(student.id),
        "academic_year_id": str(academic_year.id),
        "class_id": str(clazz.id),
        "enrollment_date": "2024-12-15",  # After academic year end
        "status": "active",
    }
    response = client.post("/api/v1/enrollments", headers=headers, json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ENROLLMENT_DATE_OUT_OF_RANGE"


def test_get_enrollment(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can read an enrollment."""
    school = School(name="Test School", code="TEST006", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU006", first_name="John", last_name="Doe", status="active")
    academic_year = AcademicYear(school_id=school.id, name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), is_current=True)
    clazz = Class(school_id=school.id, name="Form 1A", code="F1A", level=1, stream="A")
    db_session.add_all([student, academic_year, clazz])
    db_session.commit()

    enrollment = Enrollment(student_id=student.id, academic_year_id=academic_year.id, class_id=clazz.id, enrollment_date=date(2024, 1, 15), status=EnrollmentStatus.ACTIVE)
    db_session.add(enrollment)
    db_session.commit()
    db_session.refresh(enrollment)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.get(f"/api/v1/enrollments/{enrollment.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "active"


def test_list_enrollments(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can list enrollments for a school."""
    school = School(name="Test School", code="TEST007", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU007", first_name="John", last_name="Doe", status="active")
    academic_year = AcademicYear(school_id=school.id, name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), is_current=True)
    clazz = Class(school_id=school.id, name="Form 1A", code="F1A", level=1, stream="A")
    db_session.add_all([student, academic_year, clazz])
    db_session.commit()

    # Create multiple enrollments
    for i in range(3):
        enrollment = Enrollment(student_id=student.id, academic_year_id=academic_year.id, class_id=clazz.id, enrollment_date=date(2024, 1, 15), status=EnrollmentStatus.ACTIVE)
        db_session.add(enrollment)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.get(f"/api/v1/enrollments?school_id={school.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_update_enrollment(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can update an enrollment."""
    school = School(name="Test School", code="TEST008", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU008", first_name="John", last_name="Doe", status="active")
    academic_year = AcademicYear(school_id=school.id, name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), is_current=True)
    clazz = Class(school_id=school.id, name="Form 1A", code="F1A", level=1, stream="A")
    db_session.add_all([student, academic_year, clazz])
    db_session.commit()

    enrollment = Enrollment(student_id=student.id, academic_year_id=academic_year.id, class_id=clazz.id, enrollment_date=date(2024, 1, 15), status=EnrollmentStatus.ACTIVE)
    db_session.add(enrollment)
    db_session.commit()
    db_session.refresh(enrollment)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {"status": "completed"}
    response = client.patch(f"/api/v1/enrollments/{enrollment.id}", headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_unauthenticated_cannot_access_enrollments(client):
    """Unauthenticated requests are rejected."""
    response = client.get("/api/v1/enrollments?school_id=00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


def test_user_without_permission_cannot_create_enrollment(client, make_user, auth_headers, seeded_rbac, db_session):
    """Users without enrollments.create permission are rejected."""
    school = School(name="Test School", code="TEST009", city="City", country="Country")
    db_session.add(school)
    db_session.commit()

    student = Student(school_id=school.id, student_number="STU009", first_name="John", last_name="Doe", status="active")
    academic_year = AcademicYear(school_id=school.id, name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), is_current=True)
    clazz = Class(school_id=school.id, name="Form 1A", code="F1A", level=1, stream="A")
    db_session.add_all([student, academic_year, clazz])
    db_session.commit()

    make_user(email="student@example.com", password="StrongPass123", role_name="STUDENT")
    headers = auth_headers("student@example.com", "StrongPass123")

    payload = {
        "student_id": str(student.id),
        "academic_year_id": str(academic_year.id),
        "class_id": str(clazz.id),
        "enrollment_date": "2024-01-15",
        "status": "active",
    }
    response = client.post("/api/v1/enrollments", headers=headers, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_enrollment_identity_cannot_be_changed(client, make_user, auth_headers, seeded_rbac, db_session):
    """Cannot change student_id, academic_year_id, or class_id through PATCH."""
    school = School(name="Test School", code="TEST010", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU010", first_name="John", last_name="Doe", status="active")
    academic_year = AcademicYear(school_id=school.id, name="2024", start_date=date(2024, 1, 1), end_date=date(2024, 12, 31), is_current=True)
    clazz = Class(school_id=school.id, name="Form 1A", code="F1A", level=1, stream="A")
    db_session.add_all([student, academic_year, clazz])
    db_session.commit()

    enrollment = Enrollment(student_id=student.id, academic_year_id=academic_year.id, class_id=clazz.id, enrollment_date=date(2024, 1, 15), status=EnrollmentStatus.ACTIVE)
    db_session.add(enrollment)
    db_session.commit()
    db_session.refresh(enrollment)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    # Attempt to change identity fields
    payload = {"student_id": str(student.id)}  # Even same student should be rejected
    response = client.patch(f"/api/v1/enrollments/{enrollment.id}", headers=headers, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ENROLLMENT_IDENTITY_CHANGE_DENIED"

def test_linked_teacher_only_reads_enrollments_for_assigned_students(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    """School membership alone must not expose unrelated students' enrollments to teachers."""
    from app.models.class_subject import ClassSubject
    from app.models.staff import Staff
    from app.models.subject import Subject
    from app.models.teaching_assignment import TeachingAssignment
    from app.models.user_school import UserSchool

    school = School(name="Assignment Scope School", code="ASSIGN01", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    year = AcademicYear(
        school_id=school.id, name="2026", start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31), is_current=True, is_active=True,
    )
    assigned_class = Class(school_id=school.id, name="Form 1", code="F1", level=1, is_active=True)
    other_class = Class(school_id=school.id, name="Form 2", code="F2", level=2, is_active=True)
    assigned_student = Student(
        school_id=school.id, student_number="AS-001", first_name="Assigned",
        last_name="Student", status="active", is_active=True,
    )
    other_student = Student(
        school_id=school.id, student_number="AS-002", first_name="Other",
        last_name="Student", status="active", is_active=True,
    )
    subject = Subject(school_id=school.id, name="Mathematics", code="MATH", is_active=True)
    db_session.add_all([year, assigned_class, other_class, assigned_student, other_student, subject])
    db_session.flush()
    assigned_pair = ClassSubject(class_id=assigned_class.id, subject_id=subject.id)
    db_session.add(assigned_pair)
    db_session.flush()
    assigned_enrollment = Enrollment(
        student_id=assigned_student.id, academic_year_id=year.id, class_id=assigned_class.id,
        enrollment_date=date(2026, 1, 10), status=EnrollmentStatus.ACTIVE,
    )
    other_enrollment = Enrollment(
        student_id=other_student.id, academic_year_id=year.id, class_id=other_class.id,
        enrollment_date=date(2026, 1, 10), status=EnrollmentStatus.ACTIVE,
    )
    teacher = make_user(
        email="enrollment-scope-teacher@example.com", password="StrongPass123",
        role_name="TEACHER",
    )
    db_session.add(UserSchool(user_id=teacher.id, school_id=school.id))
    staff = Staff(
        school_id=school.id, staff_number="AS-T-001", first_name="Assigned",
        last_name="Teacher", employment_status="active", is_active=True, user_id=teacher.id,
    )
    db_session.add_all([assigned_enrollment, other_enrollment, staff])
    db_session.flush()
    db_session.add(TeachingAssignment(
        school_id=school.id, staff_id=staff.id, class_subject_id=assigned_pair.id,
        start_date=date(2026, 1, 1), is_active=True,
    ))
    db_session.commit()

    headers = auth_headers("enrollment-scope-teacher@example.com", "StrongPass123")
    listed = client.get(
        f"/api/v1/enrollments?school_id={school.id}",
        headers=headers,
    )
    assert listed.status_code == 200, listed.text
    assert [row["id"] for row in listed.json()] == [str(assigned_enrollment.id)]

    allowed = client.get(f"/api/v1/enrollments/{assigned_enrollment.id}", headers=headers)
    assert allowed.status_code == 200, allowed.text

    # Employment status must immediately revoke assignment-scoped academic access.
    staff.employment_status = "terminated"
    db_session.commit()
    terminated_access = client.get(f"/api/v1/enrollments/{assigned_enrollment.id}", headers=headers)
    assert terminated_access.status_code == 403, terminated_access.text
    assert terminated_access.json()["error"]["code"] == "STAFF_SCHOOL_SCOPE_DENIED"

    denied = client.get(f"/api/v1/enrollments/{other_enrollment.id}", headers=headers)
    assert denied.status_code == 403, denied.text
    assert denied.json()["error"]["code"] == "STUDENT_ASSIGNMENT_REQUIRED"
