"""First-superuser seeding battery shared by production apps and kwik's own test fixtures."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.core.enum import Permissions
from kwik.crud import crud_permissions, crud_roles
from kwik.crud.context import Context
from kwik.kernel import get_kernel
from kwik.schemas import PermissionDefinition, RoleDefinition

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.models.user_mixin import UserMixin
    from kwik.settings import BaseKwikSettings

ADMIN_ROLE_NAME = "admin"


def create_first_superuser(*, session: Session, settings: BaseKwikSettings, **extra_fields: object) -> UserMixin:
    """
    Idempotently create the first superuser with the admin role and every permission.

    Creates the user from ``settings.FIRST_SUPERUSER`` / ``FIRST_SUPERUSER_PASSWORD``
    through the kernel's registered registration schema, so custom user models work
    transparently; ``extra_fields`` feeds additional registration fields required by
    custom models (e.g. non-null custom columns).

    Returns the superuser (existing or newly created).
    """
    kernel = get_kernel()
    no_user_context = Context(session=session, user=None)

    existing = kernel.crud_users.get_by_email(email=settings.FIRST_SUPERUSER, context=no_user_context)
    if existing is not None:
        return existing

    registration = kernel.schemas.registration(
        name="admin",
        surname="admin",
        email=settings.FIRST_SUPERUSER,
        password=settings.FIRST_SUPERUSER_PASSWORD,
        is_active=True,
        **extra_fields,
    )
    superuser = kernel.crud_users.create(obj_in=registration, context=no_user_context)

    admin_context = Context(session=session, user=superuser)
    admin_role = crud_roles.create_if_not_exist(
        obj_in=RoleDefinition(name=ADMIN_ROLE_NAME, is_active=True),
        context=admin_context,
        filters={"name": ADMIN_ROLE_NAME},
    )
    for permission_name in Permissions:
        permission = crud_permissions.create_if_not_exist(
            obj_in=PermissionDefinition(name=permission_name.value),
            context=admin_context,
            filters={"name": permission_name.value},
        )
        crud_roles.assign_permission(role=admin_role, permission=permission, context=admin_context)
    crud_roles.assign_user(role=admin_role, user=superuser, context=admin_context)

    return superuser


__all__ = ["ADMIN_ROLE_NAME", "create_first_superuser"]
