"""Access-token and refresh-token behavior tests."""
import uuid
from datetime import datetime, timedelta, timezone

from app.services import jwt_service
from app.services.auth_service import AuthService


def test_valid_access_token_authenticates_me_endpoint(client, make_user):
    make_user(email="tokentest@example.com", password="StrongPass123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "tokentest@example.com", "password": "StrongPass123"},
    )
    access_token = login.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "tokentest@example.com"


def test_invalid_access_token_is_rejected(client):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_ACCESS_TOKEN"


def test_missing_access_token_is_rejected(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "NOT_AUTHENTICATED"


def test_expired_access_token_is_rejected(client, make_user):
    user = make_user(email="expiredtoken@example.com", password="StrongPass123")

    # Build a token that already expired, bypassing the normal short TTL.
    settings_module = jwt_service.get_settings()
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": str(user.id),
        "type": jwt_service.ACCESS_TOKEN_TYPE,
        "iat": int((now - timedelta(minutes=30)).timestamp()),
        "exp": int((now - timedelta(minutes=15)).timestamp()),
        "jti": str(uuid.uuid4()),
    }
    from jose import jwt as jose_jwt

    expired_token = jose_jwt.encode(
        expired_payload, settings_module.JWT_SECRET, algorithm=settings_module.JWT_ALGORITHM
    )

    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_ACCESS_TOKEN"


def test_refresh_token_issues_new_working_access_token(client, make_user):
    make_user(email="refreshworks@example.com", password="StrongPass123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "refreshworks@example.com", "password": "StrongPass123"},
    )
    refresh_token = login.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body

    # The new access token must actually work.
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200


def test_refresh_token_rotates_to_a_new_value(client, make_user):
    make_user(email="rotatetest@example.com", password="StrongPass123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "rotatetest@example.com", "password": "StrongPass123"},
    )
    old_refresh = login.json()["refresh_token"]

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    new_refresh = response.json()["refresh_token"]

    assert new_refresh != old_refresh


def test_old_refresh_token_cannot_be_reused_after_rotation(client, make_user):
    make_user(email="noreuse@example.com", password="StrongPass123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "noreuse@example.com", "password": "StrongPass123"},
    )
    old_refresh = login.json()["refresh_token"]

    first = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "REFRESH_TOKEN_REUSE_DETECTED"


def test_reuse_of_revoked_token_kills_the_whole_family(client, make_user):
    """Reusing a rotated-away token must also kill the token it was rotated INTO."""
    make_user(email="familykill@example.com", password="StrongPass123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "familykill@example.com", "password": "StrongPass123"},
    )
    original_refresh = login.json()["refresh_token"]

    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": original_refresh})
    newest_refresh = rotated.json()["refresh_token"]

    # Replay the original (now-revoked) token -> triggers family-wide revocation.
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": original_refresh})
    assert replay.status_code == 401

    # The newest token, though never used, should now also be dead.
    followup = client.post("/api/v1/auth/refresh", json={"refresh_token": newest_refresh})
    assert followup.status_code == 401


def test_revoked_refresh_token_fails(client, make_user):
    make_user(email="revoketest@example.com", password="StrongPass123")
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "revoketest@example.com", "password": "StrongPass123"},
    )
    refresh_token = login.json()["refresh_token"]

    logout_resp = client.post("/api/v1/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 204

    refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401


def test_expired_refresh_token_fails(db_session, make_user):
    user = make_user(email="expiredrefresh@example.com", password="StrongPass123")

    service = AuthService(db_session)
    raw_token, record = service.create_refresh_token(user)
    # Force it into the past.
    record.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.commit()

    import pytest

    from app.utils.errors import UnauthorizedError

    with pytest.raises(UnauthorizedError) as exc_info:
        service.rotate_refresh_token(raw_token)
    assert exc_info.value.code == "REFRESH_TOKEN_EXPIRED"


def test_invalid_refresh_token_string_is_rejected(client):
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "totally-made-up-token"}
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"
