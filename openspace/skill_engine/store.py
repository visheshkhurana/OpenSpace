"""
Storage location: <project_root>/.openspace/openspace.db
Tables:
  skill_records          — SkillRecord main table
  skill_lineage_parents  — Lineage parent-child relationships (many-to-many)
  execution_analyses     — ExecutionAnalysis records (one per task)
  skill_judgments         — Per-skill judgments within an analysis
  skill_tool_deps        — Tool dependencies
  skill_tags             — Auxiliary tags

Dual-backend design
-------------------
When the environment variable ``OPENSPACE_SKILL_DB_URL`` is **unset** (or does
not start with ``postgresql://`` / ``postgres://``), this module behaves
100% identically to the original SQLite-only implementation — zero regression.

When ``OPENSPACE_SKILL_DB_URL`` is set to a PostgreSQL connection string the
store connects to Postgres via **psycopg v3** and uses the same schema /
queries adapted for the Postgres dialect.  Requires the extra package::

    psycopg[binary,pool]>=3.1

The adapter is chosen once in ``SkillStore.__init__`` and the rest of the
class is backend-agnostic.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import threading
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from .patch import collect_skill_snapshot, compute_unified_diff
from .types import (
    EvolutionSuggestion,
    ExecutionAnalysis,
    SkillCategory,
    SkillJudgment,
    SkillLineage,
    SkillOrigin,
    SkillRecord,
    SkillVisibility,
)
from openspace.utils.logging import Logger
from openspace.config.constants import PROJECT_ROOT

logger = Logger.get_logger(__name__)


# ---------------------------------------------------------------------------
# Retry decorator — catches transient errors from either backend
# ---------------------------------------------------------------------------

def _db_retry(
    max_retries: int = 5,
    initial_delay: float = 0.1,
    backoff: float = 2.0,
):
    """Retry on transient SQLite *or* Postgres errors with exponential backoff.

    Catches ``OperationalError`` (e.g. "database is locked" / "connection
    lost") and ``DatabaseError`` from SQLite.  When psycopg is available it
    also catches ``psycopg.OperationalError`` and
    ``psycopg.errors.SerializationFailure`` (serialization / deadlock).
    Programming errors (``InterfaceError``) are NOT retried.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build the tuple of retryable exception types lazily so that
            # psycopg is truly optional — if it is not installed the SQLite
            # path still works normally.
            retryable: tuple = (sqlite3.OperationalError, sqlite3.DatabaseError)
            try:
                import psycopg  # noqa: PLC0415
                import psycopg.errors  # noqa: PLC0415
                retryable = (
                    sqlite3.OperationalError,
                    sqlite3.DatabaseError,
                    psycopg.OperationalError,
                    psycopg.errors.SerializationFailure,
                )
            except ImportError:
                pass

            delay = initial_delay
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except retryable as exc:
                    if attempt == max_retries - 1:
                        logger.error(
                            f"DB {func.__name__} failed after "
                            f"{max_retries} retries: {exc}"
                        )
                        raise
                    logger.warning(
                        f"DB {func.__name__} retry {attempt + 1}"
                        f"/{max_retries}: {exc}"
                    )
                    time.sleep(delay)
                    delay *= backoff

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# DDL — shared schema definition (SQLite dialect)
# ---------------------------------------------------------------------------

_DDL = """\
CREATE TABLE IF NOT EXISTS skill_records (
    skill_id               TEXT PRIMARY KEY,
    name                   TEXT NOT NULL,
    description            TEXT NOT NULL DEFAULT '',
    path                   TEXT NOT NULL DEFAULT '',
    is_active              INTEGER NOT NULL DEFAULT 1,
    category               TEXT NOT NULL DEFAULT 'workflow',
    visibility             TEXT NOT NULL DEFAULT 'private',
    creator_id             TEXT NOT NULL DEFAULT '',
    lineage_origin         TEXT NOT NULL DEFAULT 'imported',
    lineage_generation     INTEGER NOT NULL DEFAULT 0,
    lineage_source_task_id TEXT,
    lineage_change_summary TEXT NOT NULL DEFAULT '',
    lineage_content_diff   TEXT NOT NULL DEFAULT '',
    lineage_content_snapshot TEXT NOT NULL DEFAULT '{}',
    lineage_created_at     TEXT NOT NULL,
    lineage_created_by     TEXT NOT NULL DEFAULT '',
    total_selections       INTEGER NOT NULL DEFAULT 0,
    total_applied          INTEGER NOT NULL DEFAULT 0,
    total_completions      INTEGER NOT NULL DEFAULT 0,
    total_fallbacks        INTEGER NOT NULL DEFAULT 0,
    first_seen             TEXT NOT NULL,
    last_updated           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sr_category ON skill_records(category);
CREATE INDEX IF NOT EXISTS idx_sr_updated  ON skill_records(last_updated);
CREATE INDEX IF NOT EXISTS idx_sr_active   ON skill_records(is_active);
CREATE INDEX IF NOT EXISTS idx_sr_name     ON skill_records(name);

CREATE TABLE IF NOT EXISTS skill_lineage_parents (
    skill_id        TEXT NOT NULL
        REFERENCES skill_records(skill_id) ON DELETE CASCADE,
    parent_skill_id TEXT NOT NULL,
    PRIMARY KEY (skill_id, parent_skill_id)
);
CREATE INDEX IF NOT EXISTS idx_lp_parent
    ON skill_lineage_parents(parent_skill_id);

-- One row per task.  task_id is UNIQUE (at most one analysis per task).
CREATE TABLE IF NOT EXISTS execution_analyses (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id                 TEXT NOT NULL UNIQUE,
    timestamp               TEXT NOT NULL,
    task_completed          INTEGER NOT NULL DEFAULT 0,
    execution_note          TEXT NOT NULL DEFAULT '',
    tool_issues             TEXT NOT NULL DEFAULT '[]',
    candidate_for_evolution INTEGER NOT NULL DEFAULT 0,
    evolution_processed_at  TEXT DEFAULT NULL,
    evolution_suggestions   TEXT NOT NULL DEFAULT '[]',
    analyzed_by             TEXT NOT NULL DEFAULT '',
    analyzed_at             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ea_task  ON execution_analyses(task_id);
CREATE INDEX IF NOT EXISTS idx_ea_ts    ON execution_analyses(timestamp);

-- Per-skill judgments within an analysis.
-- FK to execution_analyses.id (CASCADE delete).
-- skill_id is a plain TEXT — no FK to skill_records so that
-- historical judgments survive skill deletion.
CREATE TABLE IF NOT EXISTS skill_judgments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id    INTEGER NOT NULL
        REFERENCES execution_analyses(id) ON DELETE CASCADE,
    skill_id       TEXT NOT NULL,
    skill_applied  INTEGER NOT NULL DEFAULT 0,
    note           TEXT NOT NULL DEFAULT '',
    UNIQUE(analysis_id, skill_id)
);
CREATE INDEX IF NOT EXISTS idx_sj_skill    ON skill_judgments(skill_id);
CREATE INDEX IF NOT EXISTS idx_sj_analysis ON skill_judgments(analysis_id);

CREATE TABLE IF NOT EXISTS skill_tool_deps (
    skill_id TEXT NOT NULL
        REFERENCES skill_records(skill_id) ON DELETE CASCADE,
    tool_key TEXT NOT NULL,
    critical INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (skill_id, tool_key)
);
CREATE INDEX IF NOT EXISTS idx_td_tool ON skill_tool_deps(tool_key);

CREATE TABLE IF NOT EXISTS skill_tags (
    skill_id TEXT NOT NULL
        REFERENCES skill_records(skill_id) ON DELETE CASCADE,
    tag      TEXT NOT NULL,
    PRIMARY KEY (skill_id, tag)
);
"""

# Postgres DDL: same as above with AUTOINCREMENT → GENERATED BY DEFAULT AS IDENTITY
_DDL_PG = """\
CREATE TABLE IF NOT EXISTS skill_records (
    skill_id               TEXT PRIMARY KEY,
    name                   TEXT NOT NULL,
    description            TEXT NOT NULL DEFAULT '',
    path                   TEXT NOT NULL DEFAULT '',
    is_active              INTEGER NOT NULL DEFAULT 1,
    category               TEXT NOT NULL DEFAULT 'workflow',
    visibility             TEXT NOT NULL DEFAULT 'private',
    creator_id             TEXT NOT NULL DEFAULT '',
    lineage_origin         TEXT NOT NULL DEFAULT 'imported',
    lineage_generation     INTEGER NOT NULL DEFAULT 0,
    lineage_source_task_id TEXT,
    lineage_change_summary TEXT NOT NULL DEFAULT '',
    lineage_content_diff   TEXT NOT NULL DEFAULT '',
    lineage_content_snapshot TEXT NOT NULL DEFAULT '{}',
    lineage_created_at     TEXT NOT NULL,
    lineage_created_by     TEXT NOT NULL DEFAULT '',
    total_selections       INTEGER NOT NULL DEFAULT 0,
    total_applied          INTEGER NOT NULL DEFAULT 0,
    total_completions      INTEGER NOT NULL DEFAULT 0,
    total_fallbacks        INTEGER NOT NULL DEFAULT 0,
    first_seen             TEXT NOT NULL,
    last_updated           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sr_category ON skill_records(category);
CREATE INDEX IF NOT EXISTS idx_sr_updated  ON skill_records(last_updated);
CREATE INDEX IF NOT EXISTS idx_sr_active   ON skill_records(is_active);
CREATE INDEX IF NOT EXISTS idx_sr_name     ON skill_records(name);

CREATE TABLE IF NOT EXISTS skill_lineage_parents (
    skill_id        TEXT NOT NULL
        REFERENCES skill_records(skill_id) ON DELETE CASCADE,
    parent_skill_id TEXT NOT NULL,
    PRIMARY KEY (skill_id, parent_skill_id)
);
CREATE INDEX IF NOT EXISTS idx_lp_parent
    ON skill_lineage_parents(parent_skill_id);

CREATE TABLE IF NOT EXISTS execution_analyses (
    id                      BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    task_id                 TEXT NOT NULL UNIQUE,
    timestamp               TEXT NOT NULL,
    task_completed          INTEGER NOT NULL DEFAULT 0,
    execution_note          TEXT NOT NULL DEFAULT '',
    tool_issues             TEXT NOT NULL DEFAULT '[]',
    candidate_for_evolution INTEGER NOT NULL DEFAULT 0,
    evolution_processed_at  TEXT DEFAULT NULL,
    evolution_suggestions   TEXT NOT NULL DEFAULT '[]',
    analyzed_by             TEXT NOT NULL DEFAULT '',
    analyzed_at             TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ea_task  ON execution_analyses(task_id);
CREATE INDEX IF NOT EXISTS idx_ea_ts    ON execution_analyses(timestamp);

CREATE TABLE IF NOT EXISTS skill_judgments (
    id             BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
    analysis_id    BIGINT NOT NULL
        REFERENCES execution_analyses(id) ON DELETE CASCADE,
    skill_id       TEXT NOT NULL,
    skill_applied  INTEGER NOT NULL DEFAULT 0,
    note           TEXT NOT NULL DEFAULT '',
    UNIQUE(analysis_id, skill_id)
);
CREATE INDEX IF NOT EXISTS idx_sj_skill    ON skill_judgments(skill_id);
CREATE INDEX IF NOT EXISTS idx_sj_analysis ON skill_judgments(analysis_id);

CREATE TABLE IF NOT EXISTS skill_tool_deps (
    skill_id TEXT NOT NULL
        REFERENCES skill_records(skill_id) ON DELETE CASCADE,
    tool_key TEXT NOT NULL,
    critical INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (skill_id, tool_key)
);
CREATE INDEX IF NOT EXISTS idx_td_tool ON skill_tool_deps(tool_key);

CREATE TABLE IF NOT EXISTS skill_tags (
    skill_id TEXT NOT NULL
        REFERENCES skill_records(skill_id) ON DELETE CASCADE,
    tag      TEXT NOT NULL,
    PRIMARY KEY (skill_id, tag)
);
"""


# ---------------------------------------------------------------------------
# Database adapter abstraction
# ---------------------------------------------------------------------------

class _DatabaseAdapter(ABC):
    """Abstract adapter that hides SQLite vs Postgres differences."""

    # ------------------------------------------------------------------
    # SQL dialect helpers
    # ------------------------------------------------------------------

    def sql(self, text: str) -> str:  # noqa: D102
        """Translate a SQL string from SQLite dialect to this backend's dialect.

        The default (SQLite) implementation returns *text* unchanged.
        Subclasses override to do e.g. ``?`` → ``%s`` substitution.
        """
        return text

    # ------------------------------------------------------------------
    # Connection / context management
    # ------------------------------------------------------------------

    @abstractmethod
    @contextmanager
    def reader(self):
        """Yield a read-capable connection/cursor context for SELECT queries."""

    @abstractmethod
    def execute(self, conn_or_cursor, sql: str, params=()):
        """Execute *sql* with *params* on *conn_or_cursor* and return cursor."""

    @abstractmethod
    def executemany(self, conn_or_cursor, sql: str, seq):
        """Execute *sql* for each params tuple in *seq*."""

    @abstractmethod
    def fetchone(self, cursor) -> Optional[Dict[str, Any]]:
        """Fetch one row as a dict (or None)."""

    @abstractmethod
    def fetchall(self, cursor) -> List[Dict[str, Any]]:
        """Fetch all rows as a list of dicts."""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @abstractmethod
    def init_db(self, write_conn) -> None:
        """Create schema (idempotent)."""

    @abstractmethod
    def migrate_add_evolution_processed_at(self, write_conn) -> None:
        """Add evolution_processed_at column if missing (idempotent)."""

    @abstractmethod
    def close(self, write_conn) -> None:
        """Tear down the backend (checkpoint WAL / close pool)."""

    @abstractmethod
    def vacuum(self, write_conn) -> None:
        """Compact / analyse the database."""

    def cleanup_wal_on_startup(self, db_path: Path) -> None:
        """SQLite-only hook — no-op by default for non-SQLite backends."""


# ---------------------------------------------------------------------------
# SQLite adapter — wraps original behaviour exactly
# ---------------------------------------------------------------------------

class _SQLiteAdapter(_DatabaseAdapter):
    """Thin wrapper that preserves all original SQLite behaviour."""

    # SQL dialect: SQLite uses ``?`` placeholders — no translation needed.
    def sql(self, text: str) -> str:
        return text

    @contextmanager
    def reader(self, db_path: Path):  # type: ignore[override]
        """Open a temporary read-only WAL connection."""
        conn = self._make_connection(db_path, read_only=True)
        try:
            yield conn
        finally:
            conn.close()

    def _make_connection(
        self, db_path: Path, *, read_only: bool
    ) -> sqlite3.Connection:
        """Create a tuned SQLite connection.

        Write connection: ``check_same_thread=False`` for cross-thread
        usage via ``asyncio.to_thread()``.

        Read connection: ``query_only=ON`` pragma for safety.
        """
        conn = sqlite3.connect(
            str(db_path),
            timeout=30.0,
            check_same_thread=False,
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-16000")  # 16 MB
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA foreign_keys=ON")
        if read_only:
            conn.execute("PRAGMA query_only=ON")
        conn.row_factory = sqlite3.Row
        return conn

    def make_write_connection(self, db_path: Path) -> sqlite3.Connection:
        return self._make_connection(db_path, read_only=False)

    def execute(self, conn_or_cursor, sql: str, params=()):
        return conn_or_cursor.execute(sql, params)

    def executemany(self, conn_or_cursor, sql: str, seq):
        return conn_or_cursor.executemany(sql, seq)

    def fetchone(self, cursor) -> Optional[Dict[str, Any]]:
        row = cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self, cursor) -> List[Dict[str, Any]]:
        return [dict(r) for r in cursor.fetchall()]

    def init_db(self, write_conn) -> None:
        write_conn.executescript(_DDL)
        self.migrate_add_evolution_processed_at(write_conn)
        write_conn.commit()

    def migrate_add_evolution_processed_at(self, write_conn) -> None:
        try:
            write_conn.execute(
                "ALTER TABLE execution_analyses "
                "ADD COLUMN evolution_processed_at TEXT DEFAULT NULL"
            )
        except sqlite3.OperationalError:
            pass  # column already exists

    def close(self, write_conn) -> None:
        try:
            write_conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            write_conn.close()
        except Exception:
            pass

    def vacuum(self, write_conn) -> None:
        write_conn.execute("VACUUM")

    def cleanup_wal_on_startup(self, db_path: Path) -> None:
        """Remove stale WAL/SHM left by unclean shutdown.

        If the main DB file is empty (0 bytes) but WAL/SHM companions
        exist, the database is unrecoverable — delete the companions
        so SQLite can start fresh.
        """
        if not db_path.exists():
            return
        wal = Path(f"{db_path}-wal")
        shm = Path(f"{db_path}-shm")
        if db_path.stat().st_size == 0 and (wal.exists() or shm.exists()):
            logger.warning(
                "Empty DB with WAL/SHM — removing for crash recovery"
            )
            for f in (wal, shm):
                if f.exists():
                    f.unlink()


# ---------------------------------------------------------------------------
# Postgres adapter — psycopg v3 + connection pool
# ---------------------------------------------------------------------------

class _PostgresAdapter(_DatabaseAdapter):
    """Adapter for PostgreSQL via psycopg v3 with a connection pool.

    Requires ``psycopg[binary,pool]>=3.1``.
    """

    def __init__(self, dsn: str) -> None:
        try:
            import psycopg_pool  # noqa: PLC0415
            from psycopg.rows import dict_row  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "psycopg[binary,pool]>=3.1 is required for the Postgres "
                "backend. Install it with: pip install 'psycopg[binary,pool]'"
            ) from exc

        self._dsn = dsn
        self._dict_row = dict_row
        self._pool = psycopg_pool.ConnectionPool(
            dsn,
            min_size=1,
            max_size=5,
            kwargs={"row_factory": dict_row},
            open=True,
        )

    # ------------------------------------------------------------------
    # SQL dialect translation: ``?`` → ``%s``
    # ------------------------------------------------------------------

    def sql(self, text: str) -> str:  # noqa: D102
        """Replace ``?`` parameter markers with ``%s`` for psycopg."""
        return text.replace("?", "%s")

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    @contextmanager
    def reader(self):  # type: ignore[override]
        """Borrow a connection from the pool for a read query."""
        with self._pool.connection() as conn:
            yield conn

    @contextmanager
    def writer(self):
        """Borrow a connection from the pool for a write transaction."""
        with self._pool.connection() as conn:
            yield conn

    def execute(self, conn_or_cursor, sql: str, params=()):
        return conn_or_cursor.execute(self.sql(sql), params or None)

    def executemany(self, conn_or_cursor, sql: str, seq):
        return conn_or_cursor.executemany(self.sql(sql), seq)

    def fetchone(self, cursor) -> Optional[Dict[str, Any]]:
        return cursor.fetchone()  # already a dict via dict_row

    def fetchall(self, cursor) -> List[Dict[str, Any]]:
        return cursor.fetchall()  # already list[dict] via dict_row

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init_db(self, _write_conn) -> None:
        """Create schema by executing each DDL statement in its own command."""
        stmts = [
            s.strip()
            for s in _DDL_PG.split(";")
            if s.strip()
        ]
        with self._pool.connection() as conn:
            for stmt in stmts:
                try:
                    conn.execute(stmt)
                except Exception:
                    # Individual index/table creation may fail if object
                    # already exists with a different definition — log and
                    # continue so the rest of the schema is applied.
                    conn.rollback()
                    logger.debug(
                        f"PG DDL stmt skipped (already exists?): "
                        f"{stmt[:60]}..."
                    )
                    conn.execute("BEGIN")
            conn.commit()
        self.migrate_add_evolution_processed_at(None)

    def migrate_add_evolution_processed_at(self, _write_conn) -> None:
        """Add column using Postgres ``ADD COLUMN IF NOT EXISTS`` (PG 9.6+)."""
        with self._pool.connection() as conn:
            conn.execute(
                "ALTER TABLE execution_analyses "
                "ADD COLUMN IF NOT EXISTS evolution_processed_at TEXT DEFAULT NULL"
            )
            conn.commit()

    def close(self, _write_conn) -> None:
        """Close the connection pool."""
        try:
            self._pool.close()
        except Exception:
            pass

    def vacuum(self, _write_conn) -> None:
        """Run ``VACUUM ANALYZE`` outside a transaction (requires autocommit)."""
        import psycopg  # noqa: PLC0415
        with psycopg.connect(self._dsn, autocommit=True) as conn:
            conn.execute("VACUUM ANALYZE")


# ---------------------------------------------------------------------------
# SkillStore — public API (dialect-agnostic)
# ---------------------------------------------------------------------------

class SkillStore:
    """Dual-backend persistence engine — Skill quality tracking and evolution ledger.

    Architecture:
        Write path: async method → asyncio.to_thread → _xxx_sync → self._mu lock → adapter
        Read path: sync method → self._reader() → independent short connection (WAL parallel read)

    Backend selection:
        ``OPENSPACE_SKILL_DB_URL`` unset (or not a postgres URL) → SQLite (default)
        ``OPENSPACE_SKILL_DB_URL=postgresql://...`` → Postgres via psycopg v3

    Lifecycle: ``__init__()`` → use → ``close()``
    Also supports async context manager::

        async with SkillStore() as store:
            await store.save_record(record)
            rec = store.load_record(skill_id)
    """

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            db_dir = PROJECT_ROOT / ".openspace"
            db_dir.mkdir(parents=True, exist_ok=True)
            db_path = db_dir / "openspace.db"

        self._db_path = Path(db_path)
        self._mu = threading.Lock()
        self._closed = False

        # --- Backend selection -------------------------------------------
        _url = os.getenv("OPENSPACE_SKILL_DB_URL", "").strip()
        if _url.startswith("postgresql://") or _url.startswith("postgres://"):
            self._adapter: _DatabaseAdapter = _PostgresAdapter(_url)
            self._conn = None  # Postgres uses the pool; no persistent write conn
            self._is_postgres = True
            logger.debug("SkillStore: using Postgres backend")
        else:
            sqlite_adapter = _SQLiteAdapter()
            self._adapter = sqlite_adapter
            self._is_postgres = False
            # Crash recovery: clean up stale WAL/SHM from unclean shutdown
            self._adapter.cleanup_wal_on_startup(self._db_path)
            # Persistent write connection (SQLite path)
            self._conn = sqlite_adapter.make_write_connection(self._db_path)
            logger.debug(f"SkillStore: using SQLite backend at {self._db_path}")

        self._init_db()
        logger.debug("SkillStore ready")

    # ------------------------------------------------------------------
    # Internal: connection/reader helpers
    # ------------------------------------------------------------------

    @contextmanager
    def _reader(self):
        """Open a temporary read-capable connection.

        SQLite: ephemeral read-only WAL connection.
        Postgres: pool connection (always dict rows).
        """
        self._ensure_open()
        if self._is_postgres:
            with self._adapter.reader() as conn:  # type: ignore[arg-type]
                yield conn
        else:
            with self._adapter.reader(self._db_path) as conn:  # type: ignore[call-arg]
                yield conn

    def _exec(self, sql: str, params=()):
        """Execute *sql* on the write connection and return cursor.

        SQLite: uses ``self._conn`` (persistent write connection).
        Postgres: raises — callers must use ``_pg_writer`` context instead.
        """
        return self._adapter.execute(self._conn, sql, params)

    @contextmanager
    def _pg_writer(self):
        """Context manager that yields a Postgres write connection from pool.

        Only used when ``self._is_postgres`` is True.
        """
        assert self._is_postgres
        with self._adapter.writer() as conn:  # type: ignore[attr-defined]
            yield conn

    # ------------------------------------------------------------------
    # Internal: BEGIN / COMMIT / ROLLBACK helpers
    # ------------------------------------------------------------------

    def _begin(self, conn=None) -> None:
        """Issue BEGIN on the appropriate connection."""
        if self._is_postgres:
            # psycopg3 manages transactions automatically; explicit BEGIN is
            # fine but not required — connections start in a transaction by
            # default in psycopg3 (autocommit=False).
            pass
        else:
            self._conn.execute("BEGIN")

    def _commit(self, conn=None) -> None:
        if self._is_postgres:
            conn.commit()
        else:
            self._conn.commit()

    def _rollback(self, conn=None) -> None:
        if self._is_postgres:
            try:
                conn.rollback()
            except Exception:
                pass
        else:
            try:
                self._conn.rollback()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("SkillStore is closed")

    @_db_retry()
    def _init_db(self) -> None:
        """Create tables if they don't exist (idempotent via IF NOT EXISTS)."""
        if self._is_postgres:
            self._adapter.init_db(None)
        else:
            with self._mu:
                self._adapter.init_db(self._conn)

    def close(self) -> None:
        """Close the persistent connection / pool.

        SQLite: performs a WAL checkpoint before closing so all committed
        data is flushed from the WAL file into the main ``.db`` file.
        Postgres: closes the connection pool.
        """
        if self._closed:
            return
        self._closed = True
        self._adapter.close(self._conn)
        logger.debug("SkillStore closed")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        self.close()

    # ------------------------------------------------------------------
    # Write API (async, offloaded via asyncio.to_thread)
    # ------------------------------------------------------------------

    async def save_record(self, record: SkillRecord) -> None:
        """Upsert a single :class:`SkillRecord`."""
        await asyncio.to_thread(self._save_record_sync, record)

    async def save_records(self, records: List[SkillRecord]) -> None:
        """Batch upsert in a single transaction."""
        await asyncio.to_thread(self._save_records_sync, records)

    async def sync_from_registry(
        self,
        discovered_skills: List[Any],
    ) -> int:
        """Ensure every discovered skill has an initial DB record.

        For each skill in *discovered_skills* (``SkillMeta`` objects
        from :meth:`SkillRegistry.discover`), if no record with the
        same ``skill_id`` already exists, a new :class:`SkillRecord` is
        created (``origin=IMPORTED``, ``generation=0``).

        Existing records (including evolved ones) are left untouched.

        Args:
            discovered_skills: List of ``SkillMeta`` objects.
        """
        return await asyncio.to_thread(
            self._sync_from_registry_sync, discovered_skills,
        )

    @_db_retry()
    def _sync_from_registry_sync(
        self, discovered_skills: List[Any],
    ) -> int:
        self._ensure_open()
        created = 0
        refreshed = 0

        if self._is_postgres:
            return self._sync_from_registry_pg(discovered_skills)

        # --- SQLite path (original logic) ---
        with self._mu:
            self._conn.execute("BEGIN")
            try:
                # Fetch all existing records keyed by skill_id
                cur = self._conn.execute(
                    "SELECT skill_id, name, description, "
                    "lineage_content_snapshot "
                    "FROM skill_records"
                )
                rows = [dict(r) for r in cur.fetchall()]
                existing: Dict[str, Any] = {r["skill_id"]: r for r in rows}

                # Also fetch all paths with an active record.
                path_rows = self._conn.execute(
                    "SELECT path FROM skill_records WHERE is_active=1"
                ).fetchall()
                existing_active_paths: set = {r[0] for r in path_rows}

                for meta in discovered_skills:
                    path_str = str(meta.path)
                    skill_dir = meta.path.parent

                    if meta.skill_id in existing:
                        row = existing[meta.skill_id]
                        updates: List[str] = []
                        params: list = []

                        if row["name"] != meta.name:
                            updates.append("name=?")
                            params.append(meta.name)
                        if row["description"] != meta.description:
                            updates.append("description=?")
                            params.append(meta.description)

                        raw_snap = row["lineage_content_snapshot"] or ""
                        if raw_snap in ("", "{}"):
                            try:
                                snap = collect_skill_snapshot(skill_dir)
                                if snap:
                                    updates.append("lineage_content_snapshot=?")
                                    params.append(json.dumps(snap, ensure_ascii=False))
                                    diff = "\n".join(
                                        compute_unified_diff("", text, filename=name)
                                        for name, text in sorted(snap.items())
                                        if compute_unified_diff("", text, filename=name)
                                    )
                                    if diff:
                                        updates.append("lineage_content_diff=?")
                                        params.append(diff)
                            except Exception as e:
                                logger.warning(
                                    f"sync_from_registry: snapshot backfill failed "
                                    f"for {meta.skill_id}: {e}"
                                )

                        if updates:
                            params.append(meta.skill_id)
                            self._conn.execute(
                                f"UPDATE skill_records SET {', '.join(updates)} "
                                f"WHERE skill_id=?",
                                params,
                            )
                            refreshed += 1
                        continue

                    # Path already covered by an evolved record
                    if path_str in existing_active_paths:
                        continue

                    # Snapshot the directory so this version can be restored later
                    snapshot: Dict[str, str] = {}
                    content_diff = ""
                    try:
                        snapshot = collect_skill_snapshot(skill_dir)
                        content_diff = "\n".join(
                            compute_unified_diff("", text, filename=name)
                            for name, text in sorted(snapshot.items())
                            if compute_unified_diff("", text, filename=name)
                        )
                    except Exception as e:
                        logger.warning(
                            f"sync_from_registry: failed to snapshot {skill_dir}: {e}"
                        )

                    record = SkillRecord(
                        skill_id=meta.skill_id,
                        name=meta.name,
                        description=meta.description,
                        path=path_str,
                        is_active=True,
                        lineage=SkillLineage(
                            origin=SkillOrigin.IMPORTED,
                            generation=0,
                            content_snapshot=snapshot,
                            content_diff=content_diff,
                        ),
                    )
                    self._upsert(record, conn=self._conn)
                    created += 1
                    logger.debug(
                        f"sync_from_registry: created {meta.name} [{meta.skill_id}]"
                    )

                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

        if created or refreshed:
            logger.info(
                f"sync_from_registry: {created} new record(s) created, "
                f"{refreshed} refreshed, "
                f"{len(discovered_skills) - created - refreshed} unchanged"
            )
        return created

    def _sync_from_registry_pg(self, discovered_skills: List[Any]) -> int:
        """Postgres-specific implementation of sync_from_registry."""
        created = 0
        refreshed = 0
        adp = self._adapter

        with self._mu:
            with adp.writer() as conn:  # type: ignore[attr-defined]
                try:
                    cur = conn.execute(
                        adp.sql(
                            "SELECT skill_id, name, description, "
                            "lineage_content_snapshot FROM skill_records"
                        )
                    )
                    rows = adp.fetchall(cur)
                    existing: Dict[str, Any] = {r["skill_id"]: r for r in rows}

                    cur2 = conn.execute(
                        adp.sql(
                            "SELECT path FROM skill_records WHERE is_active=1"
                        )
                    )
                    path_rows = adp.fetchall(cur2)
                    existing_active_paths: set = {r["path"] for r in path_rows}

                    for meta in discovered_skills:
                        path_str = str(meta.path)
                        skill_dir = meta.path.parent

                        if meta.skill_id in existing:
                            row = existing[meta.skill_id]
                            updates: List[str] = []
                            params: list = []

                            if row["name"] != meta.name:
                                updates.append("name=%s")
                                params.append(meta.name)
                            if row["description"] != meta.description:
                                updates.append("description=%s")
                                params.append(meta.description)

                            raw_snap = row["lineage_content_snapshot"] or ""
                            if raw_snap in ("", "{}"):
                                try:
                                    snap = collect_skill_snapshot(skill_dir)
                                    if snap:
                                        updates.append("lineage_content_snapshot=%s")
                                        params.append(json.dumps(snap, ensure_ascii=False))
                                        diff = "\n".join(
                                            compute_unified_diff("", text, filename=name)
                                            for name, text in sorted(snap.items())
                                            if compute_unified_diff("", text, filename=name)
                                        )
                                        if diff:
                                            updates.append("lineage_content_diff=%s")
                                            params.append(diff)
                                except Exception as e:
                                    logger.warning(
                                        f"sync_from_registry: snapshot backfill failed "
                                        f"for {meta.skill_id}: {e}"
                                    )

                            if updates:
                                params.append(meta.skill_id)
                                conn.execute(
                                    f"UPDATE skill_records SET {', '.join(updates)} "
                                    f"WHERE skill_id=%s",
                                    params,
                                )
                                refreshed += 1
                            continue

                        if path_str in existing_active_paths:
                            continue

                        snapshot: Dict[str, str] = {}
                        content_diff = ""
                        try:
                            snapshot = collect_skill_snapshot(skill_dir)
                            content_diff = "\n".join(
                                compute_unified_diff("", text, filename=name)
                                for name, text in sorted(snapshot.items())
                                if compute_unified_diff("", text, filename=name)
                            )
                        except Exception as e:
                            logger.warning(
                                f"sync_from_registry: failed to snapshot {skill_dir}: {e}"
                            )

                        record = SkillRecord(
                            skill_id=meta.skill_id,
                            name=meta.name,
                            description=meta.description,
                            path=path_str,
                            is_active=True,
                            lineage=SkillLineage(
                                origin=SkillOrigin.IMPORTED,
                                generation=0,
                                content_snapshot=snapshot,
                                content_diff=content_diff,
                            ),
                        )
                        self._upsert(record, conn=conn)
                        created += 1
                        logger.debug(
                            f"sync_from_registry: created {meta.name} [{meta.skill_id}]"
                        )

                    conn.commit()
                except Exception:
                    conn.rollback()
                    raise

        if created or refreshed:
            logger.info(
                f"sync_from_registry: {created} new record(s) created, "
                f"{refreshed} refreshed, "
                f"{len(discovered_skills) - created - refreshed} unchanged"
            )
        return created

    async def record_analysis(self, analysis: ExecutionAnalysis) -> None:
        """Atomic observation: insert analysis + judgments + increment counters.

        1. INSERT a row in ``execution_analyses`` (one per task).
        2. INSERT rows in ``skill_judgments`` for each skill assessed.
        3. For each judgment, atomically increment the matching
           ``skill_records`` counters:
           - total_selections  += 1         (always)
           - total_applied     += 1         (if skill_applied)
           - total_completions += 1         (if applied and completed)
           - total_fallbacks   += 1         (if not applied and not completed)
           - last_updated = now
        """
        await asyncio.to_thread(self._record_analysis_sync, analysis)

    async def evolve_skill(
        self,
        new_record: SkillRecord,
        parent_skill_ids: List[str],
    ) -> None:
        """Atomic evolution: insert new version + deactivate old version.

        **FIXED** — Same-name skill fix:
          - ``new_record.name`` is the same as parent
          - ``new_record.path`` is the same as parent
          - parent is set to ``is_active=False``
          - ``new_record.is_active=True``

        **DERIVED** — New skill derived:
          - ``new_record.name`` is a new name
          - parent is kept ``is_active=True`` (it is still the latest version of its line)
          - ``new_record.is_active=True``

        In the same SQL transaction, guaranteed by ``self._mu``.

        Args:
        new_record : SkillRecord
            New version record, ``lineage.parent_skill_ids`` must be non-empty.
        parent_skill_ids : list[str]
            Parent skill_id list (FIXED exactly 1, DERIVED ≥ 1).
            For FIXED, parent is automatically deactivated.
        """
        await asyncio.to_thread(
            self._evolve_skill_sync, new_record, parent_skill_ids
        )

    async def deactivate_record(self, skill_id: str) -> bool:
        """Set a specific record's ``is_active`` to False."""
        return await asyncio.to_thread(self._deactivate_record_sync, skill_id)

    async def reactivate_record(self, skill_id: str) -> bool:
        """Set a specific record's ``is_active`` to True (revert / rollback)."""
        return await asyncio.to_thread(self._reactivate_record_sync, skill_id)

    async def delete_record(self, skill_id: str) -> bool:
        """Delete a skill and all related data (CASCADE)."""
        return await asyncio.to_thread(self._delete_record_sync, skill_id)

    # ------------------------------------------------------------------
    # Sync write implementations (thread-safe via self._mu)
    # ------------------------------------------------------------------

    @_db_retry()
    def _save_record_sync(self, record: SkillRecord) -> None:
        self._ensure_open()
        if self._is_postgres:
            with self._mu:
                with self._adapter.writer() as conn:  # type: ignore[attr-defined]
                    try:
                        self._upsert(record, conn=conn)
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        raise
        else:
            with self._mu:
                self._conn.execute("BEGIN")
                try:
                    self._upsert(record, conn=self._conn)
                    self._conn.commit()
                except Exception:
                    self._conn.rollback()
                    raise

    @_db_retry()
    def _save_records_sync(self, records: List[SkillRecord]) -> None:
        self._ensure_open()
        if self._is_postgres:
            with self._mu:
                with self._adapter.writer() as conn:  # type: ignore[attr-defined]
                    try:
                        for r in records:
                            self._upsert(r, conn=conn)
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        raise
        else:
            with self._mu:
                self._conn.execute("BEGIN")
                try:
                    for r in records:
                        self._upsert(r, conn=self._conn)
                    self._conn.commit()
                except Exception:
                    self._conn.rollback()
                    raise

    @_db_retry()
    def _record_analysis_sync(self, analysis: ExecutionAnalysis) -> None:
        """Persist an analysis and update skill quality counters.

        ``SkillJudgment.skill_id`` is the **true skill_id** (e.g.
        ``weather__imp_a1b2c3d4``), the same identifier used as the DB
        primary key.  The analysis LLM receives skill_ids in its prompt
        and outputs them verbatim.

        We update counters via ``WHERE skill_id = ?`` — exact match, no
        ambiguity.
        """
        self._ensure_open()
        if self._is_postgres:
            with self._mu:
                with self._adapter.writer() as conn:  # type: ignore[attr-defined]
                    try:
                        analysis_id = self._insert_analysis(analysis, conn=conn)
                        now_iso = datetime.now().isoformat()
                        for j in analysis.skill_judgments:
                            applied = 1 if j.skill_applied else 0
                            completed = (
                                1
                                if (j.skill_applied and analysis.task_completed)
                                else 0
                            )
                            fallback = (
                                1
                                if (not j.skill_applied and not analysis.task_completed)
                                else 0
                            )
                            conn.execute(
                                self._adapter.sql(
                                    """
                                    UPDATE skill_records SET
                                        total_selections  = total_selections + 1,
                                        total_applied     = total_applied + ?,
                                        total_completions = total_completions + ?,
                                        total_fallbacks   = total_fallbacks + ?,
                                        last_updated      = ?
                                    WHERE skill_id = ?
                                    """
                                ),
                                (applied, completed, fallback, now_iso, j.skill_id),
                            )
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        raise
        else:
            with self._mu:
                self._conn.execute("BEGIN")
                try:
                    analysis_id = self._insert_analysis(analysis, conn=self._conn)

                    now_iso = datetime.now().isoformat()
                    for j in analysis.skill_judgments:
                        applied = 1 if j.skill_applied else 0
                        completed = (
                            1
                            if (j.skill_applied and analysis.task_completed)
                            else 0
                        )
                        fallback = (
                            1
                            if (not j.skill_applied and not analysis.task_completed)
                            else 0
                        )
                        self._conn.execute(
                            """
                            UPDATE skill_records SET
                                total_selections  = total_selections + 1,
                                total_applied     = total_applied + ?,
                                total_completions = total_completions + ?,
                                total_fallbacks   = total_fallbacks + ?,
                                last_updated      = ?
                            WHERE skill_id = ?
                            """,
                            (applied, completed, fallback, now_iso, j.skill_id),
                        )

                    self._conn.commit()
                except Exception:
                    self._conn.rollback()
                    raise

    @_db_retry()
    def _evolve_skill_sync(
        self,
        new_record: SkillRecord,
        parent_skill_ids: List[str],
    ) -> None:
        """Atomic: insert new version + deactivate parents (for FIXED)."""
        self._ensure_open()
        if self._is_postgres:
            with self._mu:
                with self._adapter.writer() as conn:  # type: ignore[attr-defined]
                    try:
                        if new_record.lineage.origin == SkillOrigin.FIXED:
                            for pid in parent_skill_ids:
                                conn.execute(
                                    self._adapter.sql(
                                        "UPDATE skill_records SET is_active=0, "
                                        "last_updated=? WHERE skill_id=?"
                                    ),
                                    (datetime.now().isoformat(), pid),
                                )
                        new_record.lineage.parent_skill_ids = list(parent_skill_ids)
                        new_record.is_active = True
                        self._upsert(new_record, conn=conn)
                        conn.commit()
                        origin = new_record.lineage.origin.value
                        logger.info(
                            f"evolve_skill ({origin}): "
                            f"{new_record.name}@gen{new_record.lineage.generation} "
                            f"[{new_record.skill_id}] ← parents={parent_skill_ids}"
                        )
                    except Exception:
                        conn.rollback()
                        raise
        else:
            with self._mu:
                self._conn.execute("BEGIN")
                try:
                    # For FIXED: deactivate same-name parents
                    if new_record.lineage.origin == SkillOrigin.FIXED:
                        for pid in parent_skill_ids:
                            self._conn.execute(
                                "UPDATE skill_records SET is_active=0, "
                                "last_updated=? WHERE skill_id=?",
                                (datetime.now().isoformat(), pid),
                            )

                    # Ensure new record has parent refs set
                    new_record.lineage.parent_skill_ids = list(parent_skill_ids)
                    new_record.is_active = True

                    self._upsert(new_record, conn=self._conn)
                    self._conn.commit()

                    origin = new_record.lineage.origin.value
                    logger.info(
                        f"evolve_skill ({origin}): "
                        f"{new_record.name}@gen{new_record.lineage.generation} "
                        f"[{new_record.skill_id}] ← parents={parent_skill_ids}"
                    )
                except Exception:
                    self._conn.rollback()
                    raise

    @_db_retry()
    def _deactivate_record_sync(self, skill_id: str) -> bool:
        self._ensure_open()
        if self._is_postgres:
            with self._mu:
                with self._adapter.writer() as conn:  # type: ignore[attr-defined]
                    cur = conn.execute(
                        self._adapter.sql(
                            "UPDATE skill_records SET is_active=0, last_updated=? "
                            "WHERE skill_id=?"
                        ),
                        (datetime.now().isoformat(), skill_id),
                    )
                    conn.commit()
                    return cur.rowcount > 0
        else:
            with self._mu:
                cur = self._conn.execute(
                    "UPDATE skill_records SET is_active=0, last_updated=? "
                    "WHERE skill_id=?",
                    (datetime.now().isoformat(), skill_id),
                )
                self._conn.commit()
                return cur.rowcount > 0

    @_db_retry()
    def _reactivate_record_sync(self, skill_id: str) -> bool:
        self._ensure_open()
        if self._is_postgres:
            with self._mu:
                with self._adapter.writer() as conn:  # type: ignore[attr-defined]
                    cur = conn.execute(
                        self._adapter.sql(
                            "UPDATE skill_records SET is_active=1, last_updated=? "
                            "WHERE skill_id=?"
                        ),
                        (datetime.now().isoformat(), skill_id),
                    )
                    conn.commit()
                    return cur.rowcount > 0
        else:
            with self._mu:
                cur = self._conn.execute(
                    "UPDATE skill_records SET is_active=1, last_updated=? "
                    "WHERE skill_id=?",
                    (datetime.now().isoformat(), skill_id),
                )
                self._conn.commit()
                return cur.rowcount > 0

    @_db_retry()
    def _delete_record_sync(self, skill_id: str) -> bool:
        self._ensure_open()
        if self._is_postgres:
            with self._mu:
                with self._adapter.writer() as conn:  # type: ignore[attr-defined]
                    cur = conn.execute(
                        self._adapter.sql(
                            "DELETE FROM skill_records WHERE skill_id=?"
                        ),
                        (skill_id,),
                    )
                    conn.commit()
                    return cur.rowcount > 0
        else:
            with self._mu:
                # ON DELETE CASCADE automatically cleans up lineage_parents / deps / tags
                # skill_judgments are NOT cascade-deleted (no FK to skill_records)
                cur = self._conn.execute(
                    "DELETE FROM skill_records WHERE skill_id=?", (skill_id,)
                )
                self._conn.commit()
                return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Read API (sync, each call opens its own read-only conn)
    # ------------------------------------------------------------------

    @_db_retry()
    def load_record(self, skill_id: str) -> Optional[SkillRecord]:
        """Load a single :class:`SkillRecord` by id."""
        with self._reader() as conn:
            cur = conn.execute(
                self._adapter.sql(
                    "SELECT * FROM skill_records WHERE skill_id=?"
                ),
                (skill_id,),
            )
            row = self._adapter.fetchone(cur)
            return self._to_record(conn, row) if row else None

    @_db_retry()
    def load_all(
        self, *, active_only: bool = False
    ) -> Dict[str, SkillRecord]:
        """Load skill records, keyed by ``skill_id``.

        Args:
            active_only: If True, only return records with ``is_active=True``.
        """
        with self._reader() as conn:
            if active_only:
                cur = conn.execute(
                    self._adapter.sql(
                        "SELECT * FROM skill_records WHERE is_active=1"
                    )
                )
            else:
                cur = conn.execute(
                    self._adapter.sql("SELECT * FROM skill_records")
                )
            rows = self._adapter.fetchall(cur)
            result: Dict[str, SkillRecord] = {}
            for row in rows:
                rec = self._to_record(conn, row)
                result[rec.skill_id] = rec
            logger.info(f"Loaded {len(result)} skill records (active_only={active_only})")
            return result

    @_db_retry()
    def load_active(self) -> Dict[str, SkillRecord]:
        """Load only active skill records, keyed by ``skill_id``.

        Convenience wrapper for ``load_all(active_only=True)``.
        """
        return self.load_all(active_only=True)

    @_db_retry()
    def load_record_by_path(self, skill_dir: str) -> Optional[SkillRecord]:
        """Load the most recent active SkillRecord whose ``path`` is inside *skill_dir*.

        Used by ``upload_skill`` to retrieve pre-computed upload metadata
        (origin, parents, change_summary, etc.) from the DB when
        ``.upload_meta.json`` is missing.

        The match uses ``path LIKE '{skill_dir}%'`` so both
        ``/a/b/SKILL.md`` and ``/a/b/scenarios/x.md`` match ``/a/b``.
        Returns the newest active record (by ``last_updated DESC``).
        """
        normalized = skill_dir.rstrip("/")
        with self._reader() as conn:
            cur = conn.execute(
                self._adapter.sql(
                    "SELECT * FROM skill_records "
                    "WHERE path LIKE ? AND is_active=1 "
                    "ORDER BY last_updated DESC LIMIT 1"
                ),
                (f"{normalized}%",),
            )
            row = self._adapter.fetchone(cur)
            return self._to_record(conn, row) if row else None

    @_db_retry()
    def get_versions(self, name: str) -> List[SkillRecord]:
        """Load all versions of a named skill (active + inactive), sorted by generation."""
        with self._reader() as conn:
            cur = conn.execute(
                self._adapter.sql(
                    "SELECT * FROM skill_records WHERE name=? "
                    "ORDER BY lineage_generation ASC"
                ),
                (name,),
            )
            rows = self._adapter.fetchall(cur)
            return [self._to_record(conn, r) for r in rows]

    @_db_retry()
    def load_by_category(
        self, category: SkillCategory, *, active_only: bool = True
    ) -> List[SkillRecord]:
        """Load skill records filtered by category.

        Args:
            active_only: If True (default), only return active records.
        """
        with self._reader() as conn:
            if active_only:
                cur = conn.execute(
                    self._adapter.sql(
                        "SELECT * FROM skill_records "
                        "WHERE category=? AND is_active=1"
                    ),
                    (category.value,),
                )
            else:
                cur = conn.execute(
                    self._adapter.sql(
                        "SELECT * FROM skill_records WHERE category=?"
                    ),
                    (category.value,),
                )
            rows = self._adapter.fetchall(cur)
            return [self._to_record(conn, r) for r in rows]

    @_db_retry()
    def load_analyses(
        self,
        skill_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ExecutionAnalysis]:
        """Load recent analyses.

        Args:
            skill_id: True ``skill_id`` (e.g. ``weather__imp_a1b2c3d4``).
                ``skill_judgments.skill_id`` now stores the true skill_id,
                so filtering uses exact match.
                If None, return pure-execution analyses (no judgments).
        """
        with self._reader() as conn:
            if skill_id is not None:
                cur = conn.execute(
                    self._adapter.sql(
                        "SELECT ea.* FROM execution_analyses ea "
                        "JOIN skill_judgments sj ON ea.id = sj.analysis_id "
                        "WHERE sj.skill_id = ? "
                        "ORDER BY ea.timestamp DESC LIMIT ?"
                    ),
                    (skill_id, limit),
                )
            else:
                cur = conn.execute(
                    self._adapter.sql(
                        "SELECT ea.* FROM execution_analyses ea "
                        "LEFT JOIN skill_judgments sj ON ea.id = sj.analysis_id "
                        "WHERE sj.id IS NULL "
                        "ORDER BY ea.timestamp DESC LIMIT ?"
                    ),
                    (limit,),
                )
            rows = self._adapter.fetchall(cur)
            return [self._to_analysis(conn, r) for r in reversed(rows)]

    @_db_retry()
    def load_analyses_for_task(
        self, task_id: str
    ) -> Optional[ExecutionAnalysis]:
        """Load the analysis for a specific task, or None."""
        with self._reader() as conn:
            cur = conn.execute(
                self._adapter.sql(
                    "SELECT * FROM execution_analyses WHERE task_id=?"
                ),
                (task_id,),
            )
            row = self._adapter.fetchone(cur)
            return self._to_analysis(conn, row) if row else None

    @_db_retry()
    def load_all_analyses(self, limit: int = 200) -> List[ExecutionAnalysis]:
        """Load recent analyses across all tasks."""
        with self._reader() as conn:
            cur = conn.execute(
                self._adapter.sql(
                    "SELECT * FROM execution_analyses "
                    "ORDER BY timestamp DESC LIMIT ?"
                ),
                (limit,),
            )
            rows = self._adapter.fetchall(cur)
            return [self._to_analysis(conn, r) for r in reversed(rows)]

    @_db_retry()
    def load_evolution_candidates(
        self, limit: int = 50, *, include_processed: bool = False,
    ) -> List[ExecutionAnalysis]:
        """Load analyses marked as evolution candidates.

        Args:
            limit: Max number of records.
            include_processed: If False (default), only return candidates
                whose suggestions have NOT been processed yet.
        """
        with self._reader() as conn:
            if include_processed:
                where = "WHERE candidate_for_evolution=1"
            else:
                where = (
                    "WHERE candidate_for_evolution=1 "
                    "AND evolution_processed_at IS NULL"
                )
            cur = conn.execute(
                self._adapter.sql(
                    f"SELECT * FROM execution_analyses {where} "
                    "ORDER BY timestamp DESC LIMIT ?"
                ),
                (limit,),
            )
            rows = self._adapter.fetchall(cur)
            return [self._to_analysis(conn, r) for r in reversed(rows)]

    @_db_retry()
    def mark_evolution_processed(self, task_id: str) -> None:
        """Mark an analysis's evolution suggestions as processed."""
        if self._is_postgres:
            with self._mu:
                with self._adapter.writer() as conn:  # type: ignore[attr-defined]
                    conn.execute(
                        self._adapter.sql(
                            "UPDATE execution_analyses "
                            "SET evolution_processed_at=? WHERE task_id=?"
                        ),
                        (datetime.now().isoformat(), task_id),
                    )
                    conn.commit()
        else:
            with self._mu:
                self._conn.execute(
                    "UPDATE execution_analyses "
                    "SET evolution_processed_at=? WHERE task_id=?",
                    (datetime.now().isoformat(), task_id),
                )
                self._conn.commit()

    @_db_retry()
    def find_skills_by_tool(self, tool_key: str) -> List[str]:
        """
        Only returns active records — deactivated (superseded) versions
        are excluded so that Trigger 2 never re-processes old versions.
        """
        with self._reader() as conn:
            cur = conn.execute(
                self._adapter.sql(
                    "SELECT sd.skill_id "
                    "FROM skill_tool_deps sd "
                    "JOIN skill_records sr ON sd.skill_id = sr.skill_id "
                    "WHERE sd.tool_key=? AND sr.is_active=1"
                ),
                (tool_key,),
            )
            rows = self._adapter.fetchall(cur)
            return [r["skill_id"] for r in rows]

    @_db_retry()
    def find_children(self, parent_skill_id: str) -> List[str]:
        """Find skill_ids derived from the given parent."""
        with self._reader() as conn:
            cur = conn.execute(
                self._adapter.sql(
                    "SELECT skill_id FROM skill_lineage_parents "
                    "WHERE parent_skill_id=?"
                ),
                (parent_skill_id,),
            )
            rows = self._adapter.fetchall(cur)
            return [r["skill_id"] for r in rows]

    @_db_retry()
    def count(self, *, active_only: bool = False) -> int:
        """Total number of skill records."""
        with self._reader() as conn:
            if active_only:
                cur = conn.execute(
                    self._adapter.sql(
                        "SELECT COUNT(*) AS cnt FROM skill_records WHERE is_active=1"
                    )
                )
            else:
                cur = conn.execute(
                    self._adapter.sql(
                        "SELECT COUNT(*) AS cnt FROM skill_records"
                    )
                )
            row = self._adapter.fetchone(cur)
            return row["cnt"] if row else 0

    # Analytics / Summary
    @_db_retry()
    def get_summary(self, *, active_only: bool = True) -> List[Dict[str, Any]]:
        """Lightweight summary of skills (no analyses/deps loaded).

        Default filters to active skills only.
        """
        with self._reader() as conn:
            where = "WHERE is_active=1 " if active_only else ""
            cur = conn.execute(
                self._adapter.sql(
                    f"""
                    SELECT skill_id, name, description, category, is_active,
                           visibility, creator_id,
                           lineage_origin, lineage_generation,
                           total_selections, total_applied,
                           total_completions, total_fallbacks,
                           first_seen, last_updated
                    FROM skill_records
                    {where}
                    ORDER BY last_updated DESC
                    """
                )
            )
            rows = self._adapter.fetchall(cur)
            return [dict(r) for r in rows]

    @_db_retry()
    def get_stats(self, *, active_only: bool = True) -> Dict[str, Any]:
        """Aggregate statistics across skills."""
        with self._reader() as conn:
            where = " WHERE is_active=1" if active_only else ""
            cur = conn.execute(
                self._adapter.sql(
                    f"SELECT COUNT(*) AS cnt FROM skill_records{where}"
                )
            )
            total = (self._adapter.fetchone(cur) or {}).get("cnt", 0)

            cur2 = conn.execute(
                self._adapter.sql(
                    f"SELECT category, COUNT(*) AS cnt "
                    f"FROM skill_records{where} GROUP BY category"
                )
            )
            by_category = {
                r["category"]: r["cnt"]
                for r in self._adapter.fetchall(cur2)
            }

            cur3 = conn.execute(
                self._adapter.sql(
                    f"SELECT lineage_origin, COUNT(*) AS cnt "
                    f"FROM skill_records{where} GROUP BY lineage_origin"
                )
            )
            by_origin = {
                r["lineage_origin"]: r["cnt"]
                for r in self._adapter.fetchall(cur3)
            }

            cur4 = conn.execute(
                self._adapter.sql(
                    "SELECT COUNT(*) AS cnt FROM execution_analyses"
                )
            )
            n_analyses = (self._adapter.fetchone(cur4) or {}).get("cnt", 0)

            cur5 = conn.execute(
                self._adapter.sql(
                    "SELECT COUNT(*) AS cnt FROM execution_analyses "
                    "WHERE candidate_for_evolution=1"
                )
            )
            n_candidates = (self._adapter.fetchone(cur5) or {}).get("cnt", 0)

            cur6 = conn.execute(
                self._adapter.sql(
                    "SELECT COUNT(*) AS cnt FROM execution_analyses "
                    "WHERE candidate_for_evolution=1 "
                    "AND evolution_processed_at IS NULL"
                )
            )
            n_unprocessed_candidates = (self._adapter.fetchone(cur6) or {}).get("cnt", 0)

            cur7 = conn.execute(
                self._adapter.sql(
                    f"""
                    SELECT SUM(total_selections)  AS sel,
                           SUM(total_applied)      AS app,
                           SUM(total_completions)  AS comp,
                           SUM(total_fallbacks)    AS fb
                    FROM skill_records{where}
                    """
                )
            )
            agg = self._adapter.fetchone(cur7) or {}

            # Also report total (including inactive) for context
            cur8 = conn.execute(
                self._adapter.sql(
                    "SELECT COUNT(*) AS cnt FROM skill_records"
                )
            )
            total_all = (self._adapter.fetchone(cur8) or {}).get("cnt", 0)

            return {
                "total_skills": total,
                "total_skills_all": total_all,
                "by_category": by_category,
                "by_origin": by_origin,
                "total_analyses": n_analyses,
                "evolution_candidates": n_candidates,
                "unprocessed_evolution_candidates": n_unprocessed_candidates,
                "total_selections": agg.get("sel") or 0,
                "total_applied": agg.get("app") or 0,
                "total_completions": agg.get("comp") or 0,
                "total_fallbacks": agg.get("fb") or 0,
            }

    @_db_retry()
    def get_task_skill_summary(self, task_id: str) -> Dict[str, Any]:
        """Per-task summary: task-level fields + per-skill judgments.

        Useful for understanding how multiple skills contributed to a
        single task execution.

        Returns:
            dict: ``{"task_id", "task_completed", "execution_note",
                "tool_issues", "judgments": [{skill_id, skill_applied, note}],
                ...}`` or empty dict if the task has no analysis.
        """
        with self._reader() as conn:
            cur = conn.execute(
                self._adapter.sql(
                    "SELECT * FROM execution_analyses WHERE task_id=?"
                ),
                (task_id,),
            )
            row = self._adapter.fetchone(cur)
            if not row:
                return {}

            cur2 = conn.execute(
                self._adapter.sql(
                    "SELECT skill_id, skill_applied, note "
                    "FROM skill_judgments WHERE analysis_id=?"
                ),
                (row["id"],),
            )
            judgment_rows = self._adapter.fetchall(cur2)

            try:
                evo_suggestions = json.loads(row["evolution_suggestions"] or "[]")
            except json.JSONDecodeError:
                evo_suggestions = []

            return {
                "task_id": row["task_id"],
                "timestamp": row["timestamp"],
                "task_completed": bool(row["task_completed"]),
                "execution_note": row["execution_note"],
                "tool_issues": json.loads(row["tool_issues"]),
                "candidate_for_evolution": bool(row["candidate_for_evolution"]),
                "evolution_suggestions": evo_suggestions,
                "analyzed_by": row["analyzed_by"],
                "judgments": [
                    {
                        "skill_id": jr["skill_id"],
                        "skill_applied": bool(jr["skill_applied"]),
                        "note": jr["note"],
                    }
                    for jr in judgment_rows
                ],
            }

    @_db_retry()
    def get_top_skills(
        self,
        n: int = 10,
        metric: str = "effective_rate",
        min_selections: int = 1,
        *,
        active_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Top-N skills ranked by the chosen metric.

        Metrics:
            ``effective_rate``  — completions / selections
            ``applied_rate``    — applied / selections
            ``completion_rate`` — completions / applied
            ``total_selections``— raw count
        """
        rate_exprs = {
            "effective_rate": (
                "CAST(total_completions AS REAL) / total_selections"
            ),
            "applied_rate": (
                "CAST(total_applied AS REAL) / total_selections"
            ),
            "completion_rate": (
                "CASE WHEN total_applied > 0 "
                "THEN CAST(total_completions AS REAL) / total_applied "
                "ELSE 0.0 END"
            ),
            "total_selections": "total_selections",
        }
        expr = rate_exprs.get(metric, rate_exprs["effective_rate"])
        active_clause = " AND is_active=1" if active_only else ""

        with self._reader() as conn:
            cur = conn.execute(
                self._adapter.sql(
                    f"SELECT *, ({expr}) AS _rank "
                    f"FROM skill_records "
                    f"WHERE total_selections >= ?{active_clause} "
                    f"ORDER BY _rank DESC LIMIT ?"
                ),
                (min_selections, n),
            )
            rows = self._adapter.fetchall(cur)
            results = []
            for r in rows:
                d = dict(r)
                d.pop("_rank", None)
                results.append(d)
            return results

    @_db_retry()
    def get_count_and_timestamp(
        self, *, active_only: bool = True
    ) -> Dict[str, Any]:
        """Skill count + newest ``last_updated`` for cheap change detection."""
        with self._reader() as conn:
            where = " WHERE is_active=1" if active_only else ""
            cur = conn.execute(
                self._adapter.sql(
                    f"SELECT COUNT(*) AS cnt, MAX(last_updated) AS max_ts "
                    f"FROM skill_records{where}"
                )
            )
            row = self._adapter.fetchone(cur)
            return {
                "count": row["cnt"] if row else 0,
                "max_last_updated": row["max_ts"] if row else None,
            }

    # Lineage / Ancestry
    @_db_retry()
    def get_ancestry(
        self, skill_id: str, max_depth: int = 10
    ) -> List[SkillRecord]:
        """Walk up the lineage tree; returns ancestors oldest-first."""
        with self._reader() as conn:
            visited: set = set()
            ancestors: List[SkillRecord] = []
            frontier = [skill_id]

            for _ in range(max_depth):
                next_frontier: List[str] = []
                for sid in frontier:
                    cur = conn.execute(
                        self._adapter.sql(
                            "SELECT parent_skill_id "
                            "FROM skill_lineage_parents WHERE skill_id=?"
                        ),
                        (sid,),
                    )
                    for pr in self._adapter.fetchall(cur):
                        pid = pr["parent_skill_id"]
                        if pid in visited:
                            continue
                        visited.add(pid)
                        cur2 = conn.execute(
                            self._adapter.sql(
                                "SELECT * FROM skill_records WHERE skill_id=?"
                            ),
                            (pid,),
                        )
                        row = self._adapter.fetchone(cur2)
                        if row:
                            ancestors.append(self._to_record(conn, row))
                            next_frontier.append(pid)
                frontier = next_frontier
                if not frontier:
                    break

            ancestors.sort(key=lambda r: r.lineage.generation)
            return ancestors

    @_db_retry()
    def get_lineage_tree(
        self, skill_id: str, max_depth: int = 5
    ) -> Dict[str, Any]:
        """Build a JSON-friendly tree rooted at *skill_id* (downward)."""
        with self._reader() as conn:
            return self._subtree(conn, skill_id, max_depth, set())

    def _subtree(
        self,
        conn: Any,
        sid: str,
        depth: int,
        visited: set,
    ) -> Dict[str, Any]:
        visited.add(sid)
        cur = conn.execute(
            self._adapter.sql(
                "SELECT skill_id, name, lineage_generation, lineage_origin, is_active "
                "FROM skill_records WHERE skill_id=?"
            ),
            (sid,),
        )
        row = self._adapter.fetchone(cur)
        node: Dict[str, Any] = {
            "skill_id": sid,
            "name": row["name"] if row else "?",
            "generation": row["lineage_generation"] if row else -1,
            "origin": row["lineage_origin"] if row else "unknown",
            "is_active": bool(row["is_active"]) if row else False,
            "children": [],
        }
        if depth <= 0:
            return node
        cur2 = conn.execute(
            self._adapter.sql(
                "SELECT skill_id FROM skill_lineage_parents "
                "WHERE parent_skill_id=?"
            ),
            (sid,),
        )
        for cr in self._adapter.fetchall(cur2):
            cid = cr["skill_id"]
            if cid not in visited:
                node["children"].append(
                    self._subtree(conn, cid, depth - 1, visited)
                )
        return node

    # Maintenance
    def clear(self) -> None:
        """Delete all data (keeps schema)."""
        self._ensure_open()
        if self._is_postgres:
            with self._mu:
                with self._adapter.writer() as conn:  # type: ignore[attr-defined]
                    try:
                        # CASCADE on skill_records cleans up: lineage_parents, tool_deps, tags
                        conn.execute(self._adapter.sql("DELETE FROM skill_records"))
                        # execution_analyses CASCADE cleans up skill_judgments
                        conn.execute(self._adapter.sql("DELETE FROM execution_analyses"))
                        conn.commit()
                        logger.info("SkillStore cleared")
                    except Exception:
                        conn.rollback()
                        raise
        else:
            with self._mu:
                self._conn.execute("BEGIN")
                try:
                    # CASCADE on skill_records cleans up: lineage_parents, tool_deps, tags
                    self._conn.execute("DELETE FROM skill_records")
                    # execution_analyses CASCADE cleans up skill_judgments
                    self._conn.execute("DELETE FROM execution_analyses")
                    self._conn.commit()
                    logger.info("SkillStore cleared")
                except Exception:
                    self._conn.rollback()
                    raise

    def vacuum(self) -> None:
        """Compact the database file."""
        self._ensure_open()
        with self._mu:
            self._adapter.vacuum(self._conn)

    # ------------------------------------------------------------------
    # Internal: Upsert / Insert / Deserialize
    # ------------------------------------------------------------------

    def _upsert(self, record: SkillRecord, *, conn: Any) -> None:
        """Insert or update skill_records + sync related rows.

        Called within a transaction holding ``self._mu``.
        *conn* is the active connection to use (write conn for SQLite,
        pool-borrowed connection for Postgres).
        """
        adp = self._adapter
        lin = record.lineage
        # content_snapshot is Dict[str, str]; store as JSON text
        snapshot_json = json.dumps(
            lin.content_snapshot, ensure_ascii=False
        )
        conn.execute(
            adp.sql(
                """
                INSERT INTO skill_records (
                    skill_id, name, description, path, is_active, category,
                    visibility, creator_id,
                    lineage_origin, lineage_generation,
                    lineage_source_task_id, lineage_change_summary,
                    lineage_content_diff, lineage_content_snapshot,
                    lineage_created_at, lineage_created_by,
                    total_selections, total_applied,
                    total_completions, total_fallbacks,
                    first_seen, last_updated
                ) VALUES (?,?,?,?,?,?, ?,?, ?,?, ?,?, ?,?, ?,?, ?,?,?,?, ?,?)
                ON CONFLICT(skill_id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    path=excluded.path,
                    is_active=excluded.is_active,
                    category=excluded.category,
                    visibility=excluded.visibility,
                    creator_id=excluded.creator_id,
                    lineage_origin=excluded.lineage_origin,
                    lineage_generation=excluded.lineage_generation,
                    lineage_source_task_id=excluded.lineage_source_task_id,
                    lineage_change_summary=excluded.lineage_change_summary,
                    lineage_content_diff=excluded.lineage_content_diff,
                    lineage_content_snapshot=excluded.lineage_content_snapshot,
                    lineage_created_at=excluded.lineage_created_at,
                    lineage_created_by=excluded.lineage_created_by,
                    total_selections=excluded.total_selections,
                    total_applied=excluded.total_applied,
                    total_completions=excluded.total_completions,
                    total_fallbacks=excluded.total_fallbacks,
                    last_updated=excluded.last_updated
                """
            ),
            (
                record.skill_id,
                record.name,
                record.description,
                record.path,
                int(record.is_active),
                record.category.value,
                record.visibility.value,
                record.creator_id,
                lin.origin.value,
                lin.generation,
                lin.source_task_id,
                lin.change_summary,
                lin.content_diff,
                snapshot_json,
                lin.created_at.isoformat(),
                lin.created_by,
                record.total_selections,
                record.total_applied,
                record.total_completions,
                record.total_fallbacks,
                record.first_seen.isoformat(),
                record.last_updated.isoformat(),
            ),
        )

        # Sync lineage parents
        conn.execute(
            adp.sql("DELETE FROM skill_lineage_parents WHERE skill_id=?"),
            (record.skill_id,),
        )
        for pid in lin.parent_skill_ids:
            conn.execute(
                adp.sql(
                    "INSERT INTO skill_lineage_parents"
                    "(skill_id, parent_skill_id) VALUES(?,?)"
                ),
                (record.skill_id, pid),
            )

        # Sync tool dependencies
        conn.execute(
            adp.sql("DELETE FROM skill_tool_deps WHERE skill_id=?"),
            (record.skill_id,),
        )
        critical_set = set(record.critical_tools)
        for tk in record.tool_dependencies:
            conn.execute(
                adp.sql(
                    "INSERT INTO skill_tool_deps"
                    "(skill_id, tool_key, critical) VALUES(?,?,?)"
                ),
                (record.skill_id, tk, 1 if tk in critical_set else 0),
            )

        # Sync tags
        conn.execute(
            adp.sql("DELETE FROM skill_tags WHERE skill_id=?"),
            (record.skill_id,),
        )
        for tag in record.tags:
            conn.execute(
                adp.sql("INSERT INTO skill_tags(skill_id, tag) VALUES(?,?)"),
                (record.skill_id, tag),
            )

        # Sync analyses (insert only NEW ones, dedup by task_id)
        for a in record.recent_analyses:
            cur = conn.execute(
                adp.sql(
                    "SELECT id FROM execution_analyses WHERE task_id=?"
                ),
                (a.task_id,),
            )
            existing = adp.fetchone(cur)
            if existing is None:
                self._insert_analysis(a, conn=conn)

    def _insert_analysis(self, a: ExecutionAnalysis, *, conn: Any) -> int:
        """Insert an execution_analyses row + its skill_judgments.

        Called within a transaction holding ``self._mu``.

        Returns:
            int: The ``execution_analyses.id`` of the newly inserted row.
        """
        adp = self._adapter
        params = (
            a.task_id,
            a.timestamp.isoformat(),
            int(a.task_completed),
            a.execution_note,
            json.dumps(a.tool_issues, ensure_ascii=False),
            int(a.candidate_for_evolution),
            json.dumps(
                [s.to_dict() for s in a.evolution_suggestions],
                ensure_ascii=False,
            ),
            a.analyzed_by,
            a.analyzed_at.isoformat(),
        )

        if self._is_postgres:
            # Use RETURNING id for auto-identity column
            cur = conn.execute(
                adp.sql(
                    """
                    INSERT INTO execution_analyses (
                        task_id, timestamp,
                        task_completed, execution_note,
                        tool_issues, candidate_for_evolution,
                        evolution_suggestions, analyzed_by, analyzed_at
                    ) VALUES (?,?, ?,?, ?,?, ?,?,?)
                    ON CONFLICT (task_id) DO UPDATE SET
                        timestamp=EXCLUDED.timestamp,
                        task_completed=EXCLUDED.task_completed,
                        execution_note=EXCLUDED.execution_note,
                        tool_issues=EXCLUDED.tool_issues,
                        candidate_for_evolution=EXCLUDED.candidate_for_evolution,
                        evolution_suggestions=EXCLUDED.evolution_suggestions,
                        analyzed_by=EXCLUDED.analyzed_by,
                        analyzed_at=EXCLUDED.analyzed_at
                    RETURNING id
                    """
                ),
                params,
            )
            row = adp.fetchone(cur)
            analysis_id = row["id"]
        else:
            cur = conn.execute(
                """
                INSERT INTO execution_analyses (
                    task_id, timestamp,
                    task_completed, execution_note,
                    tool_issues, candidate_for_evolution,
                    evolution_suggestions, analyzed_by, analyzed_at
                ) VALUES (?,?, ?,?, ?,?, ?,?,?)
                """,
                params,
            )
            analysis_id = cur.lastrowid

        for j in a.skill_judgments:
            conn.execute(
                adp.sql(
                    "INSERT INTO skill_judgments "
                    "(analysis_id, skill_id, skill_applied, note) "
                    "VALUES (?,?,?,?)"
                ),
                (analysis_id, j.skill_id, int(j.skill_applied), j.note),
            )

        return analysis_id

    # ------------------------------------------------------------------
    # Deserialization
    # ------------------------------------------------------------------

    def _to_record(
        self, conn: Any, row: Dict[str, Any]
    ) -> SkillRecord:
        """Deserialize a skill_records row + related rows → SkillRecord."""
        adp = self._adapter
        sid = row["skill_id"]

        cur = conn.execute(
            adp.sql(
                "SELECT parent_skill_id "
                "FROM skill_lineage_parents WHERE skill_id=?"
            ),
            (sid,),
        )
        parents = [r["parent_skill_id"] for r in adp.fetchall(cur)]

        # Deserialize content_snapshot: stored as JSON dict
        # mapping relative file paths to their text content
        raw_snapshot = row["lineage_content_snapshot"] or "{}"
        snapshot: Dict[str, str] = json.loads(raw_snapshot)

        lineage = SkillLineage(
            origin=SkillOrigin(row["lineage_origin"]),
            generation=row["lineage_generation"],
            parent_skill_ids=parents,
            source_task_id=row["lineage_source_task_id"],
            change_summary=row["lineage_change_summary"],
            content_diff=row["lineage_content_diff"],
            content_snapshot=snapshot,
            created_at=datetime.fromisoformat(row["lineage_created_at"]),
            created_by=row["lineage_created_by"],
        )

        cur2 = conn.execute(
            adp.sql(
                "SELECT tool_key, critical "
                "FROM skill_tool_deps WHERE skill_id=?"
            ),
            (sid,),
        )
        dep_rows = adp.fetchall(cur2)

        cur3 = conn.execute(
            adp.sql("SELECT tag FROM skill_tags WHERE skill_id=?"),
            (sid,),
        )
        tag_rows = adp.fetchall(cur3)

        # Load recent analyses involving this skill (via skill_judgments).
        # skill_judgments.skill_id stores the true skill_id (same as DB PK).
        cur4 = conn.execute(
            adp.sql(
                "SELECT ea.* FROM execution_analyses ea "
                "JOIN skill_judgments sj ON ea.id = sj.analysis_id "
                "WHERE sj.skill_id = ? "
                "ORDER BY ea.timestamp DESC LIMIT ?"
            ),
            (sid, SkillRecord.MAX_RECENT),
        )
        analysis_rows = adp.fetchall(cur4)

        return SkillRecord(
            skill_id=sid,
            name=row["name"],
            description=row["description"],
            path=row["path"],
            is_active=bool(row["is_active"]),
            category=SkillCategory(row["category"]),
            tags=[r["tag"] for r in tag_rows],
            visibility=(
                SkillVisibility(row["visibility"])
                if row["visibility"] else SkillVisibility.PRIVATE
            ),
            creator_id=row["creator_id"] or "",
            lineage=lineage,
            tool_dependencies=[r["tool_key"] for r in dep_rows],
            critical_tools=[
                r["tool_key"] for r in dep_rows if r["critical"]
            ],
            total_selections=row["total_selections"],
            total_applied=row["total_applied"],
            total_completions=row["total_completions"],
            total_fallbacks=row["total_fallbacks"],
            recent_analyses=[
                self._to_analysis(conn, r) for r in reversed(analysis_rows)
            ],
            first_seen=datetime.fromisoformat(row["first_seen"]),
            last_updated=datetime.fromisoformat(row["last_updated"]),
        )

    def _to_analysis(
        self, conn: Any, row: Dict[str, Any]
    ) -> ExecutionAnalysis:
        """Deserialize an execution_analyses row + judgments → ExecutionAnalysis."""
        adp = self._adapter
        analysis_id = row["id"]

        cur = conn.execute(
            adp.sql(
                "SELECT skill_id, skill_applied, note "
                "FROM skill_judgments WHERE analysis_id=?"
            ),
            (analysis_id,),
        )
        judgment_rows = adp.fetchall(cur)

        suggestions: list = []
        raw_suggestions = row["evolution_suggestions"]
        if raw_suggestions:
            try:
                suggestions = [
                    EvolutionSuggestion.from_dict(s)
                    for s in json.loads(raw_suggestions)
                ]
            except (json.JSONDecodeError, KeyError, ValueError):
                pass

        return ExecutionAnalysis(
            task_id=row["task_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            task_completed=bool(row["task_completed"]),
            execution_note=row["execution_note"],
            tool_issues=json.loads(row["tool_issues"]),
            skill_judgments=[
                SkillJudgment(
                    skill_id=jr["skill_id"],
                    skill_applied=bool(jr["skill_applied"]),
                    note=jr["note"],
                )
                for jr in judgment_rows
            ],
            evolution_suggestions=suggestions,
            analyzed_by=row["analyzed_by"],
            analyzed_at=datetime.fromisoformat(row["analyzed_at"]),
        )
