from typing import Any

from fastapi import HTTPException
from kwik import models, schemas
from kwik.core.security import get_password_hash, verify_password
from kwik.database.session import KwikSession
from kwik.exceptions import UserInactive
from starlette import status

from . import auto_crud


class AutoCRUDUser(auto_crud.AutoCRUD):
    @staticmethod
    def get_by_email(*, db: KwikSession, email: str) -> models.User | None:
        return db.query(models.User).filter(models.User.email == email).first()

    @staticmethod
    def get_by_name(*, db: KwikSession, name: str) -> models.User | None:
        return db.query(models.User).filter(models.User.name == name).first()

    # noinspection PyMethodOverriding
    @staticmethod
    def create(*, db: KwikSession, obj_in: schemas.UserCreate) -> models.User:
        db_obj = models.User(
            name=obj_in.name,
            surname=obj_in.surname,
            email=obj_in.email,
            is_active=obj_in.is_active,
            is_superuser=obj_in.is_superuser,
            hashed_password=get_password_hash(obj_in.password),
        )
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def create_if_not_exist(
        self, *, db: KwikSession, filters: dict, obj_in: schemas.UserCreate, **kwargs
    ) -> models.User:
        obj_db = db.query(models.User).filter_by(**filters).one_or_none()
        if obj_db is None:
            obj_db = self.create(db=db, obj_in=obj_in)
        return obj_db

    # noinspection PyMethodOverriding
    def update(
        self, *, db: KwikSession, db_obj: models.User, obj_in: schemas.UserUpdate | dict[str, Any]
    ) -> models.User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        return super().update(db=db, db_obj=db_obj, obj_in=update_data)

    def change_password(self, *, db: KwikSession, user_id: int, obj_in: schemas.UserChangePassword) -> models.User:
        user_db = self.get(db=db, id=user_id)
        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_412_PRECONDITION_FAILED,
                detail="The provided user does not exist",
            )
        if not self.authenticate(db=db, email=user_db.email, password=obj_in.old_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The provided password is wrong",
            )
        else:
            hashed_password = get_password_hash(obj_in.new_password)
            user_db.hashed_password = hashed_password
            db.flush()
            return user_db

    def authenticate(self, *, db: KwikSession, email: str, password: str) -> models.User | None:
        user_db = self.get_by_email(db=db, email=email)
        if not user_db:
            return None
        if not verify_password(password, user_db.hashed_password):
            return None
        return user_db

    @staticmethod
    def is_active(user: models.User) -> models.User:
        if not user.is_active:
            raise UserInactive
        return user

    def is_superuser(self, *, db: KwikSession, user_id: int) -> bool:
        user_db = self.get_if_exist(db=db, id=user_id)
        return user_db.is_superuser


user = AutoCRUDUser(models.User)
