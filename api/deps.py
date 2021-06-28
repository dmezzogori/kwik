from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.kwik import models, crud
from app.kwik.core import security
from app.kwik.core.config import settings
from app.kwik.db.session import get_db_from_request

reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

db = Depends(get_db_from_request)


def get_current_user(
    db: Session = db, token: str = Depends(reusable_oauth2)
) -> models.User:
    try:
        token_data = security.decode_token(token)
    except (jwt.JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = crud.user.get(db, id=token_data.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user

current_user = Depends(get_current_user)


def get_current_active_user(
    current_user: models.User = current_user,
) -> models.User:
    if not crud.user.is_active(current_user):
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

current_active_user = Depends(get_current_active_user)


def get_current_active_superuser(
    current_user: models.User = current_user,
) -> models.User:
    if not crud.user.is_superuser(current_user):
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user

current_active_superuser = Depends(get_current_active_superuser)


def has_permission(*permissions: str):

    def inner(db: Session = db, current_user: models.User = current_user):
        r = db.query(models.Permission).join(
            models.RolePermission,
            models.Role,
            models.UserRole).join(
            models.User, models.User.id == models.UserRole.user_id
        ).filter(
            models.Permission.name.in_(permissions),
            models.User.id == current_user.id
        ).one_or_none()
        if r is None:
            raise HTTPException(
                status_code=403, detail="The user doesn't have enough privileges"
            )

    return Depends(inner)
