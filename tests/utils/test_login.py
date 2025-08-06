"""Test suite for kwik.utils.login."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from kwik.core.settings import get_settings
from kwik.utils.login import generate_password_reset_token, verify_password_reset_token

EMAIL = "test@example.com"


def test_generate_password_reset_token() -> None:
    """Test that a password reset token is generated correctly."""
    token = generate_password_reset_token(EMAIL)
    assert isinstance(token, str)
    decoded_token = jwt.decode(token, get_settings().SECRET_KEY, algorithms=["HS256"])
    assert decoded_token["sub"] == EMAIL
    assert "exp" in decoded_token
    assert "nbf" in decoded_token


def test_verify_password_reset_token() -> None:
    """Test that a valid password reset token is verified correctly."""
    token = generate_password_reset_token(EMAIL)
    assert verify_password_reset_token(token) == EMAIL


def test_verify_password_reset_token_expired() -> None:
    """Test that an expired password reset token raises an error."""
    now = datetime.now(tz=UTC)
    expired_exp = (now - timedelta(hours=1)).timestamp()
    token = jwt.encode(
        {"exp": expired_exp, "nbf": now - timedelta(hours=2), "sub": EMAIL},
        get_settings().SECRET_KEY,
        algorithm="HS256",
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        verify_password_reset_token(token)


def test_verify_password_reset_token_invalid_signature() -> None:
    """Test that a token with an invalid signature raises an error."""
    token = generate_password_reset_token(EMAIL)
    # Tamper with the token
    tampered_token = token + "invalid"
    with pytest.raises(jwt.PyJWTError):
        verify_password_reset_token(tampered_token)


def test_verify_password_reset_token_no_sub() -> None:
    """Test that a token with no subject returns None."""
    token = jwt.encode(
        {"exp": (datetime.now(tz=UTC) + timedelta(hours=1)).timestamp(), "nbf": datetime.now(tz=UTC)},
        get_settings().SECRET_KEY,
        algorithm="HS256",
    )
    assert verify_password_reset_token(token) is None
