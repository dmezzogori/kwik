"""Login and authentication utility functions."""

from __future__ import annotations

from datetime import datetime, timedelta

from jose import jwt

from kwik.core.settings import get_settings


def generate_password_reset_token(email: str) -> str:
    """Generate JWT token for password reset with expiration."""
    delta = timedelta(hours=48)  # Default 48 hours for password reset token
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    return jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        get_settings().SECRET_KEY,
        algorithm="HS256",
    )


def verify_password_reset_token(token: str) -> str | None:
    """Verify password reset token and return email if valid."""
    decoded_token = jwt.decode(token, get_settings().SECRET_KEY, algorithms=["HS256"])
    return decoded_token.get("sub", None)
