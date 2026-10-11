"""
Main API router configuration for the Kwik framework.

This module assembles kwik's built-in endpoint routers. ``build_api_router`` lets an
application leave out the built-in routes it overrides or withdraws; ``api_router`` is
the complete set.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter

from .endpoints import login_router, permissions_router, roles_router, users_router

if TYPE_CHECKING:
    from collections.abc import Iterable

_BUILT_IN_ROUTERS: tuple[APIRouter, ...] = (login_router, users_router, roles_router, permissions_router)


def build_api_router(*, exclude: Iterable[tuple[str, str]] = ()) -> APIRouter:
    """
    Return kwik's built-in routes as one router, minus the excluded ``(METHOD, path)`` pairs.

    An application that overrides a built-in route registers its own handler first and
    excludes kwik's, so it serves one handler per pair and OpenAPI documents the one that
    runs. Without the exclusion, dispatch reaches the first handler but OpenAPI documents
    the second. Paths are the routers' full paths (``"/roles/{role_id}/users"``); methods
    are matched case-insensitively.

    Route objects move across untouched, so the routes that stay keep their response
    models, dependencies (authentication, permission gates) and OpenAPI metadata.

    Args:
        exclude: The ``(METHOD, path)`` pairs to leave out.

    Returns:
        A new router; kwik's own routers are not modified.

    Raises:
        ValueError: If a pair matches no route (a kwik upgrade renamed or moved it: fail
            at import instead of silently restoring an unguarded route), or matches a
            route that also serves methods that are not excluded (dropping the route
            would withdraw those too).

    """
    excluded = {(method.upper(), path) for method, path in exclude}
    built = APIRouter()
    matched: set[tuple[str, str]] = set()
    for router in _BUILT_IN_ROUTERS:
        for route in router.routes:
            path = getattr(route, "path", None)
            pairs = {(method, path) for method in getattr(route, "methods", None) or ()}
            hits = pairs & excluded
            if not hits:
                built.routes.append(route)
                continue
            if hits != pairs:
                surviving = sorted(method for method, _ in pairs - hits)
                dropped = sorted(method for method, _ in hits)
                msg = f"kwik route {path} also serves {surviving}; excluding {dropped} would withdraw them too"
                raise ValueError(msg)
            matched |= hits
    missing = sorted(excluded - matched)
    if missing:
        msg = f"kwik has no built-in route for {missing}"
        raise ValueError(msg)
    return built


api_router = build_api_router()

__all__ = ["api_router", "build_api_router"]
