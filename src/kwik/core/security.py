"""Security utilities for JWT tokens and password hashing."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from jose import jwt
from passlib.context import CryptContext
from pydantic import ValidationError

import kwik
import kwik.typings
from kwik import schemas
from kwik.exceptions.base import InvalidToken

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


ALGORITHM = "HS256"


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    impersonator_user_id: int | None = None,
) -> str:
    """Create JWT access token with optional expiration and impersonation support."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=kwik.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject), "kwik_impersonate": ""}
    if impersonator_user_id is not None:
        to_encode["kwik_impersonate"] = str(impersonator_user_id)

    return jwt.encode(to_encode, kwik.settings.SECRET_KEY, algorithm=ALGORITHM)


def create_token(user_id: int, impersonator_user_id: int | None = None) -> kwik.typings.Token:
    """Create OAuth2 bearer token response for user authentication."""
    access_token_expires = timedelta(minutes=kwik.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            user_id,
            expires_delta=access_token_expires,
            impersonator_user_id=impersonator_user_id,
        ),
        "token_type": "bearer",
    }


def decode_token(token: str) -> schemas.TokenPayload:
    """Decode and validate JWT token, returning payload data."""
    try:
        payload = jwt.decode(token, kwik.settings.SECRET_KEY, algorithms=[ALGORITHM])
        return schemas.TokenPayload(**payload)
    except (jwt.JWTError, ValidationError):
        raise InvalidToken


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against bcrypt hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash for password."""
    return pwd_context.hash(password)
