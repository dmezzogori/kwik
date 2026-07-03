"""Tests for explicit model passing and audit-context validation in AutoCRUD."""

from __future__ import annotations

import pytest
from pydantic import BaseModel
from sqlalchemy.orm import Mapped, mapped_column

from kwik.crud import AutoCRUD, Context, MaybeUserCtx, NoUserCtx, UserCtx
from kwik.models import Base, RecordInfoMixin, UserMixin


class _Widget(Base):
    __tablename__ = "autocrud_explicit_widgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(nullable=False)


class _AuditedWidget(Base, RecordInfoMixin):
    __tablename__ = "autocrud_explicit_audited_widgets"

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(nullable=False)


class _WidgetPayload(BaseModel):
    label: str


class _AppUser(UserMixin):
    """Structural stand-in for an app-defined user model (deliberately not mapped)."""


type _AppCtx = Context[_AppUser]


class _GenericWidgetCRUD[ModelT: Base](AutoCRUD[NoUserCtx, ModelT, _WidgetPayload, _WidgetPayload, int]):
    """Generic-over-model CRUD, mirroring the kernel-owned users CRUD shape."""


class TestExplicitModel:
    """Explicit ``model=`` bypasses generic-argument model inference."""

    def test_explicit_model_bypasses_generic_inference(self) -> None:
        """An explicit ``model=`` is used verbatim even when the base is model-generic."""
        crud = _GenericWidgetCRUD(model=_Widget)
        assert crud.model is _Widget

    def test_generic_type_parameter_without_explicit_model_raises(self) -> None:
        """A model-generic CRUD without an explicit ``model=`` raises a clear TypeError."""
        with pytest.raises(TypeError, match="pass the concrete model explicitly"):
            _GenericWidgetCRUD()


class TestAuditContextValidation:
    """Audit fields require a Context whose user type excludes ``None``."""

    def test_user_ctx_alias_is_accepted(self) -> None:
        """The ``UserCtx`` alias satisfies the non-optional-user requirement."""

        class _AuditedCRUD(AutoCRUD[UserCtx, _AuditedWidget, _WidgetPayload, _WidgetPayload, int]):
            pass

        assert _AuditedCRUD().model is _AuditedWidget

    def test_app_defined_context_alias_is_accepted(self) -> None:
        """An app-defined ``Context[AppUser]`` alias also satisfies the requirement."""

        class _AppAuditedCRUD(AutoCRUD[_AppCtx, _AuditedWidget, _WidgetPayload, _WidgetPayload, int]):
            pass

        assert _AppAuditedCRUD().model is _AuditedWidget

    def test_optional_user_context_is_rejected(self) -> None:
        """A Context permitting ``UserMixin | None`` is rejected for audited models."""

        class _MaybeAuditedCRUD(AutoCRUD[MaybeUserCtx, _AuditedWidget, _WidgetPayload, _WidgetPayload, int]):
            pass

        with pytest.raises(ValueError, match="non-optional user"):
            _MaybeAuditedCRUD()

    def test_no_user_context_is_rejected(self) -> None:
        """A Context whose user is ``None`` is rejected for audited models."""

        class _NoUserAuditedCRUD(AutoCRUD[NoUserCtx, _AuditedWidget, _WidgetPayload, _WidgetPayload, int]):
            pass

        with pytest.raises(ValueError, match="non-optional user"):
            _NoUserAuditedCRUD()
