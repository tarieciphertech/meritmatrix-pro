"""
Password hashing and verification.

Uses Argon2id (via passlib) — the recommended modern password hashing
algorithm. Never store or log plaintext passwords or hashes anywhere
outside this module's boundary.
"""
from passlib.context import CryptContext
from passlib.exc import UnknownHashError

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# A precomputed valid hash of an arbitrary, unguessable string. Used to make
# authentication attempts against unknown emails take roughly the same time
# as attempts against real accounts, reducing user-enumeration via timing.
DUMMY_PASSWORD_HASH = pwd_context.hash("dummy-password-for-timing-normalization")


class WeakPasswordError(ValueError):
    """Raised when a candidate password does not meet minimum strength rules."""


def validate_password_strength(password: str) -> None:
    """Minimum password validation. Raises WeakPasswordError if not met."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."
        )
    if len(password) > MAX_PASSWORD_LENGTH:
        raise WeakPasswordError(
            f"Password must be at most {MAX_PASSWORD_LENGTH} characters long."
        )
    if password.isdigit() or password.isalpha():
        raise WeakPasswordError(
            "Password must contain a mix of letters, numbers, or symbols."
        )


def hash_password(password: str) -> str:
    """Hash a plaintext password. Raises WeakPasswordError if too weak."""
    validate_password_strength(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Safely verify a plaintext password against a stored hash."""
    try:
        return pwd_context.verify(plain_password, password_hash)
    except (UnknownHashError, ValueError):
        return False
