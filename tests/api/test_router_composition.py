"""Tests for Kernel.create_api_router composition flags."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kwik.kernel import get_kernel

if TYPE_CHECKING:
    from fastapi import APIRouter


def _route_paths(router: APIRouter) -> set[str]:
    """
    Collect every concrete route path reachable from ``router``.

    FastAPI mounts routers included via ``include_router`` as opaque wrapper
    objects that expose the underlying router as ``original_router`` instead of
    flattening their routes into ``router.routes``; handle both shapes.
    """
    paths: set[str] = set()
    for route in router.routes:
        path = getattr(route, "path", None)
        if path is not None:
            paths.add(path)
        included = getattr(route, "original_router", None)
        if included is not None:
            paths.update(_route_paths(included))
    return paths


class TestCreateApiRouter:
    """Tests for the create_api_router composition flags."""

    def test_default_includes_all_builtin_routers(self) -> None:
        """Default composition mounts every built-in router."""
        paths = _route_paths(get_kernel().create_api_router())
        assert any(path.startswith("/users") for path in paths)
        assert any(path.startswith("/login") for path in paths)
        assert any(path.startswith("/roles") for path in paths)
        assert any(path.startswith("/permissions") for path in paths)

    def test_users_router_can_be_excluded(self) -> None:
        """Passing users=False drops the /users routes while keeping the rest."""
        paths = _route_paths(get_kernel().create_api_router(users=False))
        assert not any(path.startswith("/users") for path in paths)
        assert any(path.startswith("/login") for path in paths)

    def test_only_login_router(self) -> None:
        """Disabling users, roles, and permissions leaves only /login routes."""
        paths = _route_paths(get_kernel().create_api_router(users=False, roles=False, permissions=False))
        assert paths
        assert all(path.startswith("/login") for path in paths)
