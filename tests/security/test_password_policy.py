"""New passwords meet a configurable minimum length (teban #302)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from kwik.core import DEFAULT_PASSWORD_MIN_LENGTH
from kwik.schemas import AdminPasswordReset, UserPasswordChange, UserRegistration
from kwik.security import configure_password_policy, password_min_length
from kwik.settings import BaseKwikSettings

if TYPE_CHECKING:
    from collections.abc import Iterator

SHORT = "a" * (DEFAULT_PASSWORD_MIN_LENGTH - 1)
LONG_ENOUGH = "a" * DEFAULT_PASSWORD_MIN_LENGTH
TOO_MANY_BYTES = "é" * 40  # 40 characters, 80 UTF-8 bytes
STRICTER = 16
BYPASS = {"password_policy": False}
SEED_PASSWORD = "admin"


def _registration(password: str) -> dict[str, object]:
    """Registration payload carrying ``password``."""
    return {"name": "n", "surname": "s", "email": "policy@example.com", "password": password, "is_active": True}


@pytest.fixture(autouse=True)
def _restore_policy() -> Iterator[None]:
    """Leave the process-wide policy at its default for the next test."""
    yield
    configure_password_policy(min_length=DEFAULT_PASSWORD_MIN_LENGTH)


def test_default_minimum_is_twelve() -> None:
    """The setting and the process-wide policy both default to 12 characters."""
    assert BaseKwikSettings().PASSWORD_MIN_LENGTH == DEFAULT_PASSWORD_MIN_LENGTH
    assert password_min_length() == DEFAULT_PASSWORD_MIN_LENGTH


def test_short_password_rejected() -> None:
    """A new password one character short of the minimum is refused, naming the minimum."""
    with pytest.raises(ValidationError, match=f"at least {DEFAULT_PASSWORD_MIN_LENGTH} characters"):
        AdminPasswordReset(new_password=SHORT)


def test_every_new_password_schema_enforces_the_minimum() -> None:
    """Registration and password change apply the same policy."""
    with pytest.raises(ValidationError):
        UserRegistration.model_validate(_registration(SHORT))
    with pytest.raises(ValidationError):
        UserPasswordChange(old_password="x", new_password=SHORT)


def test_old_password_stays_unconstrained() -> None:
    """Verifying an existing short password is never refused by the policy."""
    assert UserPasswordChange(old_password="x", new_password=LONG_ENOUGH).old_password == "x"


def test_min_length_accepted() -> None:
    """A password of exactly the minimum length is accepted."""
    assert AdminPasswordReset(new_password=LONG_ENOUGH).new_password == LONG_ENOUGH


def test_min_length_counts_characters() -> None:
    """The minimum counts characters, not bytes: 12 two-byte characters pass."""
    multibyte = "é" * DEFAULT_PASSWORD_MIN_LENGTH
    assert AdminPasswordReset(new_password=multibyte).new_password == multibyte


def test_bypass_context_skips_minimum_only() -> None:
    """Seeds validating with the bypass context skip the minimum but keep the bcrypt bound."""
    assert UserRegistration.model_validate(_registration(SEED_PASSWORD), context=BYPASS).password == SEED_PASSWORD
    with pytest.raises(ValidationError, match="72 bytes"):
        UserRegistration.model_validate(_registration(TOO_MANY_BYTES), context=BYPASS)


def test_configured_minimum_honoured() -> None:
    """A stricter configured minimum applies to every new password."""
    configure_password_policy(min_length=STRICTER)
    assert password_min_length() == STRICTER
    with pytest.raises(ValidationError, match=f"at least {STRICTER} characters"):
        AdminPasswordReset(new_password=LONG_ENOUGH)


def test_setting_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    """The minimum must be between 1 and bcrypt's 72-byte limit."""
    monkeypatch.setenv("KWIK_PASSWORD_MIN_LENGTH", "0")
    with pytest.raises(ValidationError):
        BaseKwikSettings()
    monkeypatch.setenv("KWIK_PASSWORD_MIN_LENGTH", "73")
    with pytest.raises(ValidationError):
        BaseKwikSettings()
