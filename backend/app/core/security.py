import hashlib
import re
import secrets
import argon2
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

# Configure Argon2id hasher with stable production parameters
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    type=argon2.Type.ID,
)

# Precomputed dummy hash to prevent account existence disclosure through timing analysis
_DUMMY_ARGON2_HASH = _hasher.hash("dummy-constant-time-timing-salt")


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id."""
    return _hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against an Argon2id hash."""
    if not hashed_password:
        return False
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def dummy_verify_password(plain_password: str) -> bool:
    """
    Executes a real Argon2id verification against a dummy hash.
    Ensures login failure path takes consistent execution time regardless of whether
    institution, user, or password failed.
    """
    try:
        _hasher.verify(_DUMMY_ARGON2_HASH, plain_password)
    except Exception:
        pass
    return False


def generate_session_token() -> tuple[str, str]:
    """
    Generates a cryptographically random session token and its SHA-256 digest.
    Returns:
        (raw_token, token_hash)
    The raw_token is transmitted to the client in an HttpOnly cookie.
    Only the token_hash is persisted in the database.
    """
    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_session_token(raw_token)
    return raw_token, token_hash


def hash_session_token(raw_token: str) -> str:
    """Calculates SHA-256 digest of raw session token for database lookup."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    """Generates a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def generate_temporary_password(length: int = 12) -> str:
    """Generates a high-entropy temporary password compliant with policy."""
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        ok, _ = validate_password_strength(pwd)
        if ok:
            return pwd


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validates password meets minimum security criteria."""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    return True, ""
get_password_hash = hash_password
