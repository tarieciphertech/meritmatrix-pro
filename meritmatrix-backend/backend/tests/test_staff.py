"""Staff CRUD and authorization tests."""
import pytest

from app.models.staff import Staff, EmploymentStatus
from app.models.school import School


def test_create_staff(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can create a staff member."""
    school = School(name="Test School", code="TEST001", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {
        "staff_number": "STF001",
        "first_name": "John",
        "last_name": "Doe",
    }
    response = client.post(f"/api/v1/staff?school_id={school.id}", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["staff_number"] == "STF001"
    assert data["first_name"] == "John"


def test_get_staff(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can read a staff member."""
    school = School(name="Test School", code="TEST002", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    staff = Staff(school_id=school.id, staff_number="STF002", first_name="Jane", last_name="Doe")
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.get(f"/api/v1/staff/{staff.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["staff_number"] == "STF002"


def test_list_staff(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can list staff for a school."""
    school = School(name="Test School", code="TEST003", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    for i in range(3):
        staff = Staff(school_id=school.id, staff_number=f"STF00{i}", first_name=f"First{i}", last_name="Last")
        db_session.add(staff)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.get(f"/api/v1/staff?school_id={school.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_update_staff(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can update a staff member."""
    school = School(name="Test School", code="TEST004", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    staff = Staff(school_id=school.id, staff_number="STF004", first_name="Jane", last_name="Doe")
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {"first_name": "Janet"}
    response = client.patch(f"/api/v1/staff/{staff.id}", headers=headers, json=payload)
    assert response.status_code == 200
    assert response.json()["first_name"] == "Janet"


def test_archive_staff(client, make_user, auth_headers, seeded_rbac, db_session):
    """SUPER_ADMIN can archive a staff member."""
    school = School(name="Test School", code="TEST005", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    staff = Staff(school_id=school.id, staff_number="STF005", first_name="Jane", last_name="Doe")
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.delete(f"/api/v1/staff/{staff.id}", headers=headers)
    assert response.status_code == 204

    db_session.refresh(staff)
    assert staff.is_active is False


def test_duplicate_staff_number_rejected(client, make_user, auth_headers, seeded_rbac, db_session):
    """Duplicate staff numbers within the same school are rejected."""
    school = School(name="Test School", code="TEST006", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    staff = Staff(school_id=school.id, staff_number="DUP001", first_name="First", last_name="Staff")
    db_session.add(staff)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {"staff_number": "DUP001", "first_name": "Second", "last_name": "Staff"}
    response = client.post(f"/api/v1/staff?school_id={school.id}", headers=headers, json=payload)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DUPLICATE_STAFF_NUMBER"


def test_same_staff_number_different_schools_allowed(client, make_user, auth_headers, seeded_rbac, db_session):
    """Same staff number is allowed in different schools."""
    school_a = School(name="School A", code="SCHLA01", city="City", country="Country")
    school_b = School(name="School B", code="SCHLB01", city="City", country="Country")
    db_session.add_all([school_a, school_b])
    db_session.commit()

    staff_a = Staff(school_id=school_a.id, staff_number="SAME001", first_name="A", last_name="Staff")
    staff_b = Staff(school_id=school_b.id, staff_number="SAME001", first_name="B", last_name="Staff")
    db_session.add_all([staff_a, staff_b])
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    response_a = client.get(f"/api/v1/staff/{staff_a.id}", headers=headers)
    response_b = client.get(f"/api/v1/staff/{staff_b.id}", headers=headers)
    assert response_a.status_code == 200
    assert response_b.status_code == 200


def test_unauthenticated_cannot_access_staff(client):
    """Unauthenticated requests are rejected."""
    response = client.get("/api/v1/staff?school_id=00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401


def test_user_without_permission_cannot_create_staff(client, make_user, auth_headers, seeded_rbac, db_session):
    """Users without staff.create permission are rejected."""
    school = School(name="Test School", code="TEST007", city="City", country="Country")
    db_session.add(school)
    db_session.commit()

    make_user(email="student@example.com", password="StrongPass123", role_name="STUDENT")
    headers = auth_headers("student@example.com", "StrongPass123")

    payload = {"staff_number": "STF001", "first_name": "Test", "last_name": "Staff"}
    response = client.post(f"/api/v1/staff?school_id={school.id}", headers=headers, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_school_id_cannot_be_changed(client, make_user, auth_headers, seeded_rbac, db_session):
    """school_id cannot be changed through PATCH."""
    school_a = School(name="School A", code="SCHLA02", city="City", country="Country")
    school_b = School(name="School B", code="SCHLB02", city="City", country="Country")
    db_session.add_all([school_a, school_b])
    db_session.commit()

    staff = Staff(school_id=school_a.id, staff_number="STF008", first_name="Test", last_name="Staff")
    db_session.add(staff)
    db_session.commit()

    make_user(email="admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("admin@example.com", "StrongPass123")

    payload = {"school_id": str(school_b.id)}
    response = client.patch(f"/api/v1/staff/{staff.id}", headers=headers, json=payload)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SCHOOL_CHANGE_DENIED"

    db_session.refresh(staff)
    assert staff.school_id == school_a.id

def test_create_staff_login_requires_initial_password_change(client, make_user, auth_headers, seeded_rbac, db_session):
    """Provisioning links a least-privilege teacher login with onboarding enabled."""
    from app.models.user import User

    school = School(name="Onboarding School", code="ONBOARD1", city="City", country="Country")
    db_session.add(school)
    db_session.commit()
    db_session.refresh(school)

    staff = Staff(
        school_id=school.id,
        staff_number="ONBOARD-01",
        first_name="Taylor",
        last_name="Teacher",
        email="taylor.teacher@example.com",
    )
    db_session.add(staff)
    db_session.commit()
    db_session.refresh(staff)

    make_user(email="onboarding-admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("onboarding-admin@example.com", "StrongPass123")

    response = client.post(
        f"/api/v1/staff/{staff.id}/account",
        headers=headers,
        json={"password": "TempPass123"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "taylor.teacher@example.com"
    assert "password" not in body
    assert "password_hash" not in body

    db_session.refresh(staff)
    account = db_session.query(User).filter(User.id == staff.user_id).one()
    assert account.must_change_password is True
    assert account.is_active is True
