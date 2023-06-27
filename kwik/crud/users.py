from __future__ import annotations

from typing import Any, NoReturn, Sequence

from fastapi import HTTPException
from kwik import models, schemas
from kwik.core.security import get_password_hash, verify_password
from kwik.exceptions import IncorrectCredentials, UserInactive, UserNotFound
from starlette import status

from . import auto_crud


class AutoCRUDUser(auto_crud.AutoCRUD[models.User, schemas.UserCreateSchema, schemas.UserUpdateSchema]):
    def get_by_email(self, *, email: str) -> models.User | None:
        return self.db.query(models.User).filter(models.User.email == email).first()

    def get_by_name(self, *, name: str) -> models.User | None:
        return self.db.query(models.User).filter(models.User.name == name).first()

    # noinspection PyMethodOverriding
    def create(self, *, obj_in: schemas.UserCreateSchema) -> models.User:
        db_obj = models.User(
            name=obj_in.name,
            surname=obj_in.surname,
            email=obj_in.email,
            is_active=obj_in.is_active,
            is_superuser=obj_in.is_superuser,
            hashed_password=get_password_hash(obj_in.password),
        )
        self.db.add(db_obj)
        self.db.flush()
        self.db.refresh(db_obj)
        return db_obj

    def create_if_not_exist(self, *, filters: dict, obj_in: schemas.UserCreateSchema, **kwargs) -> models.User:
        obj_db = self.db.query(models.User).filter_by(**filters).one_or_none()
        if obj_db is None:
            obj_db = self.create(obj_in=obj_in)
        return obj_db

    # noinspection PyMethodOverriding
    def update(self, *, db_obj: models.User, obj_in: schemas.UserUpdateSchema | dict[str, Any]) -> models.User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        if update_data.get("password"):
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        return super().update(db_obj=db_obj, obj_in=update_data)

    def change_password(self, *, user_id: int, obj_in: schemas.UserChangePasswordSchema) -> models.User:
        user_db = self.get(id=user_id)
        if not user_db:
            raise HTTPException(
                status_code=status.HTTP_412_PRECONDITION_FAILED,
                detail="The provided user does not exist",
            )
        if not self.authenticate(email=user_db.email, password=obj_in.old_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The provided password is wrong",
            )

        hashed_password = get_password_hash(obj_in.new_password)
        user_db.hashed_password = hashed_password
        return user_db

    def reset_password(self, *, email: str, password: str) -> models.User | NoReturn:
        user_db = self.get_by_email(email=email)
        if user_db is None:
            raise UserNotFound

        self.is_active(user_db)

        hashed_password = get_password_hash(password)
        user.hashed_password = hashed_password
        self.db.add(user)
        self.db.flush()
        return user

    def authenticate(self, *, email: str, password: str) -> models.User:
        """
        Authenticate a user with email and password

        Raises:
            IncorrectCredentials: If the user does not exist or the password is wrong
        """

        # Retrieve the user from the database
        user_db = self.get_by_email(email=email)

        # Check if the user exists and the password is correct
        if user_db is None or not verify_password(password, user_db.hashed_password):
            raise IncorrectCredentials

        return user_db

    @staticmethod
    def is_active(user: models.User) -> models.User | NoReturn:
        if not user.is_active:
            raise UserInactive
        return user

    def is_superuser(self, *, user_id: int) -> bool:
        user_db = self.get_if_exist(id=user_id)
        return user_db.is_superuser

    def has_permissions(self, *, user_id: int, permissions: Sequence[str]) -> bool:
        """
        Check if the user has all the permissions provided.
        """

        r = (
            self.db.query(models.Permission)
            .join(models.RolePermission, models.Role, models.UserRole)
            .join(models.User, models.User.id == models.UserRole.user_id)
            .filter(
                models.Permission.name.in_(permissions),
                models.User.id == user_id,
            )
            .distinct()
        )
        return r.count() == len(permissions)

    def has_roles(self, *, user_id: int, roles: Sequence[str]) -> bool:
        """
        Check if the user has all the roles provided.
        """

        r = (
            self.db.query(models.Role)
            .join(models.UserRole, models.Role.id == models.UserRole.role_id)
            .join(models.User, models.User.id == models.UserRole.user_id)
            .filter(
                models.Role.name.in_(roles),
                models.User.id == user_id,
            )
            .distinct()
        )

        return r.count() == len(roles)


user = AutoCRUDUser()
