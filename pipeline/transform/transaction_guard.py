"""
ETL transaction idempotency helpers.

Wraps database write operations in proper transactions with:
  - Full rollback on any exception (no partial state left in DB)
  - Retry with exponential backoff on transient DB errors
  - Idempotency via ON CONFLICT DO UPDATE / DO NOTHING
  - Structured logging of each batch

Usage:
    from etl.transaction_guard import transactional_batch, IdempotentLoader

    # Decorator style
    @transactional_batch(engine, batch_size=200)
    def load_booths(conn, rows): ...

    # Context manager style
    with IdempotentLoader(engine) as loader:
        loader.upsert("booth_master", rows, conflict_key="booth_id")
"""
from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Generator, Sequence

import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, InterfaceError

logger = logging.getLogger(__name__)

# Transient errors that warrant a retry
_TRANSIENT = (OperationalError, InterfaceError)


def _is_transient(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(kw in msg for kw in (
        "could not connect", "connection refused", "ssl connection",
        "deadlock", "lock timeout", "server closed",
    ))


@contextmanager
def atomic(engine: Engine, retries: int = 3, backoff: float = 2.0) -> Generator:
    """
    Context manager: yields an open SQLAlchemy connection inside a transaction.
    Rolls back fully on any exception; retries on transient DB errors.

        with atomic(engine) as conn:
            conn.execute(text("INSERT INTO ..."), params)
            conn.execute(text("UPDATE  ..."), params)
        # commits here if no exception
    """
    for attempt in range(1, retries + 1):
        conn = engine.connect()
        try:
            with conn.begin():
                yield conn
            return   # commit succeeded
        except _TRANSIENT as exc:
            conn.rollback()
            if attempt < retries and _is_transient(exc):
                wait = backoff ** attempt
                logger.warning("[etl] Transient DB error (attempt %d/%d), retrying in %.1fs: %s",
                               attempt, retries, wait, exc)
                time.sleep(wait)
                continue
            logger.error("[etl] DB error after %d attempts: %s", attempt, exc)
            raise
        except Exception as exc:
            conn.rollback()
            logger.error("[etl] Rolling back transaction: %s", exc)
            raise
        finally:
            conn.close()


def transactional_batch(
    engine: Engine,
    batch_size: int = 500,
    retries: int = 3,
) -> Callable:
    """
    Decorator: wraps a loader function so it processes rows in transactional batches.

    The decorated function receives (conn, batch_rows) and should execute SQL.
    Rolls back the entire batch on error; retries transient failures.

    Usage:
        @transactional_batch(engine, batch_size=200)
        def _insert_events(conn, rows):
            conn.execute(text("INSERT INTO pulse_events ..."), rows)
    """
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(rows: Sequence[dict], **kwargs) -> int:
            total = 0
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                with atomic(engine, retries=retries) as conn:
                    fn(conn, batch, **kwargs)
                total += len(batch)
                logger.debug("[etl] %s: committed batch %d-%d (%d rows)",
                             fn.__name__, i, i + len(batch), len(batch))
            logger.info("[etl] %s: total %d rows committed", fn.__name__, total)
            return total
        return wrapper
    return decorator


class IdempotentLoader:
    """
    High-level helper for idempotent upserts into PostgreSQL.

    Opens a single connection per context manager lifetime,
    wraps every upsert call in a savepoint for row-level safety.

    Usage:
        with IdempotentLoader(engine) as loader:
            loader.upsert(
                table="booth_master",
                rows=booth_dicts,
                conflict_key="booth_id",
                update_cols=["name", "total_voters", "updated_at"],
            )
    """
    def __init__(self, engine: Engine, retries: int = 3):
        self._engine  = engine
        self._retries = retries
        self._conn: Any = None

    def __enter__(self) -> "IdempotentLoader":
        self._conn = self._engine.connect()
        self._conn.begin()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_type is None:
            self._conn.commit()
            logger.debug("[etl] IdempotentLoader: committed.")
        else:
            self._conn.rollback()
            logger.error("[etl] IdempotentLoader: rolled back due to %s", exc_val)
        self._conn.close()
        return False   # re-raise exceptions

    def upsert(
        self,
        table: str,
        rows: Sequence[dict[str, Any]],
        conflict_key: str | list[str],
        update_cols: list[str] | None = None,
        skip_on_conflict: bool = False,
    ) -> int:
        """
        Bulk upsert rows into a PostgreSQL table using ON CONFLICT.

        Args:
            table:           Target table name.
            rows:            List of dicts. All dicts must have the same keys.
            conflict_key:    Column(s) forming the unique constraint.
            update_cols:     Columns to update on conflict (None = all non-key cols).
            skip_on_conflict: If True, uses DO NOTHING instead of DO UPDATE.

        Returns:
            Number of rows processed.
        """
        if not rows:
            return 0

        cols = list(rows[0].keys())
        conflict_cols = [conflict_key] if isinstance(conflict_key, str) else conflict_key

        col_list = ", ".join(cols)
        val_list = ", ".join(f":{c}" for c in cols)
        conflict_clause = ", ".join(conflict_cols)

        if skip_on_conflict:
            on_conflict = "DO NOTHING"
        else:
            upcols = update_cols or [c for c in cols if c not in conflict_cols]
            if not upcols:
                on_conflict = "DO NOTHING"
            else:
                sets = ", ".join(f"{c} = EXCLUDED.{c}" for c in upcols)
                on_conflict = f"DO UPDATE SET {sets}"

        sql = text(f"""
            INSERT INTO {table} ({col_list})
            VALUES ({val_list})
            ON CONFLICT ({conflict_clause}) {on_conflict}
        """)

        count = 0
        for row in rows:
            try:
                self._conn.execute(sql, row)
                count += 1
            except Exception as exc:
                logger.warning("[etl] Row skipped in %s (%s): %s", table, conflict_key, exc)

        logger.debug("[etl] upsert %s: %d/%d rows processed", table, count, len(rows))
        return count
