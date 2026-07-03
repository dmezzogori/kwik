"""CRUD, scenario, and seeding behavior against a custom user model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.kernel import get_kernel
from kwik.seeding import create_first_superuser

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

    from kwik.crud import NoUserCtx
    from kwik.models import UserMixin
    from kwik.settings import BaseKwikSettings


class TestCustomUserCrud:
    """CRUD, factory, and seeding coverage for a custom user model with an extra column."""

    def test_create_persists_custom_column_on_single_table(self, no_user_context: NoUserCtx) -> None:
        """Creating via the kernel CRUD persists the custom column on the single users table."""
        kernel = get_kernel()
        registration = kernel.schemas.registration(
            name="ace",
            surname="Custom",
            email="ace@test.com",
            password="acepassword123",
            nickname="Ace",
        )
        user = kernel.crud_users.create(obj_in=registration, context=no_user_context)
        assert type(user) is kernel.user_model
        assert user.nickname == "Ace"

    def test_user_factory_forwards_extra_fields(self, user_factory: Callable[..., UserMixin]) -> None:
        """The user_factory forwards extra_fields onto the custom model."""
        user = user_factory(name="zed", extra_fields={"nickname": "Zed"})
        assert user.nickname == "Zed"

    def test_seeding_accepts_extra_fields(self, session: Session, settings: BaseKwikSettings) -> None:
        """The seeding battery forwards keyword extra fields to the custom model."""
        alt_settings = settings.model_copy(update={"FIRST_SUPERUSER": "root2@example.com"})
        superuser = create_first_superuser(session=session, settings=alt_settings, nickname="Root")
        assert superuser.nickname == "Root"
