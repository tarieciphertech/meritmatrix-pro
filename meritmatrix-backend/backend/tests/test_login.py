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
