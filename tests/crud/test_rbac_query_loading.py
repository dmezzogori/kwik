"""
Tests for RBAC relationship loading behavior.

Covers the query patterns of the roles/permissions object graph:
- batched (selectin) loading of ``User.roles`` and ``Role.permissions``,
  so listing users never triggers per-row roles queries (N+1);
- in-session freshness of the viewonly collections after role/permission
  assignment and removal;
- constant-query permission checks;
- deferral of the ``Role.user_count`` aggregate outside role reads.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from kwik.crud import UserCtx, crud_roles, crud_users
from kwik.models import Role, User
from kwik.schemas import RoleDefinition
from kwik.testing import assert_max_queries

if TYPE_CHECKING:
    from collections.abc import Callable

    from sqlalchemy.orm import Session

    from kwik.models import Permission


class TestBatchedRelationshipLoading:
    """User.roles and Role.permissions must batch-load, independent of result-set size."""

    def test_listing_users_reads_roles_in_constant_queries(
        self,
        user_factory: Callable[..., User],
        role_factory: Callable[..., Role],
        admin_context: UserCtx,
        session: Session,
    ) -> None:
        """Reading roles for N users costs a constant number of queries, not one per user."""
        role = role_factory(name="editor")
        users = [user_factory(name=f"batchuser{i}") for i in range(5)]
        for user in users:
            crud_roles.assign_user(role=role, user=user, context=admin_context)
        user_ids = [user.id for user in users]
        session.expunge_all()

        # 1 query for users + 1 batched roles load + 1 batched permissions load.
        with assert_max_queries(session, 3):
            loaded = session.execute(select(User).where(User.id.in_(user_ids))).scalars().all()
            role_names = {user.id: [role.name for role in user.roles] for user in loaded}

        assert all(names == ["editor"] for names in role_names.values())

    def test_listing_roles_reads_permissions_in_constant_queries(
        self,
        role_factory: Callable[..., Role],
        session: Session,
    ) -> None:
        """Reading permissions for N roles costs a constant number of queries, not one per role."""
        n_roles = 4
        for i in range(n_roles):
            role_factory(name=f"batchrole{i}", permissions=[f"perm{i}:read"])
        session.expunge_all()

        # 1 query for roles + 1 batched permissions load.
        with assert_max_queries(session, 2):
            roles = session.execute(select(Role).where(Role.name.like("batchrole%"))).scalars().all()
            permission_names = {role.name: [p.name for p in role.permissions] for role in roles}

        assert len(permission_names) == n_roles
        assert all(len(names) == 1 for names in permission_names.values())


class TestViewonlyCollectionFreshness:
    """Cached viewonly collections must reflect assign/remove within the same session."""

    def test_assign_user_refreshes_cached_user_roles(
        self,
        user_factory: Callable[..., User],
        role_factory: Callable[..., Role],
        admin_context: UserCtx,
    ) -> None:
        """A roles collection cached before assignment sees the new role after it."""
        user = user_factory(name="freshuser")
        role = role_factory(name="fresh_role")
        assert [r.name for r in user.roles] == []  # cache the (empty) collection

        crud_roles.assign_user(role=role, user=user, context=admin_context)

        assert "fresh_role" in [r.name for r in user.roles]

    def test_remove_user_refreshes_cached_user_roles(
        self,
        user_factory: Callable[..., User],
        admin_context: UserCtx,
    ) -> None:
        """A roles collection cached before removal no longer contains the removed role."""
        role_name = "removable_role"
        role = crud_roles.create(obj_in=RoleDefinition(name=role_name, is_active=True), context=admin_context)
        user = user_factory(name="removaluser")
        crud_roles.assign_user(role=role, user=user, context=admin_context)
        assert role_name in [r.name for r in user.roles]  # cache the collection

        crud_roles.remove_user(role=role, user=user, context=admin_context)

        assert role_name not in [r.name for r in user.roles]

    def test_assign_user_refreshes_cached_role_users(
        self,
        user_factory: Callable[..., User],
        role_factory: Callable[..., Role],
        admin_context: UserCtx,
    ) -> None:
        """A users collection cached before assignment sees the new member after it."""
        user = user_factory(name="memberuser")
        role = role_factory(name="member_role")
        assert user.id not in [u.id for u in role.users]  # cache the collection

        crud_roles.assign_user(role=role, user=user, context=admin_context)

        assert user.id in [u.id for u in role.users]

    def test_assign_permission_refreshes_cached_role_permissions(
        self,
        role_factory: Callable[..., Role],
        permission_factory: Callable[..., Permission],
        admin_context: UserCtx,
    ) -> None:
        """A permissions collection cached before assignment sees the new permission."""
        role = role_factory(name="perm_role")
        permission = permission_factory(name="docs:write")
        assert "docs:write" not in [p.name for p in role.permissions]  # cache the collection

        crud_roles.assign_permission(role=role, permission=permission, context=admin_context)

        assert "docs:write" in [p.name for p in role.permissions]

    def test_remove_permission_refreshes_cached_role_permissions(
        self,
        role_factory: Callable[..., Role],
        admin_context: UserCtx,
    ) -> None:
        """A permissions collection cached before removal no longer contains the permission."""
        role = role_factory(name="perm_removal_role", permissions=["docs:read"])
        cached = [p.name for p in role.permissions]  # cache the collection
        assert "docs:read" in cached
        permission = next(p for p in role.permissions if p.name == "docs:read")

        crud_roles.remove_permission(role=role, permission=permission, context=admin_context)

        assert "docs:read" not in [p.name for p in role.permissions]


class TestQueryBasedPermissionCheck:
    """has_permissions must run in a single query, independent of ORM cache state."""

    def test_has_permissions_true_for_granted_permission(
        self,
        user_factory: Callable[..., User],
        role_factory: Callable[..., Role],
        admin_context: UserCtx,
    ) -> None:
        """Returns True when the user holds the permission through a role."""
        role = role_factory(name="checker_role", permissions=["reports:read"])
        user = user_factory(name="checkeruser")
        crud_roles.assign_user(role=role, user=user, context=admin_context)

        assert crud_users.has_permissions(user=user, permissions=["reports:read"]) is True

    def test_has_permissions_false_for_missing_permission(
        self,
        user_factory: Callable[..., User],
    ) -> None:
        """Returns False when the user does not hold the permission."""
        user = user_factory(name="nopermuser")

        assert crud_users.has_permissions(user=user, permissions=["reports:read"]) is False

    def test_has_permissions_empty_requirement_is_true(
        self,
        user_factory: Callable[..., User],
    ) -> None:
        """An empty permission requirement is vacuously satisfied."""
        user = user_factory(name="emptypermuser")

        assert crud_users.has_permissions(user=user, permissions=[]) is True

    def test_has_permissions_falls_back_to_loaded_collections_when_detached(
        self,
        user_factory: Callable[..., User],
        role_factory: Callable[..., Role],
        admin_context: UserCtx,
        session: Session,
    ) -> None:
        """A detached user is checked against its already-loaded permissions."""
        role = role_factory(name="detached_role", permissions=["audit:read"])
        user = user_factory(name="detacheduser")
        crud_roles.assign_user(role=role, user=user, context=admin_context)
        _ = [p.name for role in user.roles for p in role.permissions]  # load collections
        session.expunge(user)

        assert crud_users.has_permissions(user=user, permissions=["audit:read"]) is True
        assert crud_users.has_permissions(user=user, permissions=["audit:write"]) is False

    def test_has_permissions_runs_at_most_one_query(
        self,
        user_factory: Callable[..., User],
        role_factory: Callable[..., Role],
        admin_context: UserCtx,
        session: Session,
    ) -> None:
        """The check costs at most one query even when collections are not cached."""
        role = role_factory(name="single_query_role", permissions=["metrics:read"])
        user = user_factory(name="singlequeryuser")
        crud_roles.assign_user(role=role, user=user, context=admin_context)
        session.expire(user, ["roles"])

        with assert_max_queries(session, 1):
            granted = crud_users.has_permissions(user=user, permissions=["metrics:read"])

        assert granted is True


class TestDeferredUserCount:
    """Role.user_count must not tax casual role loads, yet stay cheap in role reads."""

    def test_plain_role_load_does_not_include_user_count_subquery(
        self,
        role_factory: Callable[..., Role],
        session: Session,
    ) -> None:
        """Loading roles outside the roles CRUD does not pay the correlated count subquery."""
        role_factory(name="uncounted_role")
        session.expunge_all()

        with assert_max_queries(session, 10) as statements:
            session.execute(select(Role).where(Role.name == "uncounted_role")).scalars().all()

        assert not any("count(users_roles.id)" in stmt.lower() for stmt in statements)

    def test_crud_roles_get_exposes_user_count_without_extra_query(
        self,
        role_factory: Callable[..., Role],
        user_factory: Callable[..., User],
        admin_context: UserCtx,
        session: Session,
    ) -> None:
        """crud_roles.get loads user_count inline so serialization adds no query."""
        role = role_factory(name="counted_role")
        user = user_factory(name="counteduser")
        crud_roles.assign_user(role=role, user=user, context=admin_context)
        session.expunge_all()

        loaded = crud_roles.get(entity_id=role.id, context=admin_context)
        assert loaded is not None
        with assert_max_queries(session, 0):
            assert loaded.user_count == 1

    def test_crud_roles_get_multi_exposes_user_count_without_extra_queries(
        self,
        role_factory: Callable[..., Role],
        admin_context: UserCtx,
        session: Session,
    ) -> None:
        """crud_roles.get_multi loads user_count inline for every returned role."""
        for i in range(3):
            role_factory(name=f"counted_multi_{i}")
        session.expunge_all()

        _, roles = crud_roles.get_multi(context=admin_context)
        with assert_max_queries(session, 0):
            counts = [role.user_count for role in roles]

        assert all(count >= 0 for count in counts)
