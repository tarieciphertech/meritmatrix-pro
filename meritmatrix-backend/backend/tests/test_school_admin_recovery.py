"""Regression tests for school administrator login recovery."""
from app.models.user_school import UserSchool
from app.services.security import verify_password


def test_super_admin_can_reset_school_admin_password_and_force_rotation(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    make_user(email="platform-reset@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    admin = make_user(
        email="school-reset@example.com",
        password="InitialPassword123!",
        role_name="SCHOOL_ADMIN",
    )
    db_session.add(UserSchool(user_id=admin.id, school_id=school.id, school_role="SCHOOL_ADMIN"))
    db_session.commit()
    headers = auth_headers("platform-reset@example.com", "StrongPass123")

    response = client.post(
        f"/api/v1/schools/{school.id}/admin-account/reset-password",
        headers=headers,
        json={"password": "ReplacementPassword123!"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["email"] == "school-reset@example.com"
    assert response.json()["must_change_password"] is True

    db_session.refresh(admin)
    assert verify_password("ReplacementPassword123!", admin.password_hash)
    assert admin.must_change_password is True


def test_school_admin_cannot_reset_its_own_or_another_school_admin_password(
    client, make_user, auth_headers, seeded_rbac, db_session
):
    from app.models.school import School
    from app.models.user import User

    school_a = School(name="Scoped Academy A", code="SCOPED-A")
    school_b = School(name="Scoped Academy B", code="SCOPED-B")
    db_session.add_all([school_a, school_b])
    db_session.flush()
    make_user(email="scoped-admin-reset@example.com", password="StrongPass123", role_name="SCHOOL_ADMIN")
    admin = db_session.query(User).filter(User.email == "scoped-admin-reset@example.com").one()
    db_session.add(UserSchool(user_id=admin.id, school_id=school_a.id, school_role="SCHOOL_ADMIN"))
    db_session.commit()
    headers = auth_headers("scoped-admin-reset@example.com", "StrongPass123")

    response = client.post(
        f"/api/v1/schools/{school_b.id}/admin-account/reset-password",
        headers=headers,
        json={"password": "ReplacementPassword123!"},
    )
    assert response.status_code == 403, response.text
