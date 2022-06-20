from datetime import datetime, timedelta
from typing import Any

import kwik
from jose import jwt
from kwik import schemas
from kwik.exceptions import Forbidden
from passlib.context import CryptContext
from pydantic import ValidationError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


ALGORITHM = "HS256"


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta = None,
    impersonator_user_id: int | None = None,
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=kwik.settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"exp": expire, "sub": str(subject), "kwik_impersonate": ""}
    if impersonator_user_id is not None:
        to_encode["kwik_impersonate"] = str(impersonator_user_id)

    encoded_jwt = jwt.encode(to_encode, kwik.settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_token(
    user_id: int,
    impersonator_user_id: int | None = None,
) -> dict:
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
    try:
        payload = jwt.decode(token, kwik.settings.SECRET_KEY, algorithms=[ALGORITHM])
        token_data = schemas.TokenPayload(**payload)
        return token_data
    except (jwt.JWTError, ValidationError):
        raise Forbidden()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
