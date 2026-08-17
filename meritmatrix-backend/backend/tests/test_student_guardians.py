"""Student-Guardian relationship tests including cross-school security and primary guardian invariant."""
import pytest

from app.models.student import Student
from app.models.guardian import Guardian
from app.models.student_guardian import StudentGuardian
from app.models.school import School


def test_create_student_guardian_relationship(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can create a student-guardian relationship."""
    school = School(name="Test School", code="TEST001", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU001", first_name="John", last_name="Doe", status="active")
    guardian = Guardian(school_id=school.id, first_name="Jane", last_name="Doe", phone="+1-555-0100")
    db_session.add_all([student, guardian])
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "student_id": str(student.id),
        "guardian_id": str(guardian.id),
        "relationship_type": "mother",
        "is_primary": True,
    }
    response = client.post("/api/v1/student-guardians", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["student_id"] == str(student.id)
    assert data["guardian_id"] == str(guardian.id)
    assert data["is_primary"] is True


def test_cross_school_relationship_rejected(client, make_user, auth_headers, seeded_rbac, db_session):
    """Cannot create relationship between student and guardian from different schools."""
    school_a = School(name="School A", code="SCHLA01", city="City", country="Country")
    school_b = School(name="School B", code="SCHLB01", city="City", country="Country")
    db_session.add_all([school_a, school_b])
    db_session.commit()

    student_a = Student(school_id=school_a.id, student_number="STU001", first_name="John", last_name="Doe", status="active")
    guardian_b = Guardian(school_id=school_b.id, first_name="Jane", last_name="Doe", phone="+1-555-0100")
    db_session.add_all([student_a, guardian_b])
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "student_id": str(student_a.id),
        "guardian_id": str(guardian_b.id),
        "relationship_type": "mother",
    }
    response = client.post("/api/v1/student-guardians", headers=headers, json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "CROSS_SCHOOL_RELATIONSHIP_DENIED"


def test_duplicate_relationship_rejected(client, make_user, auth_headers, seeded_rbac, db_session):
    """Cannot create duplicate student-guardian relationship."""
    school = School(name="Test School", code="TEST002", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU002", first_name="John", last_name="Doe", status="active")
    guardian = Guardian(school_id=school.id, first_name="Jane", last_name="Doe", phone="+1-555-0100")
    db_session.add_all([student, guardian])
    db_session.commit()

    # Create first relationship
    relationship = StudentGuardian(student_id=student.id, guardian_id=guardian.id, relationship_type="mother")
    db_session.add(relationship)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "student_id": str(student.id),
        "guardian_id": str(guardian.id),
        "relationship_type": "mother",
    }
    response = client.post("/api/v1/student-guardians", headers=headers, json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_STUDENT_GUARDIAN"


def test_primary_guardian_replacement(client, make_user, auth_headers, seeded_rbac, db_session):
    """Creating a new primary guardian unsets the previous primary."""
    school = School(name="Test School", code="TEST003", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU003", first_name="John", last_name="Doe", status="active")
    guardian_a = Guardian(school_id=school.id, first_name="Jane", last_name="Doe", phone="+1-555-0100")
    guardian_b = Guardian(school_id=school.id, first_name="Jim", last_name="Doe", phone="+1-555-0101")
    db_session.add_all([student, guardian_a, guardian_b])
    db_session.commit()

    # Create first primary guardian
    relationship_a = StudentGuardian(student_id=student.id, guardian_id=guardian_a.id, relationship_type="mother", is_primary=True)
    db_session.add(relationship_a)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    # Create second guardian as primary - this should unset the first
    payload = {
        "student_id": str(student.id),
        "guardian_id": str(guardian_b.id),
        "relationship_type": "father",
        "is_primary": True,
    }
    response = client.post("/api/v1/student-guardians", headers=headers, json=payload)
    assert response.status_code == 201, response.text

    # Verify only one primary via database state
    all_relationships = db_session.query(StudentGuardian).filter_by(student_id=student.id).all()
    primary_count = sum(1 for r in all_relationships if r.is_primary)
    assert primary_count == 1, f"Expected 1 primary guardian, got {primary_count}"

    # Verify the new one is primary
    relationship_b = db_session.query(StudentGuardian).filter_by(guardian_id=guardian_b.id).first()
    assert relationship_b.is_primary is True


def test_list_student_guardians(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can list guardians for a student."""
    school = School(name="Test School", code="TEST004", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU004", first_name="John", last_name="Doe", status="active")
    guardian_a = Guardian(school_id=school.id, first_name="Jane", last_name="Doe", phone="+1-555-0100")
    guardian_b = Guardian(school_id=school.id, first_name="Jim", last_name="Doe", phone="+1-555-0101")
    db_session.add_all([student, guardian_a, guardian_b])
    db_session.commit()

    relationship_a = StudentGuardian(student_id=student.id, guardian_id=guardian_a.id, relationship_type="mother")
    relationship_b = StudentGuardian(student_id=student.id, guardian_id=guardian_b.id, relationship_type="father")
    db_session.add_all([relationship_a, relationship_b])
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.get(f"/api/v1/student-guardians/student/{student.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_delete_relationship(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can delete a student-guardian relationship."""
    school = School(name="Test School", code="TEST005", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    student = Student(school_id=school.id, student_number="STU005", first_name="John", last_name="Doe", status="active")
    guardian = Guardian(school_id=school.id, first_name="Jane", last_name="Doe", phone="+1-555-0100")
    db_session.add_all([student, guardian])
    db_session.commit()

    relationship = StudentGuardian(student_id=student.id, guardian_id=guardian.id, relationship_type="mother")
    db_session.add(relationship)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.delete(f"/api/v1/student-guardians/{relationship.id}", headers=headers)
    assert response.status_code == 204


def test_unauthenticated_cannot_access_student_guardians(client):
    """Unauthenticated requests are rejected."""
    response = client.get("/api/v1/student-guardians/student/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


def test_user_without_permission_cannot_create_relationship(client, make_user, auth_headers, seeded_rbac, db_session):
    """Users without student_guardians.create permission are rejected."""
    school = School(name="Test School", code="TEST006", city="City", country="Country")
    db_session.add(school)
    db_session.commit()

    student = Student(school_id=school.id, student_number="STU006", first_name="John", last_name="Doe", status="active")
    guardian = Guardian(school_id=school.id, first_name="Jane", last_name="Doe", phone="+1-555-0100")
    db_session.add_all([student, guardian])
    db_session.commit()

    make_user(email="student@example.com", password="StrongPass123", role_name="STUDENT")
    headers = auth_headers("student@example.com", "StrongPass123")

    payload = {
        "student_id": str(student.id),
        "guardian_id": str(guardian.id),
        "relationship_type": "mother",
    }
    response = client.post("/api/v1/student-guardians", headers=headers, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"