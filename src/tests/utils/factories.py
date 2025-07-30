"""Factory classes for creating test data using factory_boy."""

from __future__ import annotations

import factory
from factory.faker import Faker

from kwik.core.security import get_password_hash
from kwik.models.user import Permission, Role, User


class UserFactory(factory.Factory):
    """Factory for creating User test instances."""

    class Meta:
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
        model = Role

    name = Faker("job")
    is_active = True
    is_locked = False


class PermissionFactory(factory.Factory):
    """Factory for creating Permission test instances."""

    class Meta:
        model = Permission

    name = Faker("word")
