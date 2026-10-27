---
title: Authentication and sessions
description: Bearer tokens, optional auth sessions with refresh and revocation, and impersonation
---

Kwik authenticates requests with a bearer token. By default the token is a self-contained JWT, as in kwik 1.13. If you give the application an auth session store, every token belongs to a session that can be refreshed and revoked.

## Bearer tokens {#bearer-tokens}

Clients send the token in the `Authorization` header:

```http
Authorization: Bearer <access_token>
```

OpenAPI declares one HTTP scheme, `bearer`, so Swagger UI asks for the token directly. `POST /login/access-token` still takes the OAuth2 password form (`username`, `password`) and returns the token.

A request without a valid token gets `401` with a `WWW-Authenticate` header:

| Case | Header |
|------|--------|
| No `Authorization: Bearer` header | `Bearer` |
| Invalid, expired or revoked token, or a token of the wrong type | `Bearer error="invalid_token"` |

Inactive accounts are refused on the bearer path, with or without a store. Under impersonation the check applies to the acting account, so the impersonator must be active. Password login refuses an inactive account with the same answer as a wrong password.

## Without a store (default) {#without-a-store}

With no store the application behaves as kwik 1.13: the access token has no session, is valid until `ACCESS_TOKEN_EXPIRE_MINUTES` (default 10,080, seven days) and cannot be revoked. `POST /login/refresh` and `POST /login/logout` answer `501`.

## Turning sessions on {#sessions-on}

Pass a store to `Kwik`:

```python
from kwik import Kwik

app = Kwik(settings=settings, api_router=api_router, auth_session_store=MyStore()).app
```

If the store needs the request's database session, override the dependency instead:

```python
from kwik.dependencies import Session as DbSession
from kwik.dependencies.token import _get_auth_session_store


def _sql_store(session: DbSession) -> SqlStore:
    return SqlStore(session)


app.dependency_overrides[_get_auth_session_store] = _sql_store
```

The override must be a function whose parameter is annotated with the `Session` dependency; an un-annotated parameter (a lambda) is read by FastAPI as a query parameter and every route answers 422.

Then set the lifetimes. With sessions, the access token should be short; the refresh token carries the long lifetime:

| Setting | Default | Meaning |
|---------|---------|---------|
| `KWIK_ACCESS_TOKEN_EXPIRE_MINUTES` | 10080 | Access token lifetime. Set it to a few minutes (for example 15). |
| `KWIK_REFRESH_TOKEN_EXPIRE_MINUTES` | 43200 | Refresh expiry, 30 days. It moves forward on every rotation. |
| `KWIK_REFRESH_REUSE_GRACE_SECONDS` | 30 | How long the previous refresh token still works after a rotation. |

With a store, login and refresh return the `Token` body with two extra fields:

```json
{
  "access_token": "...",
  "token_type": "bearer",
  "refresh_token": "...",
  "expires_in": 900
}
```

`expires_in` is the access token lifetime in seconds. Without a store, both fields are serialised as `null`. Exchange the refresh token for a new pair:

```http
POST /login/refresh
Content-Type: application/json

{"refresh_token": "..."}
```

`/login/refresh` is public: the access token may already have expired. The refresh token travels in the JSON body only. An application that wants an HttpOnly cookie re-declares the route and calls `refresh_session` itself:

```python
from kwik.api import build_api_router
from kwik.auth import refresh_session

api_router.add_api_route("/login/refresh", my_cookie_refresh, methods=["POST"])
api_router.include_router(build_api_router(exclude=[("POST", "/login/refresh")]))
```

`POST /login/logout` revokes the current session, so its access and refresh tokens stop working.

### Rotation and reuse {#rotation}

Every refresh installs a new refresh token and invalidates the old one. Presenting the previous token again within the grace window (two tabs refreshing at once, a lost response) returns the same successor. Any other reuse of an old token is treated as theft: the whole session, and its impersonation children, is revoked.

Tokens that carry no session id are refused once a store is configured. You can switch sessions on in a single release; every user signs in once.

## The store contract {#store}

kwik adds no table. You persist the record and implement the protocol, both in `kwik.auth`.

```python
@dataclass
class AuthSession:
    id: str
    user_id: int
    created_at: datetime
    expires_at: datetime          # refresh expiry, whole seconds
    refresh_token_id: str         # jti of the current refresh token
    impersonator_user_id: int | None = None
    parent_session_id: str | None = None
    previous_refresh_token_id: str | None = None
    rotated_at: datetime | None = None
    revoked_at: datetime | None = None
```

Every datetime is timezone-aware UTC, on the way in and on the way out; normalise with `.astimezone(UTC)` if the database session time zone is not UTC. The store has five methods:

| Method | Contract |
|--------|----------|
| `create(session)` | Persist a new record. |
| `get(session_id)` | Return the record or `None`. |
| `update(session)` | Replace the record. For your own use; kwik's refresh never calls it. Setting `revoked_at` through `update` does not cascade to child sessions, so revoke with `revoke`. |
| `rotate(session_id, *, expected_token_id, new_token_id, expires_at, rotated_at)` | Compare-and-set, see below. |
| `revoke(session_id, *, at)` | Set `revoked_at` on the session and on every session whose `parent_session_id` is it. |

`rotate` must be atomic. Two concurrent refreshes with the same token must not both win, so do it as one statement:

```sql
UPDATE auth_sessions
SET previous_refresh_token_id = refresh_token_id,
    refresh_token_id = :new,
    expires_at = LEAST(:expires_at, created_at + interval '90 days'),
    rotated_at = :rotated_at
WHERE id = :id
  AND refresh_token_id = :expected
  AND revoked_at IS NULL
RETURNING *
```

It returns the new record (the clamped one: kwik mints the refresh token's expiry from the returned `expires_at`), or `None` when another rotation won or the session does not exist. kwik then re-reads the session and applies the grace check. The `revoked_at IS NULL` condition is not required by the protocol, but it keeps a revoked session from rotating in a race with `revoke`.

`get` runs on every authenticated request, and twice on a route that combines an `AuthenticatedRouter` with a permission gate. Keep it one indexed read. If you cache it, the cache TTL is your revocation bound.

The hard cap on a session (for example 90 days from `created_at`, however often it refreshes) is the store's policy, not kwik's. Enforce it in `rotate`: clamp the new `expires_at`, as the `LEAST(...)` above does, because every rotation overwrites `expires_at`. Changing it through `update` would not last. Use `update` only to revoke. Deactivating a user should also revoke their sessions: kwik refuses inactive accounts on the bearer path, but it does not revoke anything for you.

!!! warning "Revocation must be durable"
    When `refresh_session` detects reuse, or finds a child session whose parent is dead, it calls `store.revoke(...)` and then raises `SessionRevokedError`, a subclass of `InvalidBearerTokenError` with the same 401 and challenge. A request that raises normally rolls back kwik's request database session, which would discard a revocation the store wrote through it. Since 1.14.0 kwik makes an exception for `SessionRevokedError`: it commits the request session, then lets the error answer the 401. A store bound to the request session therefore keeps its revocation, on kwik's `POST /login/refresh` and on any application route that calls `refresh_session` under a `Kwik` app.

    The commit covers everything pending in the request session. On `POST /login/refresh` the store's own writes are the only ones, but an application route that writes other data and then calls `refresh_session` has those writes committed too when the session is revoked.

    Outside a `Kwik` app (a worker, a script, a FastAPI app without kwik's commit dependency) nothing commits for you, and `revoke` must commit on its own: use a separate connection or session and commit immediately, as the sketch below does. The sketch also works under a `Kwik` app. Keep `rotate` and `get` on the request session.

A sketch with SQLAlchemy, with columns you may add beyond the record (kind, client, user agent, IP, last used):

```python
from dataclasses import fields
from datetime import datetime, timedelta

from sqlalchemy import DateTime, ForeignKey, String, func, update
from sqlalchemy.orm import Mapped, Session, mapped_column

from kwik.auth import AuthSession
from kwik.models import Base  # or your own declarative base

HARD_CAP = timedelta(days=90)
AUTH_SESSION_FIELDS = [f.name for f in fields(AuthSession)]


class AuthSessionRow(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    refresh_token_id: Mapped[str] = mapped_column(String(64))
    impersonator_user_id: Mapped[int | None]
    parent_session_id: Mapped[str | None] = mapped_column(String(64), index=True)
    previous_refresh_token_id: Mapped[str | None] = mapped_column(String(64))
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # your own columns: user_agent, ip, last_used_at, ...


class SqlStore:
    def __init__(self, db: Session) -> None:
        self.db = db  # the request's session; commit and rollback are kwik's

    def create(self, session: AuthSession) -> None:
        self.db.add(AuthSessionRow(**vars(session)))
        self.db.flush()

    def get(self, session_id: str) -> AuthSession | None:
        row = self.db.get(AuthSessionRow, session_id)
        return None if row is None else AuthSession(**{f: getattr(row, f) for f in AUTH_SESSION_FIELDS})

    def rotate(self, session_id, *, expected_token_id, new_token_id, expires_at, rotated_at):
        row = self.db.execute(
            update(AuthSessionRow)
            .where(
                AuthSessionRow.id == session_id,
                AuthSessionRow.refresh_token_id == expected_token_id,
                AuthSessionRow.revoked_at.is_(None),
            )
            .values(
                previous_refresh_token_id=expected_token_id,
                refresh_token_id=new_token_id,
                # the hard cap lives here: every rotation overwrites expires_at
                expires_at=func.least(expires_at, AuthSessionRow.created_at + HARD_CAP),
                rotated_at=rotated_at,
            )
            .returning(AuthSessionRow)
        ).scalar_one_or_none()
        return None if row is None else AuthSession(**{f: getattr(row, f) for f in AUTH_SESSION_FIELDS})

    def revoke(self, session_id: str, *, at: datetime) -> None:
        # Own transaction, so the revocation lasts even where nothing commits the request session
        # (outside a Kwik app). Under a Kwik app, self.db would also do: kwik commits it on SessionRevokedError.
        with Session(self.db.get_bind()) as own, own.begin():
            own.execute(
                update(AuthSessionRow)
                .where(
                    (AuthSessionRow.id == session_id) | (AuthSessionRow.parent_session_id == session_id),
                    AuthSessionRow.revoked_at.is_(None),
                )
                .values(revoked_at=at)
            )

    # update(): same shape, copy the record's fields onto the row.
```

Wire the store in with the `_sql_store` override shown above.

## Impersonation {#impersonation}

`POST /login/impersonate?user_id=...` requires the impersonation permission. With a store it opens a child session: `user_id` is the impersonated user, `impersonator_user_id` the caller, and `parent_session_id` the caller's own session. The child has its own refresh token, and the token's `kwik_impersonate` claim keeps naming the impersonator across refreshes.

- Impersonating while already impersonating is refused with `403`, with or without a store.
- `POST /login/stop_impersonating` revokes the child session and opens a fresh session for the impersonator. The impersonator's own session, possibly in use in another tab, is left alone. It answers `401` if the child or the parent is no longer active.
- Revoking the parent revokes the children, so the store's `revoke` must cascade.
- `refresh_session` refuses a child whose parent session is missing or inactive, and revokes the child. The per-request check does not look at the parent; it relies on the cascade.

## Outside FastAPI {#outside-fastapi}

For SSE endpoints, workers and scripts, `authenticate_from_token` takes the store, so the session check applies there too:

```python
from kwik.security import authenticate_from_token

user = authenticate_from_token(token=raw_token, settings=settings, session=session, store=store)
```

To check a decoded payload yourself, import `require_active_session` from `kwik.auth` and call `require_active_session(payload=payload, store=store)`. It returns the `AuthSession`, or `None` when `store` is `None`. With a store it raises `InvalidBearerTokenError` when the token has no session id or is not an access token, or when the session is missing, revoked or expired. `open_session`, `refresh_session` and `revoke_session` are the same functions the login routes call. Outside a `Kwik` app, commit after a `SessionRevokedError` yourself if your store revokes through a session you control (see [Revocation must be durable](#store)).

## Testing {#testing}

`IdentityAwareTestClient` mints tokens for a user and opens a session when the application has a store. `InMemoryAuthSessionStore` is a ready-made store for tests. See [Testing](testing.md).
