"""
tests/test_auth/test_jwt.py

Unit tests for JWT creation, decoding, and edge cases.
Tests the security module in isolation (no DB, no HTTP).
"""
import time
from datetime import UTC, datetime, timedelta

import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    decode_access_token,
    extract_token_subject,
    hash_password,
    verify_password,
)


# ── Password Hashing ──────────────────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plain_text(self) -> None:
        """Hashed password must not equal the plain-text input."""
        plain = "MyPassword1"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_correct_password_verifies(self) -> None:
        """verify_password must return True for the correct password."""
        plain = "MyPassword1"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_wrong_password_fails(self) -> None:
        """verify_password must return False for a wrong password."""
        hashed = hash_password("MyPassword1")
        assert verify_password("WrongPassword1", hashed) is False

    def test_hash_is_unique_per_call(self) -> None:
        """Two hashes of the same password must differ (bcrypt uses random salts)."""
        plain = "MyPassword1"
        hash1 = hash_password(plain)
        hash2 = hash_password(plain)
        assert hash1 != hash2

    def test_bcrypt_prefix(self) -> None:
        """Hash must be a valid bcrypt hash string starting with $2b$."""
        hashed = hash_password("MyPassword1")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")


# ── JWT Creation ─────────────────────────────────────────────────────────────

class TestJWTCreation:
    def test_token_is_string(self) -> None:
        """create_access_token must return a non-empty string."""
        token = create_access_token(subject="user-123")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_has_three_parts(self) -> None:
        """A valid JWT has three dot-separated segments."""
        token = create_access_token(subject="user-123")
        parts = token.split(".")
        assert len(parts) == 3

    def test_token_contains_subject(self) -> None:
        """Decoded token must contain the correct 'sub' claim."""
        subject = "test-user-uuid"
        token = create_access_token(subject=subject)
        payload = decode_access_token(token)
        assert payload["sub"] == subject

    def test_token_contains_additional_claims(self) -> None:
        """Additional claims must be present in the decoded payload."""
        token = create_access_token(
            subject="user-123",
            additional_claims={"role": "ADMIN", "email": "admin@test.com"},
        )
        payload = decode_access_token(token)
        assert payload["role"] == "ADMIN"
        assert payload["email"] == "admin@test.com"

    def test_token_has_exp_and_iat(self) -> None:
        """Token must contain standard 'iat' and 'exp' claims."""
        token = create_access_token(subject="user-123")
        payload = decode_access_token(token)
        assert "iat" in payload
        assert "exp" in payload
        assert payload["exp"] > payload["iat"]

    def test_custom_expiry_respected(self) -> None:
        """Custom expires_delta must be used when provided."""
        custom_delta = timedelta(hours=2)
        token = create_access_token(subject="user-123", expires_delta=custom_delta)
        payload = decode_access_token(token)
        # exp should be approximately 2 hours from now
        now = datetime.now(UTC).timestamp()
        assert abs(payload["exp"] - (now + 7200)) < 10  # Allow 10s tolerance


# ── JWT Decoding & Edge Cases ─────────────────────────────────────────────────

class TestJWTDecoding:
    def test_expired_token_raises(self) -> None:
        """An expired token must raise JWTError."""
        token = create_access_token(
            subject="user-123",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        with pytest.raises(JWTError):
            decode_access_token(token)

    def test_tampered_token_raises(self) -> None:
        """A token with modified payload must raise JWTError."""
        token = create_access_token(subject="user-123")
        # Tamper with the payload segment
        parts = token.split(".")
        tampered = parts[0] + "." + parts[1] + "TAMPERED" + "." + parts[2]
        with pytest.raises(JWTError):
            decode_access_token(tampered)

    def test_invalid_string_raises(self) -> None:
        """A completely invalid string must raise JWTError."""
        with pytest.raises(JWTError):
            decode_access_token("not.a.jwt")

    def test_empty_string_raises(self) -> None:
        """An empty string must raise JWTError."""
        with pytest.raises(JWTError):
            decode_access_token("")


# ── extract_token_subject ─────────────────────────────────────────────────────

class TestExtractTokenSubject:
    def test_returns_subject_for_valid_token(self) -> None:
        """extract_token_subject must return the subject string for valid tokens."""
        token = create_access_token(subject="user-uuid-42")
        assert extract_token_subject(token) == "user-uuid-42"

    def test_returns_none_for_invalid_token(self) -> None:
        """extract_token_subject must return None for invalid tokens (no raise)."""
        result = extract_token_subject("completely.invalid.token")
        assert result is None

    def test_returns_none_for_expired_token(self) -> None:
        """extract_token_subject must return None for expired tokens (no raise)."""
        token = create_access_token(
            subject="user-123",
            expires_delta=timedelta(seconds=-1),
        )
        assert extract_token_subject(token) is None
