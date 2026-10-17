"""Role-based access control tests."""


def test_unauthenticated_request_to_protected_endpoint_fails(client, seeded_rbac):
    response = client.get("/api/v1/users")
    assert response.status_code == 401


def test_school_admin_can_access_its_assigned_school(client, make_user, auth_headers, seeded_rbac, db_session):
    from app.models.school import School
    from app.models.user_school import UserSchool

    admin = make_user(
        email="admin@example.com",
        password="StrongPass123",
        role_name="SCHOOL_ADMIN",
    )
    school = School(name="RBAC School", code="RBAC-SCHOOL", city="Gaborone", country="Botswana")
    db_session.add(school)
    db_session.flush()
    db_session.add(UserSchool(user_id=admin.id, school_id=school.id, school_role="SCHOOL_ADMIN"))
    db_session.commit()
    headers = auth_headers("admin@example.com", "StrongPass123")

    response = client.get("/api/v1/schools/" + str(school.id), headers=headers)
    assert response.status_code == 200, response.text


def test_user_missing_permission_gets_403(client, make_user, auth_headers):
    # STUDENT role has no platform-wide user-management permissions.
    make_user(email="student1@example.com", password="StrongPass123", role_name="STUDENT")
    headers = auth_headers("student1@example.com", "StrongPass123")

    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "newperson@example.com",
            "password": "StrongPass123",
            "first_name": "New",
            "last_name": "Person",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_super_admin_system_admin_permission_grants_everything(client, make_user, auth_headers):
    make_user(email="root@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    headers = auth_headers("root@example.com", "StrongPass123")

    # SUPER_ADMIN holds system.admin, which should satisfy any permission
    # check, including ones not explicitly listed for the role.
    response = client.post(
        "/api/v1/users",
        headers=headers,
        json={
            "email": "created-by-admin@example.com",
            "password": "StrongPass123",
            "first_name": "Created",
            "last_name": "ByAdmin",
        },
    )
    assert response.status_code == 201


def test_user_with_no_roles_is_denied_permission_protected_endpoint(client, make_user, auth_headers):
    make_user(email="noroles@example.com", password="StrongPass123")  # no role_name given
    headers = auth_headers("noroles@example.com", "StrongPass123")

    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 403


def test_own_profile_endpoint_works_regardless_of_permissions(client, make_user, auth_headers):
    """GET /users/me only requires authentication, not a specific permission."""
    make_user(email="justme@example.com", password="StrongPass123")  # no roles/permissions
    headers = auth_headers("justme@example.com", "StrongPass123")

    response = client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "justme@example.com"
