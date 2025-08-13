"""Test AutoCRUD context validation functionality."""

import pytest
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String

from kwik.crud.autocrud import AutoCRUD
from kwik.crud.context import NoUserCtx, UserCtx
from kwik.models import Base


class ModelWithAuditFields(Base):
    """Test model with audit trail fields."""

    __tablename__ = "model_with_audit"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    creator_user_id = Column(Integer)  # Audit field
    last_modifier_user_id = Column(Integer)  # Audit field


class ModelWithoutAuditFields(Base):
    """Test model without audit trail fields."""

    __tablename__ = "model_without_audit"

    id = Column(Integer, primary_key=True)
    name = Column(String(50))


class _CreateSchema(BaseModel):
    """Test create schema."""

    name: str


class _UpdateSchema(BaseModel):
    """Test update schema."""

    name: str | None = None


class TestAutoCRUDValidation:
    """Test AutoCRUD context validation."""

    def test_autocrud_with_audit_fields_and_userctx_succeeds(self) -> None:
        """Test that models with audit fields work with UserCtx."""

        class ValidCRUD(AutoCRUD[UserCtx, ModelWithAuditFields, _CreateSchema, _UpdateSchema, int]):
            pass

        # Should not raise any exception
        crud = ValidCRUD()
        assert crud.record_creator_user_id is True
        assert crud.record_modifier_user_id is True

    def test_autocrud_with_audit_fields_and_nouserctx_fails(self) -> None:
        """Test that models with audit fields fail with NoUserCtx."""
        with pytest.raises(  # noqa: PT012
            ValueError,
            match=r"Model ModelWithAuditFields has audit trail fields.*but Context parameter is NoUserCtx",
        ):

            class InvalidCRUD(AutoCRUD[NoUserCtx, ModelWithAuditFields, _CreateSchema, _UpdateSchema, int]):
                pass

            InvalidCRUD()

    def test_autocrud_without_audit_fields_and_nouserctx_succeeds(self) -> None:
        """Test that models without audit fields work with NoUserCtx."""

        class ValidCRUD(AutoCRUD[NoUserCtx, ModelWithoutAuditFields, _CreateSchema, _UpdateSchema, int]):
            pass

        # Should not raise any exception
        crud = ValidCRUD()
        assert crud.record_creator_user_id is False
        assert crud.record_modifier_user_id is False

    def test_autocrud_without_audit_fields_and_userctx_succeeds(self) -> None:
        """Test that models without audit fields also work with UserCtx."""

        class ValidCRUD(AutoCRUD[UserCtx, ModelWithoutAuditFields, _CreateSchema, _UpdateSchema, int]):
            pass

        # Should not raise any exception
        crud = ValidCRUD()
        assert crud.record_creator_user_id is False
        assert crud.record_modifier_user_id is False

    def test_autocrud_with_only_creator_field_requires_userctx(self) -> None:
        """Test that having only creator_user_id field requires UserCtx."""

        class ModelWithOnlyCreator(Base):
            __tablename__ = "model_with_only_creator"

            id = Column(Integer, primary_key=True)
            name = Column(String(50))
            creator_user_id = Column(Integer)  # Only creator field

        with pytest.raises(  # noqa: PT012
            ValueError,
            match=r"Model ModelWithOnlyCreator has audit trail fields.*but Context parameter is NoUserCtx",
        ):

            class InvalidCRUD(AutoCRUD[NoUserCtx, ModelWithOnlyCreator, _CreateSchema, _UpdateSchema, int]):
                pass

            InvalidCRUD()

    def test_autocrud_with_only_modifier_field_requires_userctx(self) -> None:
        """Test that having only last_modifier_user_id field requires UserCtx."""

        class ModelWithOnlyModifier(Base):
            __tablename__ = "model_with_only_modifier"

            id = Column(Integer, primary_key=True)
            name = Column(String(50))
            last_modifier_user_id = Column(Integer)  # Only modifier field

        with pytest.raises(  # noqa: PT012
            ValueError,
            match=r"Model ModelWithOnlyModifier has audit trail fields.*but Context parameter is NoUserCtx",
        ):

            class InvalidCRUD(AutoCRUD[NoUserCtx, ModelWithOnlyModifier, _CreateSchema, _UpdateSchema, int]):
                pass

            InvalidCRUD()
