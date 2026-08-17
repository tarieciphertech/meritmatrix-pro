"""Password hashing and verification tests."""
import pytest

from app.services.security import (
    WeakPasswordError,
    hash_password,
    validate_password_strength,
    verify_password,
)


def test_hash_password_produces_a_hash_different_from_plaintext():
    plaintext = "CorrectHorse123"
    hashed = hash_password(plaintext)
    assert hashed != plaintext
    assert hashed.startswith("$argon2")


def test_hash_password_is_not_deterministic_across_calls():
    # Argon2 includes a random salt, so hashing the same password twice
    # must produce two different hashes.
    h1 = hash_password("CorrectHorse123")
    h2 = hash_password("CorrectHorse123")
    assert h1 != h2


def test_verify_password_succeeds_with_correct_password():
    hashed = hash_password("CorrectHorse123")
    assert verify_password("CorrectHorse123", hashed) is True


def test_verify_password_fails_with_incorrect_password():
    hashed = hash_password("CorrectHorse123")
    assert verify_password("WrongPassword999", hashed) is False


def test_verify_password_handles_garbage_hash_safely():
    assert verify_password("anything", "not-a-real-hash") is False


@pytest.mark.parametrize(
    "weak_password",
    [
        "short1",  # too short
        "alllettersnodigits",  # all alpha
        "12345678901234",  # all digits
    ],
)
def test_weak_passwords_are_rejected(weak_password):
    with pytest.raises(WeakPasswordError):
        validate_password_strength(weak_password)


def test_strong_password_passes_validation():
    validate_password_strength("Reasonably-Strong9")  # should not raise
