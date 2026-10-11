"""Apps can exclude kwik's built-in routes to override or withdraw them (teban #378 / #302)."""

from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute

from kwik.api import build_api_router
from kwik.api.api import api_router
from kwik.api.endpoints import login_router, permissions_router, roles_router, users_router

RESET = ("PUT", "/users/{user_id}/reset-password")
STRIP = ("DELETE", "/roles/{role_id}/users")


def _pairs(router: APIRouter) -> list[tuple[str, str]]:
    """List a router's (METHOD, path) pairs in registration order."""
    return [
        (method, route.path)
        for route in router.routes
        if isinstance(route, APIRoute)
        for method in sorted(route.methods)
    ]


def _noop(**_: object) -> None:
    """Stand-in endpoint."""


def test_no_exclusion_keeps_every_route_in_order() -> None:
    """Without exclusions the builder reproduces kwik's four routers, in order."""
    expected = [
        pair for router in (login_router, users_router, roles_router, permissions_router) for pair in _pairs(router)
    ]
    assert _pairs(build_api_router()) == expected
    assert _pairs(api_router) == expected


def test_excluded_pairs_are_dropped() -> None:
    """Exactly the excluded pairs are missing from the result."""
    full = _pairs(build_api_router())
    filtered = _pairs(build_api_router(exclude={RESET, STRIP}))
    assert [pair for pair in full if pair not in {RESET, STRIP}] == filtered


def test_methods_are_case_insensitive() -> None:
    """A lower-case method names the same route."""
    assert RESET not in _pairs(build_api_router(exclude={("put", RESET[1])}))


def test_unknown_pair_raises() -> None:
    """A pair matching no route fails loudly instead of silently restoring the route."""
    with pytest.raises(ValueError, match="nope"):
        build_api_router(exclude={("PUT", "/users/{user_id}/nope")})


def test_partial_method_match_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Excluding one method of a multi-method route would withdraw the others, so it raises."""
    multi = APIRouter()
    multi.add_api_route("/multi", _noop, methods=["GET", "POST"])
    monkeypatch.setattr("kwik.api.api._BUILT_IN_ROUTERS", (multi,))
    with pytest.raises(ValueError, match="POST"):
        build_api_router(exclude={("GET", "/multi")})


def test_override_yields_single_openapi_operation() -> None:
    """An app that excludes and re-declares a route documents only its own handler."""
    override = APIRouter()

    def mine(user_id: int) -> None:
        """Stand-in for an app's guarded override."""

    override.add_api_route(RESET[1], mine, methods=[RESET[0]], operation_id="mine")
    app = FastAPI()
    app.include_router(override)
    app.include_router(build_api_router(exclude={RESET}))
    assert app.openapi()["paths"][RESET[1]]["put"]["operationId"] == "mine"


def test_result_is_a_fresh_router() -> None:
    """Building twice never shares or mutates kwik's own routers."""
    before = len(users_router.routes)
    first = build_api_router(exclude={RESET})
    second = build_api_router()
    assert first is not second
    assert len(users_router.routes) == before
