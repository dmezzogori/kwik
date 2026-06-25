"""Test suite for kwik.utils.login."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import jwt
import pytest

from kwik.crud import crud_users
from kwik.exceptions.base import TokenValidationError
from kwik.schemas import UserRegistration
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
PASSWORD_HASH = get_password_hash("initial-password-123")


def test_generate_password_reset_token(settings: BaseKwikSettings) -> None:
    """Token embeds sub/exp/nbf and a pwd fingerprint of the current hash."""
    token = generate_password_reset_token(email=EMAIL, settings=settings, password_hash=PASSWORD_HASH)
    assert isinstance(token, str)
    decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded_token["sub"] == EMAIL
    assert "exp" in decoded_token
    assert "nbf" in decoded_token
    assert decoded_token["pwd"] == hashlib.sha256(PASSWORD_HASH.encode("utf-8")).hexdigest()[:16]


def _make_user(context, *, email: str, password: str, is_active: bool = True):
    """Create a user in the given context and return it."""
    return crud_users.create(
        obj_in=UserRegistration(
            name="reset",
            surname="user",
            email=email,
            password=password,
            is_active=is_active,
        ),
        context=context,
    )


def test_verify_password_reset_token_roundtrip(settings: BaseKwikSettings, no_user_context) -> None:
    """A freshly generated token verifies back to the user's email."""
    email = f"rt-{uuid.uuid4().hex}@example.com"
    user = _make_user(no_user_context, email=email, password="initial-pass-123")
    token = generate_password_reset_token(email=email, settings=settings, password_hash=user.hashed_password)
    assert verify_password_reset_token(token, settings=settings, context=no_user_context) == email


def test_verify_password_reset_token_rejected_after_change(settings: BaseKwikSettings, no_user_context) -> None:
    """Token stops verifying once the user's password (hash) changes."""
    email = f"chg-{uuid.uuid4().hex}@example.com"
    user = _make_user(no_user_context, email=email, password="initial-pass-123")
    token = generate_password_reset_token(email=email, settings=settings, password_hash=user.hashed_password)
    # Simulate a password change: new hash invalidates the embedded fingerprint.
    user.hashed_password = get_password_hash("brand-new-pass-456")
    no_user_context.session.flush()
    assert verify_password_reset_token(token, settings=settings, context=no_user_context) is None


def test_verify_password_reset_token_unknown_user(settings: BaseKwikSettings, no_user_context) -> None:
    """Token for an email with no matching user returns None."""
    token = generate_password_reset_token(
        email="ghost@example.com", settings=settings, password_hash=get_password_hash("x")
    )
    assert verify_password_reset_token(token, settings=settings, context=no_user_context) is None


def test_verify_password_reset_token_inactive_user(settings: BaseKwikSettings, no_user_context) -> None:
    """Token for an inactive user returns None even with a matching fingerprint."""
    email = f"inact-{uuid.uuid4().hex}@example.com"
    user = _make_user(no_user_context, email=email, password="initial-pass-123", is_active=False)
    token = generate_password_reset_token(email=email, settings=settings, password_hash=user.hashed_password)
    assert verify_password_reset_token(token, settings=settings, context=no_user_context) is None


def test_verify_password_reset_token_invalid_signature(settings: BaseKwikSettings, no_user_context) -> None:
    """A tampered token returns None (caller maps this to TokenValidationError)."""
    token = generate_password_reset_token(
        email="any@example.com", settings=settings, password_hash=get_password_hash("x")
    )
    assert verify_password_reset_token(token + "tamper", settings=settings, context=no_user_context) is None


def test_verify_password_reset_token_expired(settings: BaseKwikSettings, no_user_context) -> None:
    """An expired token returns None."""
    now = datetime.now(tz=UTC)
    token = jwt.encode(
        {"exp": (now - timedelta(hours=1)).timestamp(), "nbf": now - timedelta(hours=2), "sub": "any@example.com"},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    assert verify_password_reset_token(token, settings=settings, context=no_user_context) is None


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
