# Database connection pool

Kwik creates one SQLAlchemy engine per worker process, and each engine keeps its own
connection pool. Three settings size it. Like every setting, they take the `KWIK_` prefix
in the environment.

| Setting | Env variable | Default | Meaning |
|---------|--------------|---------|---------|
| `POSTGRES_POOL_SIZE` | `KWIK_POSTGRES_POOL_SIZE` | `10` | Connections the pool keeps open. |
| `POSTGRES_MAX_OVERFLOW` | `KWIK_POSTGRES_MAX_OVERFLOW` | `20` | Extra connections opened under load and closed when returned. |
| `POSTGRES_POOL_TIMEOUT` | `KWIK_POSTGRES_POOL_TIMEOUT` | `10.0` | Seconds a checkout waits for a free connection before raising `sqlalchemy.exc.TimeoutError`. |

## Why the checkout timeout is 10 seconds

When all `POSTGRES_POOL_SIZE + POSTGRES_MAX_OVERFLOW` connections are checked out, the
next request waits for one to come back. SQLAlchemy's default wait is 30 seconds. For
those 30 seconds the request holds its worker thread, which makes the starvation worse,
and then it fails anyway. Most reverse proxies time out sooner, so the client sees a
gateway timeout rather than the real cause.

At 10 seconds a starved request fails quickly, and the error names the pool.
10 seconds is also shorter than the renewal interval of periodic work such as a
streaming connection that renews a lease every 15 seconds, so a starved renewal fails
before the next one is due, instead of overlapping it.

Raise it only if your requests legitimately queue for connections under normal load. In
that case, a larger pool is usually the better fix.

## Sizing the pool against the worker count

Every worker process (`BACKEND_WORKERS`) has its own pool. Together the workers can open:

```
BACKEND_WORKERS × (POSTGRES_POOL_SIZE + POSTGRES_MAX_OVERFLOW)
```

connections. That number must stay below the database server's `max_connections`, minus
the connections taken by other clients of the same database (background workers,
migrations, administration tools). Set `POSTGRES_MAX_CONNECTIONS` to the server's limit:
at startup Kwik logs a warning that names the three numbers when the product exceeds it.

Example: with 4 workers and the defaults, the workers can open 4 × 30 = 120 connections.
That is more than PostgreSQL's default `max_connections` of 100, so lower the overflow
(for example `POSTGRES_MAX_OVERFLOW=10`, giving 80) or raise the server's limit.
