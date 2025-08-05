"""Factory classes for creating test data using factory_boy."""

from __future__ import annotations

import factory
from factory.faker import Faker

from kwik.core.security import get_password_hash
from kwik.database.context_vars import current_user_ctx_var
from kwik.models.user import Permission, Role, User


class UserFactory(factory.Factory):
    """Factory for creating User test instances."""

    class Meta:
        """Factory configuration for User model."""

        model = User

    name = Faker("first_name")
    surname = Faker("last_name")
    email = Faker("email")
    hashed_password = factory.LazyAttribute(lambda _: get_password_hash("testpassword123"))
    is_active = True
    is_superuser = False


class SuperUserFactory(UserFactory):
    """Factory for creating superuser test instances."""

    is_superuser = True


class RoleFactory(factory.Factory):
    """Factory for creating Role test instances."""

    class Meta:
        """Factory configuration for Role model."""

        model = Role

    name = Faker("job")
    is_active = True
    is_locked = False
    creator_user_id = factory.LazyAttribute(
        lambda _: current_user_ctx_var.get().id if current_user_ctx_var.get() else None,
    )


class PermissionFactory(factory.Factory):
    """Factory for creating Permission test instances."""

    class Meta:
        """Factory configuration for Permission model."""

        model = Permission

    name = Faker("word")
    creator_user_id = factory.LazyAttribute(
        lambda _: current_user_ctx_var.get().id if current_user_ctx_var.get() else None,
    )
