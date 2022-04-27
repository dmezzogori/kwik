from typing import Any, Dict, Optional, Union

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from kwik import models, schemas
from kwik.core.security import get_password_hash, verify_password
from . import auto_crud


class AutoCRUDUser(auto_crud.AutoCRUD):
    def get_by_email(self, *, db: Session, email: str) -> Optional[models.User]:
        return db.query(models.User).filter(models.User.email == email).first()

    def get_by_name(self, *, db: Session, name: str) -> Optional[models.User]:
        return db.query(models.User).filter(models.User.name == name).first()

    def create(self, *, db: Session, obj_in: schemas.UserCreate) -> models.User:
        db_obj = models.User(
            name=obj_in.name,
            surname=obj_in.surname,
            email=obj_in.email,
            is_active=obj_in.is_active,
            hashed_password=get_password_hash(obj_in.password),
        )
        db.add(db_obj)
        db.flush()
        db.refresh(db_obj)
        return db_obj

    def create_if_not_exist(self, *, db: Session, filters: dict, obj_in: schemas.UserCreate, **kwargs) -> models.User:
        obj_db = db.query(models.User).filter_by(**filters).one_or_none()
        if obj_db is None:
            obj_db = self.create(db=db, obj_in=obj_in)
        return obj_db

    def update(
        self, *, db: Session, db_obj: models.User, obj_in: Union[schemas.UserUpdate, Dict[str, Any]]
    ) -> models.User:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
        if update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            del update_data["password"]
            update_data["hashed_password"] = hashed_password
        return super().update(db=db, db_obj=db_obj, obj_in=update_data)

    def change_password(
        self, *, db: Session, user_id: int, obj_in: schemas.UserChangePassword
    ) -> Optional[models.User]:
        user = self.get(db=db, id=user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_412_PRECONDITION_FAILED, detail="The provided user does not exist",
            )
        if not self.authenticate(db=db, email=user.email, password=obj_in.old_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="The provided password is wrong",
            )
        else:
            hashed_password = get_password_hash(obj_in.new_password)
            user.hashed_password = hashed_password
            db.flush()
            return user

    def authenticate(self, *, db: Session, email: str, password: str) -> Optional[models.User]:
        user = self.get_by_email(db=db, email=email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def is_active(self, user: models.User):
        if not user.is_active:
            raise UserInactive
        return user

    def is_superuser(self, user: models.User) -> bool:
        return True  # TODO: fix user.is_superuser


user = AutoCRUDUser(models.User)
