"""Regression tests for guardian phone identifier normalization and login."""
import pytest

from app.routers.guardian_accounts import _phone
from app.services.auth_service import AuthService


@pytest.mark.parametrize(
    ("entered", "expected"),
    [
        ("0771234567", "+263771234567"),
        ("263771234567", "+263771234567"),
        ("+263771234567", "+263771234567"),
        ("00263771234567", "+263771234567"),
        (" 077 123 4567 ", "+263771234567"),
    ],
)
def test_zimbabwe_phone_formats_are_canonicalized(entered, expected):
    assert _phone(entered) == expected


def test_guardian_can_login_using_local_zimbabwe_phone_format(make_user, db_session):
    user = make_user(email="guardian-test@example.com", password="StrongPass123")
    user.phone = "+263771234567"
    db_session.commit()

    authenticated = AuthService(db_session).authenticate_user(
        "0771234567", "StrongPass123"
    )

    assert authenticated.id == user.id


def test_guardian_can_login_using_international_phone_format(make_user, db_session):
    user = make_user(email="guardian-intl@example.com", password="StrongPass123")
    user.phone = "+263771234567"
    db_session.commit()

    authenticated = AuthService(db_session).authenticate_user(
        "+263 77 123 4567", "StrongPass123"
    )

    assert authenticated.id == user.id
