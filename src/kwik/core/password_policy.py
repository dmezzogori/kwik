"""
Process-wide minimum length for new passwords.

Lives in ``kwik.core`` because ``kwik.schemas`` enforces it and ``kwik.security``
imports ``kwik.schemas``. ``Kwik`` configures it from ``PASSWORD_MIN_LENGTH`` when
the application is built; processes that never build a ``Kwik`` app (scripts,
background workers) keep the default, which equals the setting's default.
"""

from __future__ import annotations

from typing import Final

DEFAULT_PASSWORD_MIN_LENGTH: Final[int] = 12
"""Minimum number of characters of a new password unless configured otherwise.

Length only, no composition rules, following NIST SP 800-63B."""

_min_length = DEFAULT_PASSWORD_MIN_LENGTH


def configure_password_policy(*, min_length: int) -> None:
    """Set the minimum number of characters a new password must have."""
    global _min_length  # noqa: PLW0603
    _min_length = min_length


def password_min_length() -> int:
    """Return the minimum number of characters a new password must have."""
    return _min_length


__all__ = ["DEFAULT_PASSWORD_MIN_LENGTH", "configure_password_policy", "password_min_length"]
