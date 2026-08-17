"""Student CRUD and authorization tests."""
import uuid

import pytest

from app.models.student import Student, StudentStatus
from app.models.school import School
from app.schemas.student import StudentCreate


# ---- CRUD Tests ----

def test_create_student(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can create a student."""
    # Create school first
    school = School(name="Test School", code="TEST001", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "student_number": "STU001",
        "first_name": "John",
        "last_name": "Doe",
        "status": "active",
    }
    response = client.post(f"/api/v1/students?school_id={school.id}", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["student_number"] == "STU001"
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["is_active"] is True


def test_get_student(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can read a student."""
    school = School(name="Test School", code="TEST002", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU002", first_name="Jane", last_name="Doe", status=StudentStatus.ACTIVE)
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.get(f"/api/v1/students/{student.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["student_number"] == "STU002"


def test_list_students(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can list students for a school."""
    school = School(name="Test School", code="TEST003", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    # Create some students
    for i in range(3):
        student = Student(school_id=school.id, student_number=f"STU00{i}", first_name=f"First{i}", last_name="Last", status=StudentStatus.ACTIVE)
        db_session.add(student)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.get(f"/api/v1/students?school_id={school.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_update_student(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can update a student."""
    school = School(name="Test School", code="TEST004", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU004", first_name="Jane", last_name="Doe", status=StudentStatus.ACTIVE)
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {"first_name": "Janet"}
    response = client.patch(f"/api/v1/students/{student.id}", headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Janet"


def test_archive_student(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can archive a student."""
    school = School(name="Test School", code="TEST005", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU005", first_name="Jane", last_name="Doe", status=StudentStatus.ACTIVE)
    db_session.add(student)
    db_session.commit()
    db_session.refresh(student)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.delete(f"/api/v1/students/{student.id}", headers=headers)
    assert response.status_code == 204

    db_session.refresh(student)
    assert student.is_active is False


# ---- Validation Tests ----

def test_duplicate_student_number_rejected(client, make_user, auth_headers, seeded_rbac, db_session):
    """Duplicate student numbers within the same school are rejected."""
    school = School(name="Test School", code="TEST006", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    # Create first student
    student = Student(school_id=school.id, student_number="DUP001", first_name="First", last_name="Student", status=StudentStatus.ACTIVE)
    db_session.add(student)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    # Try to create with same number
    payload = {"student_number": "DUP001", "first_name": "Second", "last_name": "Student", "status": "active"}
    response = client.post(f"/api/v1/students?school_id={school.id}", headers=headers, json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_STUDENT_NUMBER"


def test_same_student_number_different_schools_allowed(client, make_user, auth_headers, seeded_rbac, db_session):
    """Same student number is allowed in different schools."""
    school_a = School(name="School A", code="SCHLA01", city="City", country="Country")
    school_b = School(name="School B", code="SCHLB01", city="City", country="Country")
    db_session.add_all([school_a, school_b])
    db_session.commit()

    student_a = Student(school_id=school_a.id, student_number="SAME001", first_name="A", last_name="Student", status=StudentStatus.ACTIVE)
    student_b = Student(school_id=school_b.id, student_number="SAME001", first_name="B", last_name="Student", status=StudentStatus.ACTIVE)
    db_session.add_all([student_a, student_b])
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    # Both should be retrievable
    response_a = client.get(f"/api/v1/students/{student_a.id}", headers=headers)
    response_b = client.get(f"/api/v1/students/{student_b.id}", headers=headers)
    assert response_a.status_code == 200
    assert response_b.status_code == 200


# ---- Authorization Tests ----

def test_unauthenticated_cannot_access_students(client):
    """Unauthenticated requests are rejected."""
    response = client.get("/api/v1/students?school_id=00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


def test_user_without_permission_cannot_create_student(client, make_user, auth_headers, seeded_rbac, db_session):
    """Users without students.create permission are rejected."""
    school = School(name="Test School", code="TEST007", city="City", country="Country")
    db_session.add(school)
    db_session.commit()

    make_user(email="student@example.com", password="StrongPass123", role_name="STUDENT")
    headers = auth_headers("student@example.com", "StrongPass123")

    payload = {"student_number": "STU001", "first_name": "Test", "last_name": "Student", "status": "active"}
    response = client.post(f"/api/v1/students?school_id={school.id}", headers=headers, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_school_id_cannot_be_changed(client, make_user, auth_headers, seeded_rbac, db_session):
    """school_id cannot be changed through PATCH."""
    school_a = School(name="School A", code="SCHLA02", city="City", country="Country")
    school_b = School(name="School B", code="SCHLB02", city="City", country="Country")
    db_session.add_all([school_a, school_b])
    db_session.commit()

    student = Student(school_id=school_a.id, student_number="STU008", first_name="Test", last_name="Student", status=StudentStatus.ACTIVE)
    db_session.add(student)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    # Attempt to change school_id
    payload = {"school_id": str(school_b.id)}
    response = client.patch(f"/api/v1/students/{student.id}", headers=headers, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SCHOOL_CHANGE_DENIED"

    # Verify school_id unchanged
    db_session.refresh(student)
    assert student.school_id == school_a.id