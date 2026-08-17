"""Guardian CRUD and authorization tests."""
import pytest

from app.models.guardian import Guardian
from app.models.school import School


# ---- CRUD Tests ----

def test_create_guardian(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can create a guardian."""
    school = School(name="Test School", code="TEST001", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "phone": "+1-555-0100",
    }
    response = client.post(f"/api/v1/guardians?school_id={school.id}", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["is_active"] is True


def test_get_guardian(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can read a guardian."""
    school = School(name="Test School", code="TEST002", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    guardian = Guardian(school_id=school.id, first_name="Jane", last_name="Doe", phone="+1-555-0101")
    db_session.add(guardian)
    db_session.commit()
    db_session.refresh(guardian)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.get(f"/api/v1/guardians/{guardian.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Jane"


def test_list_guardians(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can list guardians for a school."""
    school = School(name="Test School", code="TEST003", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    for i in range(3):
        guardian = Guardian(school_id=school.id, first_name=f"First{i}", last_name="Last", phone=f"+1-555-0{i}")
        db_session.add(guardian)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.get(f"/api/v1/guardians?school_id={school.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_update_guardian(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can update a guardian."""
    school = School(name="Test School", code="TEST004", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    guardian = Guardian(school_id=school.id, first_name="Jane", last_name="Doe", phone="+1-555-0104")
    db_session.add(guardian)
    db_session.commit()
    db_session.refresh(guardian)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {"first_name": "Janet"}
    response = client.patch(f"/api/v1/guardians/{guardian.id}", headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Janet"


def test_archive_guardian(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can archive a guardian."""
    school = School(name="Test School", code="TEST005", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    guardian = Guardian(school_id=school.id, first_name="Jane", last_name="Doe", phone="+1-555-0105")
    db_session.add(guardian)
    db_session.commit()
    db_session.refresh(guardian)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.delete(f"/api/v1/guardians/{guardian.id}", headers=headers)
    assert response.status_code == 204

    db_session.refresh(guardian)
    assert guardian.is_active is False


# ---- Authorization Tests ----

def test_unauthenticated_cannot_access_guardians(client):
    """Unauthenticated requests are rejected."""
    response = client.get("/api/v1/guardians?school_id=00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


def test_user_without_permission_cannot_create_guardian(client, make_user, auth_headers, seeded_rbac, db_session):
    """Users without guardians.create permission are rejected."""
    school = School(name="Test School", code="TEST006", city="City", country="Country")
    db_session.add(school)
    db_session.commit()

    make_user(email="student@example.com", password="StrongPass123", role_name="STUDENT")
    headers = auth_headers("student@example.com", "StrongPass123")

    payload = {"first_name": "Test", "last_name": "Guardian", "phone": "+1-555-0100"}
    response = client.post(f"/api/v1/guardians?school_id={school.id}", headers=headers, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_school_id_cannot_be_changed(client, make_user, auth_headers, seeded_rbac, db_session):
    """school_id cannot be changed through PATCH."""
    school_a = School(name="School A", code="SCHLA01", city="City", country="Country")
    school_b = School(name="School B", code="SCHLB01", city="City", country="Country")
    db_session.add_all([school_a, school_b])
    db_session.commit()

    guardian = Guardian(school_id=school_a.id, first_name="Test", last_name="Guardian", phone="+1-555-0100")
    db_session.add(guardian)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {"school_id": str(school_b.id)}
    response = client.patch(f"/api/v1/guardians/{guardian.id}", headers=headers, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SCHOOL_CHANGE_DENIED"

    db_session.refresh(guardian)
    assert guardian.school_id == school_a.id