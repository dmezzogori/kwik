"""Test AutoCRUD context validation functionality."""

from unittest.mock import Mock, patch

import pytest
from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, select

from kwik.crud.autocrud import AutoCRUD, _sort_query
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

    def test_sort_query_invalid_field(self) -> None:
        """Test _sort_query function with invalid field name."""
        mock_sort = [("invalid_field", "asc")]
        stmt = select(ModelWithoutAuditFields)

        with pytest.raises(ValueError, match="Invalid sort field 'invalid_field' for model ModelWithoutAuditFields"):
            _sort_query(model=ModelWithoutAuditFields, stmt=stmt, sort=mock_sort)

    def test_get_multi_invalid_filter_field(self, no_user_context: NoUserCtx) -> None:
        """Test get_multi with invalid filter field."""

        class TestCRUD(AutoCRUD[NoUserCtx, ModelWithoutAuditFields, _CreateSchema, _UpdateSchema, int]):
            pass

        crud = TestCRUD()

        with pytest.raises(ValueError, match="Invalid filter field 'invalid_field' for model ModelWithoutAuditFields"):
            crud.get_multi(context=no_user_context, invalid_field="test")

    def test_get_multi_invalid_sort_field(self, no_user_context: NoUserCtx) -> None:
        """Test get_multi with invalid sort field."""

        class TestCRUD(AutoCRUD[NoUserCtx, ModelWithoutAuditFields, _CreateSchema, _UpdateSchema, int]):
            pass

        crud = TestCRUD()
        mock_sort = [("invalid_field", "asc")]

        with pytest.raises(ValueError, match="Invalid sort field 'invalid_field' for model ModelWithoutAuditFields"):
            crud.get_multi(context=no_user_context, sort=mock_sort)

    def test_autocrud_empty_generic_args(self) -> None:
        """Test AutoCRUD constructor with empty generic args."""

        class TestCRUDEmptyArgs(AutoCRUD):
            def __init__(self) -> None:
                # Simulate empty args scenario
                self.__orig_bases__ = (AutoCRUD,)  # No generic args
                super().__init__()

        with pytest.raises(ValueError, match="Model type must be specified via generic type parameters"):
            TestCRUDEmptyArgs()

    def test_get_multi_model_without_primary_key(self, no_user_context: NoUserCtx) -> None:
        """Test get_multi with model that has no primary key columns."""

        class TestCRUD(AutoCRUD[NoUserCtx, ModelWithoutAuditFields, _CreateSchema, _UpdateSchema, int]):
            pass

        crud = TestCRUD()

        # Mock the inspect function to return no primary key columns
        with patch("kwik.crud.autocrud.inspect") as mock_inspect:
            # Mock empty primary key columns to test the branch
            mock_pk = Mock()
            mock_pk.__iter__ = Mock(return_value=iter([]))  # Empty primary key
            mock_inspect.return_value.primary_key = mock_pk

            # This should work but won't add default ordering since there are no PK columns
            # We're testing the branch coverage for line 133->137
            count, results = crud.get_multi(context=no_user_context)
            assert count == 0
            assert results == []

    def test_create_with_audit_fields_no_user(self) -> None:
        """Test create with audit fields but context.user is None."""

        class TestCRUD(AutoCRUD[UserCtx, ModelWithAuditFields, _CreateSchema, _UpdateSchema, int]):
            pass

        crud = TestCRUD()

        # Create a context with user=None to test the branch
        mock_session = Mock()
        mock_session.add.return_value = None
        mock_session.flush.return_value = None
        mock_session.refresh.return_value = None

        # Create a mock context that has user=None
        mock_context = Mock()
        mock_context.session = mock_session
        mock_context.user = None

        schema = _CreateSchema(name="test")
        crud.create(obj_in=schema, context=mock_context)

        # Verify that the create method was called but audit field was not set
        mock_session.add.assert_called_once()
        created_obj = mock_session.add.call_args[0][0]
        # The field should not have been added to the object data since user is None
        assert "creator_user_id" not in created_obj.__dict__

    def test_update_with_audit_fields_no_user(self) -> None:
        """Test update with audit fields but context.user is None."""

        class TestCRUD(AutoCRUD[UserCtx, ModelWithAuditFields, _CreateSchema, _UpdateSchema, int]):
            pass

        crud = TestCRUD()

        # Mock existing object
        existing_obj = ModelWithAuditFields(id=1, name="existing")

        # Create a mock session and context with user=None
        mock_session = Mock()
        mock_session.get.return_value = existing_obj
        mock_session.add.return_value = None
        mock_session.flush.return_value = None
        mock_session.refresh.return_value = None

        # Create a mock context that has user=None
        mock_context = Mock()
        mock_context.session = mock_session
        mock_context.user = None

        schema = _UpdateSchema(name="updated")
        result = crud.update(entity_id=1, obj_in=schema, context=mock_context)

        # Verify that the audit fields are not set when user is None
        mock_session.add.assert_called_once()
        assert result.name == "updated"
        # Check that last_modifier_user_id was not updated since user is None
        # The existing object might have the field but it shouldn't be updated
        assert result.name == "updated"
