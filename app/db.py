"""PostgreSQL connection helpers for app persistence."""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Dict, Iterator

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - depends on optional runtime dependency
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _connect_target() -> str | Dict[str, Any] | None:
    """Build a psycopg connection target from environment variables."""
    dsn = os.getenv("POSTGRES_DSN") or os.getenv("DATABASE_URL")
    if dsn:
        return dsn

    required = ("PGHOST", "PGPORT", "PGDATABASE", "PGUSER", "PGPASSWORD")
    env_values = {k: os.getenv(k) for k in required}
    if not all(env_values.values()):
        return None

    return {
        "host": env_values["PGHOST"],
        "port": env_values["PGPORT"],
        "dbname": env_values["PGDATABASE"],
        "user": env_values["PGUSER"],
        "password": env_values["PGPASSWORD"],
        "sslmode": os.getenv("PGSSLMODE", "prefer"),
    }


def is_database_configured() -> bool:
    """Return True when Postgres connection settings are present."""
    return _connect_target() is not None


def is_database_ready() -> bool:
    """Return True when psycopg is installed and DB settings are present."""
    return psycopg is not None and is_database_configured()


@contextmanager
def get_connection(*, autocommit: bool = False) -> Iterator[psycopg.Connection]:
    """Yield a PostgreSQL connection configured from environment variables."""
    if psycopg is None:
        raise RuntimeError(
            "psycopg is not installed. Install dependencies from requirements.txt."
        )

    target = _connect_target()
    if target is None:
        raise RuntimeError(
            "Postgres is not configured. Set DATABASE_URL/POSTGRES_DSN or "
            "PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD."
        )

    connect_kwargs: Dict[str, Any] = {"row_factory": dict_row, "autocommit": autocommit}
    if isinstance(target, str):
        conn = psycopg.connect(target, **connect_kwargs)
    else:
        conn = psycopg.connect(**target, **connect_kwargs)

    try:
        yield conn
    finally:
        conn.close()
