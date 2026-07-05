"""Tests for the first-superuser seeding battery."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.core.enum import Permissions
from kwik.models import RolePermission
from kwik.seeding import ADMIN_ROLE_NAME, create_first_superuser

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from kwik.settings import BaseKwikSettings


class TestCreateFirstSuperuser:
    """Tests for the create_first_superuser seeding battery."""

    def test_is_idempotent(self, session: Session, settings: BaseKwikSettings) -> None:
        """Calling the battery twice returns the same superuser."""
        first = create_first_superuser(session=session, settings=settings)
        second = create_first_superuser(session=session, settings=settings)
        assert first.id == second.id

    def test_superuser_has_admin_role_with_all_permissions(self, session: Session, settings: BaseKwikSettings) -> None:
        """The seeded superuser has the admin role and every permission."""
        user = create_first_superuser(session=session, settings=settings)
        assert ADMIN_ROLE_NAME in {role.name for role in user.roles}
        assert {permission.name for permission in user.permissions} == {p.value for p in Permissions}

    def test_rerun_restores_deleted_permission_assignment(
        self,
        session: Session,
        settings: BaseKwikSettings,
    ) -> None:
        """Re-running the battery converges: a role-permission assignment deleted since the first run is restored."""
        create_first_superuser(session=session, settings=settings)

        assignment = session.query(RolePermission).first()
        assert assignment is not None
        role_id = assignment.role_id
        permission_id = assignment.permission_id

        session.delete(assignment)
        session.flush()
        assert (
            session.query(RolePermission)
            .filter(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id)
            .one_or_none()
            is None
        )

        create_first_superuser(session=session, settings=settings)

        restored = (
            session.query(RolePermission)
            .filter(RolePermission.role_id == role_id, RolePermission.permission_id == permission_id)
            .one_or_none()
        )
        assert restored is not None
