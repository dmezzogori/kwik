"""Test suite for kwik.utils.login."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import jwt
import pytest
from fastapi import status
from pydantic import ValidationError

from kwik.core import BCRYPT_MAX_PASSWORD_BYTES
from kwik.crud import crud_users
from kwik.exceptions.base import TokenValidationError
from kwik.exceptions.users import PasswordTooLongError
from kwik.schemas import UserPasswordChange, UserRegistration
from kwik.security import (
    ALGORITHM,
    create_refresh_token,
    create_token,
    decode_token,
    generate_password_reset_token,
    get_password_hash,
    verify_password,
    verify_password_reset_token,
)
from kwik.settings import BaseKwikSettings

if TYPE_CHECKING:
    from kwik.crud import NoUserCtx
    from kwik.models import User

EMAIL = "test@example.com"
PASSWORD_HASH = get_password_hash("initial-password-123")
USER_ID = 123
SESSION_ID = "sess-1"
TOKEN_ID = "jti-1"
EXPIRES_AT = datetime(2099, 1, 1, tzinfo=UTC)  # far future: PyJWT's wall-clock exp check never interferes
SECONDS_PER_MINUTE = 60
THIRTY_DAYS_IN_MINUTES = 43_200
GRACE_SECONDS = 30


def test_generate_password_reset_token(settings: BaseKwikSettings) -> None:
    """Token embeds sub/exp/nbf and a pwd fingerprint of the current hash."""
    token = generate_password_reset_token(email=EMAIL, settings=settings, password_hash=PASSWORD_HASH)
    assert isinstance(token, str)
    decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert decoded_token["sub"] == EMAIL
    assert "exp" in decoded_token
    assert "nbf" in decoded_token
    assert decoded_token["pwd"] == hashlib.sha256(PASSWORD_HASH.encode("utf-8")).hexdigest()[:16]


def _make_user(context: NoUserCtx, *, email: str, password: str, is_active: bool = True) -> User:
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


def test_verify_password_reset_token_roundtrip(settings: BaseKwikSettings, no_user_context: NoUserCtx) -> None:
    """A freshly generated token verifies back to the user's email."""
    email = f"rt-{uuid.uuid4().hex}@example.com"
    user = _make_user(no_user_context, email=email, password="initial-pass-123")
    token = generate_password_reset_token(email=email, settings=settings, password_hash=user.hashed_password)
    assert verify_password_reset_token(token, settings=settings, context=no_user_context) == email


def test_verify_password_reset_token_rejected_after_change(
    settings: BaseKwikSettings, no_user_context: NoUserCtx
) -> None:
    """Token stops verifying once the user's password (hash) changes."""
    email = f"chg-{uuid.uuid4().hex}@example.com"
    user = _make_user(no_user_context, email=email, password="initial-pass-123")
    token = generate_password_reset_token(email=email, settings=settings, password_hash=user.hashed_password)
    # Simulate a password change: new hash invalidates the embedded fingerprint.
    user.hashed_password = get_password_hash("brand-new-pass-456")
    no_user_context.session.flush()
    assert verify_password_reset_token(token, settings=settings, context=no_user_context) is None


def test_verify_password_reset_token_unknown_user(settings: BaseKwikSettings, no_user_context: NoUserCtx) -> None:
    """Token for an email with no matching user returns None."""
    token = generate_password_reset_token(
        email="ghost@example.com", settings=settings, password_hash=get_password_hash("x")
    )
    assert verify_password_reset_token(token, settings=settings, context=no_user_context) is None


def test_verify_password_reset_token_inactive_user(settings: BaseKwikSettings, no_user_context: NoUserCtx) -> None:
    """Token for an inactive user returns None even with a matching fingerprint."""
    email = f"inact-{uuid.uuid4().hex}@example.com"
    user = _make_user(no_user_context, email=email, password="initial-pass-123", is_active=False)
    token = generate_password_reset_token(email=email, settings=settings, password_hash=user.hashed_password)
    assert verify_password_reset_token(token, settings=settings, context=no_user_context) is None


def test_verify_password_reset_token_invalid_signature(settings: BaseKwikSettings, no_user_context: NoUserCtx) -> None:
    """A tampered token returns None (caller maps this to TokenValidationError)."""
    token = generate_password_reset_token(
        email="any@example.com", settings=settings, password_hash=get_password_hash("x")
    )
    assert verify_password_reset_token(token + "tamper", settings=settings, context=no_user_context) is None


def test_verify_password_reset_token_expired(settings: BaseKwikSettings, no_user_context: NoUserCtx) -> None:
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


def test_create_token_without_session_has_no_session_claims(settings: BaseKwikSettings) -> None:
    """A token minted without a session carries the 1.13 claim set and no refresh data."""
    token = create_token(user_id=USER_ID, settings=settings)
    claims = jwt.decode(token.access_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    assert "sid" not in claims
    assert "typ" not in claims
    assert token.refresh_token is None
    assert token.expires_in is None


def test_create_token_with_session_carries_sid_and_type(settings: BaseKwikSettings) -> None:
    """A token minted for a session carries sid and typ and reports its lifetime in seconds."""
    token = create_token(user_id=USER_ID, session_id=SESSION_ID, settings=settings)
    payload = decode_token(token=token.access_token, settings=settings)
    assert payload.sid == SESSION_ID
    assert payload.typ == "access"
    assert token.expires_in == settings.ACCESS_TOKEN_EXPIRE_MINUTES * SECONDS_PER_MINUTE


def test_refresh_token_roundtrip(settings: BaseKwikSettings) -> None:
    """A refresh token decodes, as a refresh token, to the claims it was created with."""
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    raw = create_refresh_token(
        user_id=USER_ID,
        session_id=SESSION_ID,
        token_id=TOKEN_ID,
        expires_at=expires_at,
        settings=settings,
    )
    payload = decode_token(token=raw, settings=settings, token_type="refresh")
    assert (payload.sub, payload.sid, payload.jti, payload.typ) == (USER_ID, SESSION_ID, TOKEN_ID, "refresh")


def test_refresh_token_encoding_is_deterministic(settings: BaseKwikSettings) -> None:
    """Encoding the same arguments twice yields the same string."""

    def encode() -> str:
        return create_refresh_token(
            user_id=USER_ID,
            session_id=SESSION_ID,
            token_id=TOKEN_ID,
            expires_at=EXPIRES_AT,
            settings=settings,
        )

    assert encode() == encode()


def test_decode_token_rejects_other_type(settings: BaseKwikSettings) -> None:
    """An access token is not accepted as a refresh token, nor the reverse."""
    access = create_token(user_id=USER_ID, session_id=SESSION_ID, settings=settings).access_token
    refresh = create_refresh_token(
        user_id=USER_ID,
        session_id=SESSION_ID,
        token_id=TOKEN_ID,
        expires_at=EXPIRES_AT,
        settings=settings,
    )
    with pytest.raises(TokenValidationError):
        decode_token(token=access, settings=settings, token_type="refresh")
    with pytest.raises(TokenValidationError):
        decode_token(token=refresh, settings=settings)


def test_decode_token_accepts_1_13_payload(settings: BaseKwikSettings) -> None:
    """A token minted by kwik 1.13 (no typ, no sid) still validates as an access token."""
    legacy = jwt.encode(
        {"exp": EXPIRES_AT, "sub": str(USER_ID), "kwik_impersonate": ""},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )
    payload = decode_token(token=legacy, settings=settings)
    assert (payload.sid, payload.typ, payload.jti) == (None, "access", None)


def test_settings_refresh_defaults() -> None:
    """The refresh lifetime defaults to 30 days and the reuse grace to 30 seconds."""
    assert BaseKwikSettings().REFRESH_TOKEN_EXPIRE_MINUTES == THIRTY_DAYS_IN_MINUTES
    assert BaseKwikSettings().REFRESH_REUSE_GRACE_SECONDS == GRACE_SECONDS


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


def test_get_password_hash_accepts_exactly_the_bcrypt_limit() -> None:
    """A password of exactly BCRYPT_MAX_PASSWORD_BYTES bytes must still hash."""
    password = "a" * BCRYPT_MAX_PASSWORD_BYTES

    assert verify_password(password, get_password_hash(password)) is True


def test_get_password_hash_rejects_over_long_password() -> None:
    """Bcrypt >=5.0.0 rejects >72 bytes; kwik surfaces that as a typed 422 error."""
    password = "a" * (BCRYPT_MAX_PASSWORD_BYTES + 1)

    with pytest.raises(PasswordTooLongError) as exc_info:
        get_password_hash(password)

    assert exc_info.value.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert str(BCRYPT_MAX_PASSWORD_BYTES) in exc_info.value.detail


def test_get_password_hash_counts_bytes_not_characters() -> None:
    """A 72-character multi-byte password exceeds 72 bytes and must be rejected."""
    # Each "e" with a combining acute is 2 bytes in UTF-8, so 72 chars == 144 bytes.
    password = "é" * BCRYPT_MAX_PASSWORD_BYTES

    assert len(password) == BCRYPT_MAX_PASSWORD_BYTES
    assert len(password.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES

    with pytest.raises(PasswordTooLongError):
        get_password_hash(password)


def test_verify_password_rejects_over_long_password_without_raising() -> None:
    """
    An over-long password fails verification rather than propagating ValueError.

    Accounts created under bcrypt <5.0.0 could hold a silently-truncated secret;
    verification must degrade to a failed login, not a 500.
    """
    hashed_password = get_password_hash("a" * BCRYPT_MAX_PASSWORD_BYTES)
    over_long = "a" * (BCRYPT_MAX_PASSWORD_BYTES + 1)

    assert verify_password(over_long, hashed_password) is False


@pytest.mark.parametrize(
    "password",
    [
        "a" * (BCRYPT_MAX_PASSWORD_BYTES + 1),
        "é" * BCRYPT_MAX_PASSWORD_BYTES,
    ],
    ids=["over-long-ascii", "over-long-utf8"],
)
def test_user_registration_schema_rejects_over_long_password(password: str) -> None:
    """The schema rejects over-long passwords so the API answers 422, not 500."""
    with pytest.raises(ValidationError):
        UserRegistration(
            name="Test",
            surname="User",
            email="over.long@example.com",
            password=password,
        )


def test_password_change_schema_leaves_old_password_unconstrained() -> None:
    """
    Only the password being *set* is capped; the one being verified is not.

    A legacy account may hold a secret longer than bcrypt's limit, and rejecting it
    at validation time would turn a failed login into a confusing 422.
    """
    over_long = "a" * (BCRYPT_MAX_PASSWORD_BYTES + 1)

    schema = UserPasswordChange(old_password=over_long, new_password="fits-fine-123")

    assert schema.old_password == over_long

    with pytest.raises(ValidationError):
        UserPasswordChange(old_password=over_long, new_password=over_long)
