"""Cross-school isolation and IDOR prevention tests.

These tests verify that SCHOOL_ADMIN users can only access resources
belonging to their assigned school, preventing horizontal privilege
escalation and IDOR attacks.
"""
import uuid
from datetime import date

import pytest

from app.models.school import School
from app.models.clazz import Class
from app.models.subject import Subject
from app.models.academic_year import AcademicYear
from app.models.term import Term
from app.models.class_subject import ClassSubject
from app.models.user_school import UserSchool
from app.repositories.user_school_repository import UserSchoolRepository


# ---- Helper Fixtures ----

@pytest.fixture
def school_a(client, make_user, auth_headers, seeded_rbac, db_session):
    """Create School A."""
    make_user(email="super@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("super@example.com", "StrongPass123")
    
    payload = {"name": "School A", "code": "SCHLA", "city": "City A", "country": "Country"}
    response = client.post("/api/v1/schools", headers=headers, json=payload)
    school_data = response.json()
    return uuid.UUID(school_data["id"])


@pytest.fixture
def school_b(client, make_user, auth_headers, seeded_rbac, db_session, school_a):
    """Create School B."""
    make_user(email="super@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("super@example.com", "StrongPass123")
    
    payload = {"name": "School B", "code": "SCHLB", "city": "City B", "country": "Country"}
    response = client.post("/api/v1/schools", headers=headers, json=payload)
    school_data = response.json()
    return uuid.UUID(school_data["id"])


@pytest.fixture
def school_a_admin(client, make_user, auth_headers, seeded_rbac, db_session, school_a):
    """Create a SCHOOL_ADMIN assigned to School A."""
    user = make_user(email="adminA@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    
    # Assign user to School A
    repo = UserSchoolRepository(db_session)
    repo.create(UserSchool(user_id=user.id, school_id=school_a))
    db_session.commit()
    
    return user


@pytest.fixture
def school_b_admin(client, make_user, auth_headers, seeded_rbac, db_session, school_b):
    """Create a SCHOOL_ADMIN assigned to School B."""
    user = make_user(email="adminB@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    
    # Assign user to School B
    repo = UserSchoolRepository(db_session)
    repo.create(UserSchool(user_id=user.id, school_id=school_b))
    db_session.commit()
    
    return user


# ---- School Access Isolation Tests ----

class TestSchoolAccessIsolation:
    """Test that SCHOOL_ADMIN users can only access their own school."""

    def test_admin_a_can_access_school_a(self, client, auth_headers, school_a_admin, school_a):
        """Admin A can read School A."""
        headers = auth_headers("adminA@example.com", "StrongPass123")
        response = client.get(f"/api/v1/schools/{school_a}", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["id"] == str(school_a)

    def test_admin_a_cannot_access_school_b(self, client, auth_headers, school_a_admin, school_b):
        """Admin A cannot read School B (IDOR prevention)."""
        headers = auth_headers("adminA@example.com", "StrongPass123")
        response = client.get(f"/api/v1/schools/{school_b}", headers=headers)
        assert response.status_code == 403, response.text
        assert response.json()["error"]["code"] == "SCHOOL_ACCESS_DENIED"

    def test_school_admin_school_list_contains_only_memberships(
        self, client, auth_headers, school_a_admin, school_a, school_b
    ):
        """The school selector must not leak schools outside the user's membership."""
        headers = auth_headers("adminA@example.com", "StrongPass123")
        response = client.get("/api/v1/schools?limit=200", headers=headers)
        assert response.status_code == 200, response.text
        school_ids = {row["id"] for row in response.json()}
        assert school_ids == {str(school_a)}
        assert str(school_b) not in school_ids


# ---- Academic Year Isolation Tests ----

class TestAcademicYearIsolation:
    """Test that academic years are properly scoped to schools."""

    def test_create_academic_year_for_school_a(self, client, auth_headers, seeded_rbac, db_session, school_a):
        """SUPER_ADMIN can create academic year for School A."""
        make_user(email="super@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
        headers = auth_headers("super@example.com", "StrongPass123")
        
        payload = {
            "name": "2025 Academic Year",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31"
        }
        response = client.post(f"/api/v1/academic-years?school_id={school_a}", headers=headers, json=payload)
        assert response.status_code == 201

    def test_invalid_date_range_rejected(self, client, auth_headers, seeded_rbac, db_session, school_a):
        """Academic year with end_date before start_date is rejected."""
        make_user(email="super@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
        headers = auth_headers("super@example.com", "StrongPass123")
        
        payload = {
            "name": "Invalid Year",
            "start_date": "2025-12-31",
            "end_date": "2025-01-01"  # Before start_date
        }
        response = client.post(f"/api/v1/academic-years?school_id={school_a}", headers=headers, json=payload)
        assert response.status_code == 400
        assert "INVALID_DATE_RANGE" in response.json()["error"]["code"]


# ---- Term Isolation Tests ----

class TestTermIsolation:
    """Test that terms are properly scoped and validated."""

    def test_term_must_be_within_academic_year(self, client, auth_headers, seeded_rbac, db_session, school_a):
        """Term dates outside academic year are rejected."""
        make_user(email="super@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
        headers = auth_headers("super@example.com", "StrongPass123")
        
        # Create academic year
        ay_payload = {
            "name": "2025 Academic Year",
            "start_date": "2025-01-01",
            "end_date": "2025-12-31"
        }
        ay_response = client.post(f"/api/v1/academic-years?school_id={school_a}", headers=headers, json=ay_payload)
        ay_id = ay_response.json()["id"]
        
        # Try to create term outside academic year
        term_payload = {
            "name": "Invalid Term",
            "term_number": 1,
            "start_date": "2024-01-01",  # Before academic year
            "end_date": "2024-03-31"
        }
        response = client.post(f"/api/v1/terms?academic_year_id={ay_id}", headers=headers, json=term_payload)
        assert response.status_code == 400
        assert "TERM_OUTSIDE_ACADEMIC_YEAR" in response.json()["error"]["code"]


# ---- Class-Subject Cross-School Tests ----

class TestClassSubjectIsolation:
    """Test that class-subject assignments cannot cross school boundaries."""

    def test_cannot_assign_subject_from_different_school(
        self, client, auth_headers, seeded_rbac, db_session, school_a, school_b
    ):
        """Cannot assign a subject from School B to a class from School A."""
        make_user(email="super@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
        headers = auth_headers("super@example.com", "StrongPass123")
        
        # Create class in School A
        class_payload = {"name": "Form 1A", "code": "F1A", "level": 1}
        class_response = client.post(f"/api/v1/classes?school_id={school_a}", headers=headers, json=class_payload)
        class_id = class_response.json()["id"]
        
        # Create subject in School B
        subject_payload = {"name": "Mathematics", "code": "MAT101"}
        subject_response = client.post(f"/api/v1/subjects?school_id={school_b}", headers=headers, json=subject_payload)
        subject_id = subject_response.json()["id"]
        
        # Try to assign - should fail
        assign_payload = {"class_id": class_id, "subject_id": subject_id}
        response = client.post("/api/v1/class-subjects", headers=headers, json=assign_payload)
        assert response.status_code == 400
        assert "CROSS_SCHOOL_ASSIGNMENT_DENIED" in response.json()["error"]["code"]

    def test_can_assign_within_same_school(
        self, client, auth_headers, seeded_rbac, db_session, school_a
    ):
        """Can assign subject to class within the same school."""
        make_user(email="super@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
        headers = auth_headers("super@example.com", "StrongPass123")
        
        # Create class in School A
        class_payload = {"name": "Form 1A", "code": "F1A", "level": 1}
        class_response = client.post(f"/api/v1/classes?school_id={school_a}", headers=headers, json=class_payload)
        class_id = class_response.json()["id"]
        
        # Create subject in School A
        subject_payload = {"name": "Mathematics", "code": "MAT101"}
        subject_response = client.post(f"/api/v1/subjects?school_id={school_a}", headers=headers, json=subject_payload)
        subject_id = subject_response.json()["id"]
        
        # Assign - should succeed
        assign_payload = {"class_id": class_id, "subject_id": subject_id}
        response = client.post("/api/v1/class-subjects", headers=headers, json=assign_payload)
        assert response.status_code == 201


# ---- Duplicate Prevention Tests ----

class TestDuplicatePrevention:
    """Test that duplicates are properly prevented."""

    def test_duplicate_class_code_in_same_school_rejected(
        self, client, auth_headers, seeded_rbac, db_session, school_a
    ):
        """Duplicate class codes within the same school are rejected."""
        make_user(email="super@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
        headers = auth_headers("super@example.com", "StrongPass123")
        
        payload = {"name": "Form 1A", "code": "F1A", "level": 1}
        client.post(f"/api/v1/classes?school_id={school_a}", headers=headers, json=payload)
        
        # Try duplicate
        response = client.post(f"/api/v1/classes?school_id={school_a}", headers=headers, json=payload)
        assert response.status_code == 409
        assert "CLASS_CODE_EXISTS" in response.json()["error"]["code"]

    def test_duplicate_subject_code_in_same_school_rejected(
        self, client, auth_headers, seeded_rbac, db_session, school_a
    ):
        """Duplicate subject codes within the same school are rejected."""
        make_user(email="super@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
        headers = auth_headers("super@example.com", "StrongPass123")
        
        payload = {"name": "Mathematics", "code": "MAT101"}
        client.post(f"/api/v1/subjects?school_id={school_a}", headers=headers, json=payload)
        
        # Try duplicate
        response = client.post(f"/api/v1/subjects?school_id={school_a}", headers=headers, json=payload)
        assert response.status_code == 409
        assert "SUBJECT_CODE_EXISTS" in response.json()["error"]["code"]

    def test_same_class_code_different_schools_allowed(
        self, client, auth_headers, seeded_rbac, db_session, school_a, school_b
    ):
        """Same class code in different schools is allowed."""
        make_user(email="super@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
        headers = auth_headers("super@example.com", "StrongPass123")
        
        payload = {"name": "Form 1A", "code": "F1A", "level": 1}
        client.post(f"/api/v1/classes?school_id={school_a}", headers=headers, json=payload)
        
        # Same code in different school should work
        response = client.post(f"/api/v1/classes?school_id={school_b}", headers=headers, json=payload)
        assert response.status_code == 201