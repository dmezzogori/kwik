"""Test suite for kwik.utils.login."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import jwt
import pytest

from kwik.exceptions.base import TokenValidationError
from kwik.security import (
    ALGORITHM,
    create_token,
    decode_token,
    generate_password_reset_token,
    get_password_hash,
    verify_password,
    verify_password_reset_token,
)

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


def test_decode_token_valid(settings: BaseKwikSettings) -> None:
    """Test that a valid JWT token is decoded correctly."""
    user_id = 123
    token_data = create_token(user_id=user_id, settings=settings)
    decoded_payload = decode_token(token=token_data.access_token, settings=settings)

    assert decoded_payload.sub == user_id
    assert decoded_payload.kwik_impersonate == ""


def test_decode_token_with_impersonation(settings: BaseKwikSettings) -> None:
    """Test that a JWT token with impersonation is decoded correctly."""
    user_id = 123
    impersonator_id = 456
    token_data = create_token(user_id=user_id, impersonator_user_id=impersonator_id, settings=settings)
    decoded_payload = decode_token(token=token_data.access_token, settings=settings)

    assert decoded_payload.sub == user_id
    assert decoded_payload.kwik_impersonate == str(impersonator_id)


def test_decode_token_invalid_signature(settings: BaseKwikSettings) -> None:
    """Test that an invalid token signature raises TokenValidationError."""
    user_id = 123
    token_data = create_token(user_id=user_id, settings=settings)
    tampered_token = token_data.access_token + "invalid"

    with pytest.raises(TokenValidationError):
        decode_token(token=tampered_token, settings=settings)


def test_decode_token_expired(settings: BaseKwikSettings) -> None:
    """Test that an expired token raises TokenValidationError."""
    now = datetime.now(UTC)
    expired_exp = now - timedelta(hours=1)
    expired_token = jwt.encode(
        {
            "exp": expired_exp,
            "sub": "123",
            "kwik_impersonate": "",
        },
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

    with pytest.raises(TokenValidationError):
        decode_token(token=expired_token, settings=settings)


def test_decode_token_invalid_payload(settings: BaseKwikSettings) -> None:
    """Test that a token with invalid payload raises TokenValidationError."""
    invalid_token = jwt.encode(
        {"invalid_field": "value"},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

    with pytest.raises(TokenValidationError):
        decode_token(token=invalid_token, settings=settings)


def test_verify_password_matching() -> None:
    """Test that verify_password returns True for matching passwords."""
    plain_password = "test_password_123"
    hashed_password = get_password_hash(plain_password)

    assert verify_password(plain_password, hashed_password) is True


def test_verify_password_non_matching() -> None:
    """Test that verify_password returns False for non-matching passwords."""
    plain_password = "test_password_123"
    wrong_password = "wrong_password_456"
    hashed_password = get_password_hash(plain_password)

    assert verify_password(wrong_password, hashed_password) is False


def test_verify_password_invalid_hash() -> None:
    """Test that verify_password returns False for invalid hash format."""
    plain_password = "test_password_123"
    invalid_hash = "not_a_valid_bcrypt_hash"

    assert verify_password(plain_password, invalid_hash) is False


def test_verify_password_empty_password() -> None:
    """Test that verify_password handles empty passwords gracefully."""
    empty_password = ""
    hashed_password = get_password_hash("some_password")

    assert verify_password(empty_password, hashed_password) is False


def test_verify_password_empty_hash() -> None:
    """Test that verify_password handles empty hash gracefully."""
    plain_password = "test_password_123"
    empty_hash = ""

    assert verify_password(plain_password, empty_hash) is False
