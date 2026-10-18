"""School CRUD and authorization tests."""
import uuid

import pytest

from app.models.school import School
from app.models.user_school import UserSchool
from app.schemas.school import SchoolCreate


# ---- CRUD Tests ----

def test_create_school(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can create a school."""
    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "name": "Test School",
        "code": "TEST001",
        "city": "Test City",
        "country": "Test Country",
        "institution_type": "high_school",
    }
    response = client.post("/api/v1/schools", headers=headers, json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test School"
    assert data["code"] == "TEST001"
    assert data["is_active"] is True


def test_list_schools(client, make_user, auth_headers, seeded_rbac, db_session):
    """A school administrator can list only their single assigned school."""
    user = make_user(email="reader@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    school = School(name="Assigned School", code="ASSIGNED001", city="City", country="Country")
    other_school = School(name="Other School", code="OTHER001", city="City", country="Country")
    db_session.add_all([school, other_school])
    db_session.flush()
    db_session.add(UserSchool(user_id=user.id, school_id=school.id, school_role="SCHOOL_ADMIN"))
    db_session.commit()
    headers = auth_headers("reader@example.com", "StrongPass123")

    response = client.get("/api/v1/schools", headers=headers)
    assert response.status_code == 200, response.text
    assert [row["id"] for row in response.json()] == [str(school.id)]

def test_read_school(client, make_user, auth_headers, seeded_rbac, db_session):
    """Users with schools.read can read a school."""
    make_user(email="reader@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("reader@example.com", "StrongPass123")

    school = School(name="Test School", code="TEST002", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    response = client.get(f"/api/v1/schools/{school.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["code"] == "TEST002"


def test_update_school(client, make_user, auth_headers, seeded_rbac, db_session):
    """Users with schools.update can update a school."""
    make_user(email="updater@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("updater@example.com", "StrongPass123")

    school = School(name="Test School", code="TEST003", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    payload = {"name": "Updated School Name"}
    response = client.patch(f"/api/v1/schools/{school.id}", headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json()["name"] == "Updated School Name"


def test_deactivate_school(client, make_user, auth_headers, seeded_rbac, db_session):
    """Users with schools.update can deactivate a school."""
    make_user(email="updater@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("updater@example.com", "StrongPass123")

    school = School(name="Test School", code="TEST004", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    response = client.delete(f"/api/v1/schools/{school.id}", headers=headers)
    assert response.status_code == 204

    # Verify it's deactivated
    db_session.refresh(school)
    assert school.is_active is False


# ---- Validation Tests ----

def test_duplicate_school_code_rejected(client, make_user, auth_headers, seeded_rbac, db_session):
    """Duplicate school codes are rejected."""
    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    # Create first school
    school = School(name="School 1", code="DUP001", city="City", country="Country")
    db_session.add(school)
    db_session.commit()

    # Try to create with same code
    payload = {"name": "School 2", "code": "DUP001", "city": "City", "country": "Country"}
    response = client.post("/api/v1/schools", headers=headers, json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SCHOOL_CODE_EXISTS"


# ---- Authorization Tests ----

def test_unauthenticated_cannot_create_school(client):
    """Unauthenticated requests are rejected."""
    payload = {"name": "Test", "code": "UNAUTH01"}
    response = client.post("/api/v1/schools", json=payload)
    assert response.status_code == 401


def test_user_without_permission_cannot_create_school(client, make_user, auth_headers, seeded_rbac):
    """Users without schools.create permission are rejected."""
    make_user(email="student@example.com", password="StrongPass123", role_name="STUDENT")
    headers = auth_headers("student@example.com", "StrongPass123")

    payload = {"name": "Test", "code": "UNAUTH02"}
    response = client.post("/api/v1/schools", headers=headers, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"