from datetime import datetime, timedelta

import kwik
from jose import jwt


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=kwik.settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.utcnow()
    expires = now + delta
    exp = expires.timestamp()
    encoded_jwt = jwt.encode({"exp": exp, "nbf": now, "sub": email}, kwik.settings.SECRET_KEY, algorithm="HS256",)
    return encoded_jwt


def verify_password_reset_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(token, kwik.settings.SECRET_KEY, algorithms=["HS256"])
        return decoded_token["sub"]
    except jwt.JWTError:
        return None
