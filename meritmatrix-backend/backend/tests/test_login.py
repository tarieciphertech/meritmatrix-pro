"""POST /api/v1/auth/login tests."""


def test_login_with_valid_credentials_succeeds(client, make_user):
    make_user(email="valid@example.com", password="StrongPass123")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "valid@example.com", "password": "StrongPass123"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


def test_login_with_wrong_password_fails(client, make_user):
    make_user(email="wrongpw@example.com", password="StrongPass123")

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "wrongpw@example.com", "password": "NotTheRightOne1"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_with_unknown_email_fails(client, seeded_rbac):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "WhateverPass1"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_with_inactive_user_fails(client, make_user):
    make_user(email="inactive@example.com", password="StrongPass123", is_active=False)

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "StrongPass123"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_unknown_email_and_wrong_password_return_identical_error_body(client, make_user):
    """Generic errors must not leak whether the account exists."""
    make_user(email="exists@example.com", password="StrongPass123")

    unknown_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@example.com", "password": "WhateverPass1"},
    )
    wrong_pw_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "exists@example.com", "password": "WhateverPass1"},
    )

    assert unknown_resp.status_code == wrong_pw_resp.status_code == 401
    assert unknown_resp.json() == wrong_pw_resp.json()


def test_staff_first_login_requires_password_change_and_blocks_school_api(client, make_user, db_session):
    user = make_user(email="newteacher@example.com", password="TempPass123", role_name="TEACHER")
    user.must_change_password = True
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "newteacher@example.com", "password": "TempPass123"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["must_change_password"] is True
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True

    blocked = client.get(
        "/api/v1/staff?school_id=00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"


def test_password_change_clears_onboarding_gate(client, make_user, db_session):
    user = make_user(email="teacherchange@example.com", password="TempPass123", role_name="TEACHER")
    user.must_change_password = True
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacherchange@example.com", "password": "TempPass123"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    changed = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "TempPass123", "new_password": "NewStrongPass456"},
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["must_change_password"] is False

    new_headers = {"Authorization": f"Bearer {changed.json()['access_token']}"}
    me = client.get("/api/v1/auth/me", headers=new_headers)
    assert me.status_code == 200
    assert me.json()["must_change_password"] is False


def test_password_change_rejects_incorrect_current_password(client, make_user, db_session):
    user = make_user(email="teacherwrongcurrent@example.com", password="TempPass123", role_name="TEACHER")
    user.must_change_password = True
    db_session.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacherwrongcurrent@example.com", "password": "TempPass123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "WrongTemp123", "new_password": "NewStrongPass456"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "CURRENT_PASSWORD_INVALID"
