"""Dedicated school-admin provisioning and tenant-isolation regression tests."""

def _create_school(client, headers, name, code):
    response = client.post(
        "/api/v1/schools",
        headers=headers,
        json={"name": name, "code": code, "city": "Gaborone", "country": "Botswana"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_super_admin_provisions_school_admin_and_school_admin_is_tenant_scoped(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    make_user(email="platform-admin@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    platform_headers = auth_headers("platform-admin@example.com", "StrongPass123")
    school_a = _create_school(client, platform_headers, "School A", "SCHOOL-A")
    school_b = _create_school(client, platform_headers, "School B", "SCHOOL-B")

    created = client.post(
        f"/api/v1/schools/{school_a['id']}/admin-account",
        headers=platform_headers,
        json={
            "first_name": "Amina",
            "last_name": "Administrator",
            "email": "amina.admin@example.com",
            "password": "SchoolAdminStrong123!",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["role"] == "SCHOOL_ADMIN"
    assert created.json()["school_id"] == school_a["id"]
    assert created.json()["must_change_password"] is True

    duplicate = client.post(
        f"/api/v1/schools/{school_a['id']}/admin-account",
        headers=platform_headers,
        json={
            "first_name": "Second",
            "last_name": "Administrator",
            "email": "second.admin@example.com",
            "password": "SchoolAdminStrong123!",
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "SCHOOL_ADMIN_EXISTS"

    admin_headers = auth_headers("amina.admin@example.com", "SchoolAdminStrong123!")
    first_attempt = client.get(
        f"/api/v1/staff?school_id={school_a['id']}", headers=admin_headers
    )
    assert first_attempt.status_code == 403
    assert first_attempt.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    changed = client.post(
        "/api/v1/auth/change-password",
        headers=admin_headers,
        json={
            "current_password": "SchoolAdminStrong123!",
            "new_password": "SchoolAdminNewPass456!",
        },
    )
    assert changed.status_code == 200, changed.text
    admin_headers = {"Authorization": f"Bearer {changed.json()['access_token']}"}

    school_list = client.get("/api/v1/schools?limit=200", headers=admin_headers)
    assert school_list.status_code == 200, school_list.text
    assert {row["id"] for row in school_list.json()} == {school_a["id"]}

    own_school = client.get(f"/api/v1/schools/{school_a['id']}", headers=admin_headers)
    assert own_school.status_code == 200, own_school.text
    other_school = client.get(f"/api/v1/schools/{school_b['id']}", headers=admin_headers)
    assert other_school.status_code == 403
    assert other_school.json()["error"]["code"] == "SCHOOL_ACCESS_DENIED"

    # School administrators can configure their school but cannot rename or deactivate it.
    configured = client.patch(
        f"/api/v1/schools/{school_a['id']}",
        headers=admin_headers,
        json={"timezone": "Africa/Gaborone", "currency": "BWP"},
    )
    assert configured.status_code == 200, configured.text
    assert configured.json()["currency"] == "BWP"

    rename = client.patch(
        f"/api/v1/schools/{school_a['id']}",
        headers=admin_headers,
        json={"name": "Attempted Rename"},
    )
    assert rename.status_code == 403
    assert rename.json()["error"]["code"] == "PLATFORM_SCHOOL_FIELDS_RESTRICTED"

    # Staff creation is school-scoped and remains available to the school admin.
    staff = client.post(
        f"/api/v1/staff?school_id={school_a['id']}",
        headers=admin_headers,
        json={
            "staff_number": "A-001",
            "first_name": "Tariro",
            "last_name": "Teacher",
            "email": "tariro.teacher@example.com",
            "job_title": "Teacher",
        },
    )
    assert staff.status_code == 201, staff.text
    outside_staff = client.get(
        f"/api/v1/staff?school_id={school_b['id']}", headers=admin_headers
    )
    assert outside_staff.status_code == 403
    assert outside_staff.json()["error"]["code"] == "SCHOOL_ACCESS_DENIED"

    # Global user endpoints are not available to a school admin.
    users = client.get("/api/v1/users", headers=admin_headers)
    assert users.status_code == 403


def test_only_super_admin_can_provision_school_admin(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    make_user(email="school-creator@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    super_headers = auth_headers("school-creator@example.com", "StrongPass123")
    school = _create_school(client, super_headers, "Protected School", "PROTECTED")

    make_user(email="ordinary-school-admin@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    # This account is not a platform super-admin and has no system.admin permission.
    ordinary_headers = auth_headers("ordinary-school-admin@example.com", "StrongPass123")
    response = client.post(
        f"/api/v1/schools/{school['id']}/admin-account",
        headers=ordinary_headers,
        json={
            "first_name": "Unauthorized",
            "last_name": "Attempt",
            "email": "unauthorized.admin@example.com",
            "password": "SchoolAdminStrong123!",
        },
    )
    assert response.status_code == 403



def test_school_admin_with_multiple_school_memberships_is_denied(
    make_user, seeded_rbac, db_session
):
    from app.models.school import School
    from app.models.user_school import UserSchool
    from app.services.user_school_service import UserSchoolService

    admin = make_user(email="multi-school-admin@example.com", role_name="SCHOOL_ADMIN")
    school_a = School(name="Multi Admin A", code="MULTI-A", city="Gaborone", country="Botswana")
    school_b = School(name="Multi Admin B", code="MULTI-B", city="Gaborone", country="Botswana")
    db_session.add_all([school_a, school_b])
    db_session.flush()
    db_session.add_all([
        UserSchool(user_id=admin.id, school_id=school_a.id, school_role="SCHOOL_ADMIN"),
        UserSchool(user_id=admin.id, school_id=school_b.id, school_role="SCHOOL_ADMIN"),
    ])
    db_session.commit()

    service = UserSchoolService(db_session)
    assert service.is_user_member_of_school(admin.id, school_a.id) is False
    assert service.is_user_member_of_school(admin.id, school_b.id) is False
    assert service.get_schools_for_user(admin.id) == []



def test_school_admin_cannot_be_assigned_to_a_second_school(
    make_user, seeded_rbac, db_session
):
    import pytest

    from app.models.school import School
    from app.services.user_school_service import UserSchoolService
    from app.utils.errors import ConflictError

    admin = make_user(email="single-school-admin@example.com", role_name="SCHOOL_ADMIN")
    school_a = School(name="Single Admin A", code="SINGLE-A", city="Gaborone", country="Botswana")
    school_b = School(name="Single Admin B", code="SINGLE-B", city="Gaborone", country="Botswana")
    db_session.add_all([school_a, school_b])
    db_session.flush()

    service = UserSchoolService(db_session)
    service.add_user_to_school(admin.id, school_a.id, "SCHOOL_ADMIN")
    db_session.commit()

    with pytest.raises(ConflictError) as exc:
        service.add_user_to_school(admin.id, school_b.id, "SCHOOL_ADMIN")
    assert exc.value.code == "SCHOOL_ADMIN_SINGLE_SCHOOL"

    # The failed attempt must not change the existing single-school membership.
    db_session.rollback()
    assert service.is_user_member_of_school(admin.id, school_a.id) is True
    assert service.is_user_member_of_school(admin.id, school_b.id) is False
