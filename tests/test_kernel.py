"""Tests for the kwik Kernel registry and validation."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

import kwik.kernel
from kwik.kernel import Kernel, UserSchemas, get_kernel
from kwik.models import Base, Role, UserMixin
from kwik.models.default_user import DefaultUser
from kwik.schemas import UserProfile, UserProfileUpdate, UserRegistration


class _WrongTableUser(Base, UserMixin):
    """Valid composition but wrong table name — must be rejected."""

    __tablename__ = "kernel_test_users"


class _PlainProfile(BaseModel):
    """Profile schema WITHOUT from_attributes — must be rejected."""

    id: int


@pytest.fixture
def clean_slot(monkeypatch: pytest.MonkeyPatch) -> None:
    """Detach the process-wide kernel slot for the duration of one test."""
    monkeypatch.setattr(kwik.kernel, "_active_kernel", None)


class TestKernelValidation:
    """All validation failures raise BEFORE the slot is claimed — no fixture needed."""

    def test_rejects_non_model(self) -> None:
        """A non-SQLAlchemy class is rejected before the slot is claimed."""

        class _NotAModel:
            pass

        with pytest.raises(TypeError, match="SQLAlchemy model"):
            Kernel(user_model=_NotAModel)

    def test_rejects_model_without_user_mixin(self) -> None:
        """A model that does not subclass UserMixin is rejected."""
        with pytest.raises(TypeError, match="UserMixin"):
            Kernel(user_model=Role)

    def test_rejects_wrong_tablename(self) -> None:
        """A user model mapped to the wrong table name is rejected."""
        with pytest.raises(TypeError, match="__tablename__"):
            Kernel(user_model=_WrongTableUser)

    def test_rejects_non_schema_in_bundle(self) -> None:
        """A bundle carrying a non-BaseModel schema is rejected."""

        class _NotASchema:
            pass

        bundle = UserSchemas(profile=_NotASchema, registration=UserRegistration, update=UserProfileUpdate)
        with pytest.raises(TypeError, match="BaseModel subclass"):
            Kernel(user_model=DefaultUser, schemas=bundle)

    def test_rejects_profile_without_from_attributes(self) -> None:
        """A profile schema without from_attributes is rejected."""
        bundle = UserSchemas(profile=_PlainProfile, registration=UserRegistration, update=UserProfileUpdate)
        with pytest.raises(TypeError, match="from_attributes"):
            Kernel(user_model=DefaultUser, schemas=bundle)


class TestKernelSlot:
    """The kernel claims the process-wide slot and resolves via get_kernel()."""

    def test_claims_slot_and_get_kernel_returns_it(self, clean_slot: None) -> None:  # noqa: ARG002
        """A constructed kernel claims the slot and is returned by get_kernel()."""
        kernel = Kernel(user_model=DefaultUser)
        assert get_kernel() is kernel
        assert kernel.user_model is DefaultUser
        assert kernel.crud_users.model is DefaultUser

    def test_double_registration_raises(self, clean_slot: None) -> None:  # noqa: ARG002
        """Constructing a second kernel while one is active raises."""
        Kernel(user_model=DefaultUser)
        with pytest.raises(RuntimeError, match="already active"):
            Kernel(user_model=DefaultUser)

    def test_default_schemas_applied_when_not_provided(self, clean_slot: None) -> None:  # noqa: ARG002
        """Omitting schemas wires the stock user schema bundle."""
        kernel = Kernel(user_model=DefaultUser)
        expected = UserSchemas(profile=UserProfile, registration=UserRegistration, update=UserProfileUpdate)
        assert kernel.schemas == expected

    def test_reset_for_testing_clears_slot(self, clean_slot: None) -> None:  # noqa: ARG002
        """_reset_for_testing detaches the active kernel from the slot."""
        Kernel(user_model=DefaultUser)
        kwik.kernel._reset_for_testing()
        assert kwik.kernel._active_kernel is None

    def test_default_kernel_materializes_default_user(self, clean_slot: None) -> None:  # noqa: ARG002
        """get_kernel() with no active kernel materializes one wired to DefaultUser."""
        kernel = get_kernel()
        assert kernel.user_model is DefaultUser
        assert kwik.kernel._active_kernel is kernel
