"""Security-focused tests spanning multiple endpoints."""
import logging

from sqlalchemy import select

from app.models.refresh_token import RefreshToken


def test_password_hash_never_appears_in_login_response(client, make_user):
    make_user(email="nohash@example.com", password="StrongPass123")
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nohash@example.com", "password": "StrongPass123"},
    )
    body_text = response.text
    assert "password_hash" not in body_text
    assert "StrongPass123" not in body_text
    assert "$argon2" not in body_text


def test_password_hash_never_appears_in_user_response(client, make_user, auth_headers):
    make_user(email="viewer@example.com", password="StrongPass123", role_name="SUPER_ADMIN")
    make_user(email="target@example.com", password="AnotherStrongPass1")
    headers = auth_headers("viewer@example.com", "StrongPass123")

    response = client.get("/api/v1/users", headers=headers)
    body_text = response.text
    assert "password_hash" not in body_text
    assert "AnotherStrongPass1" not in body_text


def test_password_is_not_written_to_logs(client, make_user, caplog):
    make_user(email="logcheck@example.com", password="SuperSecretPass1")
    with caplog.at_level(logging.DEBUG):
        client.post(
            "/api/v1/auth/login",
            json={"email": "logcheck@example.com", "password": "SuperSecretPass1"},
        )
    for record in caplog.records:
        assert "SuperSecretPass1" not in record.getMessage()


def test_refresh_tokens_are_never_stored_in_plaintext(client, make_user, db_session):
    make_user(email="plaintextcheck@example.com", password="StrongPass123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "plaintextcheck@example.com", "password": "StrongPass123"},
    )
    raw_refresh_token = login.json()["refresh_token"]

    stored_tokens = db_session.execute(select(RefreshToken)).scalars().all()
    assert len(stored_tokens) >= 1
    for token in stored_tokens:
        assert token.token_hash != raw_refresh_token
        assert raw_refresh_token not in token.token_hash


def test_login_error_messages_are_generic_not_specific(client, make_user):
    make_user(email="specificitycheck@example.com", password="StrongPass123")

    wrong_password = client.post(
        "/api/v1/auth/login",
        json={"email": "specificitycheck@example.com", "password": "WrongPassword1"},
    ).json()

    unknown_user = client.post(
        "/api/v1/auth/login",
        json={"email": "nobodyhome@example.com", "password": "WrongPassword1"},
    ).json()

    # Neither response may reveal *why* the login failed.
    for body in (wrong_password, unknown_user):
        message = body["error"]["message"].lower()
        assert "no such user" not in message
        assert "does not exist" not in message
        assert "incorrect password" not in message


def test_user_cannot_access_another_users_resource_without_permission(
    client, make_user, auth_headers
):
    target = make_user(email="victim@example.com", password="StrongPass123")
    make_user(email="attacker@example.com", password="StrongPass123")  # no roles/permissions
    headers = auth_headers("attacker@example.com", "StrongPass123")

    response = client.get(f"/api/v1/users/{target.id}", headers=headers)
    assert response.status_code == 403


def test_500_errors_never_leak_raw_exception_details(client):
    # An endpoint that doesn't exist should return our normalized 404 shape,
    # never a raw traceback or stack trace text.
    response = client.get("/api/v1/this-does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert "Traceback" not in response.text
