"""Test suite for kwik.utils.login."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import jwt
import pytest

from kwik.core.security import ALGORITHM, generate_password_reset_token, verify_password_reset_token

if TYPE_CHECKING:
    from kwik.settings import BaseKwikSettings

EMAIL = "test@example.com"


def test_generate_password_reset_token(settings: BaseKwikSettings) -> None:
    """Test that a password reset token is generated correctly."""
    token = generate_password_reset_token(EMAIL, settings=settings)
    assert isinstance(token, str)
    decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded_token["sub"] == EMAIL
    assert "exp" in decoded_token
    assert "nbf" in decoded_token


def test_verify_password_reset_token(settings: BaseKwikSettings) -> None:
    """Test that a valid password reset token is verified correctly."""
    token = generate_password_reset_token(EMAIL, settings=settings)
    assert verify_password_reset_token(token, settings=settings) == EMAIL


def test_verify_password_reset_token_expired(settings: BaseKwikSettings) -> None:
    """Test that an expired password reset token raises an error."""
    now = datetime.now(tz=UTC)
    expired_exp = (now - timedelta(hours=1)).timestamp()
    token = jwt.encode(
        {"exp": expired_exp, "nbf": now - timedelta(hours=2), "sub": EMAIL},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        verify_password_reset_token(token, settings=settings)


def test_verify_password_reset_token_invalid_signature(settings: BaseKwikSettings) -> None:
    """Test that a token with an invalid signature raises an error."""
    token = generate_password_reset_token(EMAIL, settings=settings)
    # Tamper with the token
    tampered_token = token + "invalid"
    with pytest.raises(jwt.PyJWTError):
        verify_password_reset_token(tampered_token, settings=settings)


def test_verify_password_reset_token_no_sub(settings: BaseKwikSettings) -> None:
    """Test that a token with no subject returns None."""
    token = jwt.encode(
        {"exp": (datetime.now(tz=UTC) + timedelta(hours=1)).timestamp(), "nbf": datetime.now(tz=UTC)},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    assert verify_password_reset_token(token, settings=settings) is None
