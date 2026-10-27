"""Authentication and login API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Body, Depends
from fastapi.security import OAuth2PasswordRequestForm  # noqa: TC002

from kwik.auth import open_session, refresh_session, revoke_session
from kwik.core.enum import Permissions
from kwik.crud import crud_users
from kwik.dependencies import (
    AuthSessions,
    NoUserContext,
    Settings,
    UserContext,
    current_token,
    current_user,
    has_permission,
)
from kwik.exceptions import AuthSessionsNotConfiguredError
from kwik.exceptions.auth import InvalidBearerTokenError
from kwik.exceptions.base import AccessDeniedError, TokenValidationError
from kwik.schemas import NewPassword, RefreshRequest, Token, UserProfile
from kwik.security import create_token, verify_password_reset_token

if TYPE_CHECKING:
    from kwik.models import User

login_router = APIRouter(prefix="/login", tags=["login"])


@login_router.post("/access-token", response_model=Token)
def login_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    settings: Settings,
    context: NoUserContext,
    store: AuthSessions,
) -> Token:
    """
    OAuth2 compatible token login, get an access token for future requests.

    When the application configured an auth session store, the login opens a session and the
    response also carries a refresh token; otherwise it returns a plain access token.

    Raises:
        IncorrectCredentials: If the provided credentials are incorrect

    """
    user = crud_users.authenticate(email=form_data.username, password=form_data.password, context=context)
    if store is None:
        return create_token(user_id=user.id, settings=settings)
    return open_session(user_id=user.id, settings=settings, store=store)


@login_router.post("/refresh", response_model=Token)
def refresh(body: RefreshRequest, settings: Settings, store: AuthSessions) -> Token:
    """
    Exchange a refresh token for a new access and refresh token pair (public route).

    Raises:
        AuthSessionsNotConfiguredError: If the application configured no auth session store.
        InvalidBearerTokenError: If the refresh token is invalid or expired.
        SessionRevokedError: If the token was reused, or its impersonation parent is dead; the session is revoked.

    """
    if store is None:
        raise AuthSessionsNotConfiguredError
    return refresh_session(refresh_token=body.refresh_token, settings=settings, store=store)


@login_router.post("/logout")
def logout(token: current_token, store: AuthSessions) -> dict:
    """
    Revoke the current session, which invalidates its access and refresh tokens.

    Raises:
        AuthSessionsNotConfiguredError: If the application configured no auth session store.
        InvalidBearerTokenError: If the token carries no session id.

    """
    if store is None:
        raise AuthSessionsNotConfiguredError
    if token.sid is None:
        raise InvalidBearerTokenError
    revoke_session(session_id=token.sid, store=store)
    return {"msg": "Session revoked"}


@login_router.post("/test-token", response_model=UserProfile)
def test_token(user: current_user) -> User:
    """Test access token."""
    return user


@login_router.post(
    "/impersonate",
    response_model=Token,
    dependencies=(has_permission(Permissions.impersonification),),
)
def impersonate(  # noqa: PLR0913
    user_id: int,
    user: current_user,
    token: current_token,
    settings: Settings,
    context: UserContext,
    store: AuthSessions,
) -> Token:
    """
    Impersonate a user.

    When the application configured an auth session store, impersonation opens a child session
    of the caller's session, with its own refresh token; revoking the caller's session revokes
    it too. Otherwise it returns a plain impersonation access token.

    Raises:
        AccessDeniedError: If the caller is already impersonating (no chains).

    """
    if token.kwik_impersonate != "":
        raise AccessDeniedError(detail="Already impersonating")
    user_to_impersonate = crud_users.get_if_exist(entity_id=user_id, context=context)
    if store is None:
        return create_token(user_id=user_to_impersonate.id, impersonator_user_id=user.id, settings=settings)
    return open_session(
        user_id=user_to_impersonate.id,
        impersonator_user_id=user.id,
        parent_session_id=token.sid,
        settings=settings,
        store=store,
    )


@login_router.post("/is_impersonating", response_model=bool)
def is_impersonating(token: current_token) -> bool:
    return token.kwik_impersonate != ""


@login_router.post("/stop_impersonating", response_model=Token)
def stop_impersonating(token: current_token, settings: Settings, store: AuthSessions) -> Token:
    """
    Stop impersonating and return a token for the impersonator.

    With an auth session store, this revokes the impersonation session and opens a fresh session
    for the impersonator; the impersonator's own session, which may be in use elsewhere, is left
    alone. Otherwise it returns a plain access token for the impersonator.

    Raises:
        TokenValidationError: If the token is not an impersonation token.
        InvalidBearerTokenError: If the impersonation session or the impersonator's session is
            no longer active.

    """
    if token.kwik_impersonate == "":
        raise TokenValidationError(detail="Not impersonating")
    impersonator_user_id = int(token.kwik_impersonate)
    if store is None:
        return create_token(user_id=impersonator_user_id, settings=settings)
    now = datetime.now(UTC)
    child = store.get(token.sid) if token.sid is not None else None
    parent = store.get(child.parent_session_id) if child is not None and child.parent_session_id else None
    if child is None or parent is None or not parent.is_active(now=now):
        raise InvalidBearerTokenError
    revoke_session(session_id=child.id, store=store, now=now)
    return open_session(user_id=impersonator_user_id, settings=settings, store=store, now=now)


@login_router.post("/reset-password")
def reset_password(
    token: Annotated[str, Body()],
    password: Annotated[NewPassword, Body()],
    settings: Settings,
    context: NoUserContext,
) -> dict:
    """Reset password using a self-service reset token (no authentication required)."""
    email = verify_password_reset_token(token=token, settings=settings, context=context)
    if not email:
        raise TokenValidationError

    crud_users.reset_password(email=email, password=password, context=context)
    return {"msg": "Password updated successfully"}


__all__ = ["login_router"]
