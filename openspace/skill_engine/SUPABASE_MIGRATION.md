# Supabase / Postgres Migration Guide

## Overview

`SkillStore` supports two storage backends:

| Backend   | Activation                                   | Notes                             |
|-----------|----------------------------------------------|-----------------------------------|
| **SQLite** | `OPENSPACE_SKILL_DB_URL` **unset** (default) | Zero config, file-based, WAL mode |
| **Postgres** | `OPENSPACE_SKILL_DB_URL=postgresql://...`  | Supabase or any Postgres ≥ 9.6    |

The switch is **fully transparent** — all public `SkillStore` methods behave
identically regardless of the backend.

---

## Step 1 — Install the extra dependency

```bash
pip install "psycopg[binary,pool]>=3.1"
```

This is **not** added to `pyproject.toml` / `requirements.txt` automatically.
Add the line above to your project's dependency file when enabling the Postgres
backend in production.

---

## Step 2 — Get your Supabase connection string

1. Go to your [Supabase Dashboard](https://app.supabase.com/project/fhrynagbidbznfvuoxcn).
2. Click **Settings → Database**.
3. Under **Connection string**, choose either:

   - **Direct connection** (best for long-running processes / self-hosted):
     ```
     postgresql://postgres:<PASSWORD>@db.fhrynagbidbznfvuoxcn.supabase.co:5432/postgres
     ```
   - **Pooler (Transaction mode)** (best for serverless / short-lived connections):
     ```
     postgresql://postgres.fhrynagbidbznfvuoxcn:<PASSWORD>@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
     ```

4. Replace `<PASSWORD>` with your actual database password.

> **Tip:** For persistent services (e.g. a long-running Python process) prefer
> the **direct** connection string. For serverless functions use the pooler URL.

---

## Step 3 — Set the environment variable

```bash
export OPENSPACE_SKILL_DB_URL="postgresql://postgres:<PASSWORD>@db.fhrynagbidbznfvuoxcn.supabase.co:5432/postgres"
```

Or add it to your `.env` file:

```dotenv
OPENSPACE_SKILL_DB_URL=postgresql://postgres:<PASSWORD>@db.fhrynagbidbznfvuoxcn.supabase.co:5432/postgres
```

---

## Step 4 — First run (schema auto-creation)

On first instantiation, `SkillStore()` will automatically:

1. Connect to Postgres using the URL.
2. Open a connection pool (`min_size=1, max_size=5`).
3. Run the full DDL (`CREATE TABLE IF NOT EXISTS …`) inside a transaction.
4. Run the idempotent migration (`ALTER TABLE … ADD COLUMN IF NOT EXISTS …`).

No manual `psql` commands or migration scripts are needed.

```python
from openspace.skill_engine.store import SkillStore

async with SkillStore() as store:
    # Tables are created on this line if they don't exist yet
    records = store.load_all()
```

---

## Caveats and operational notes

### Concurrent writes

The `SkillStore` uses a `threading.Lock` (`self._mu`) to serialise writes
internally.  With Postgres, write operations borrow a connection from the
pool and commit within the lock.  The pool size is `max_size=5`.

If you run **multiple separate processes** against the same Supabase database
simultaneously, Postgres's row-level locking handles concurrency correctly —
but be aware that `evolve_skill` and `record_analysis` perform multi-statement
transactions that need to succeed atomically.

### Pool size

The default pool is `min_size=1, max_size=5`.  Supabase Free tier allows up
to 60 concurrent connections; paid plans allow more.  Adjust pool size by
subclassing `_PostgresAdapter` if needed, or wait for a future config option.

### WAL / vacuum

The SQLite-specific `VACUUM` command becomes `VACUUM ANALYZE` in Postgres
(run outside a transaction with `autocommit=True`).  Supabase's managed
Postgres runs `autovacuum` automatically, so calling `store.vacuum()` is
optional.

### SQLite fallback

If `OPENSPACE_SKILL_DB_URL` is unset or does not start with
`postgresql://` / `postgres://`, the store silently falls back to the
original SQLite implementation.  No code changes are required.

### Env var takes precedence

The `db_path` constructor argument is **ignored** when the Postgres URL is
set.  The `store.db_path` property still returns the default SQLite path for
backward compatibility, but the store does not create or use that file.

---

## Rollback / switching back to SQLite

Simply unset the environment variable:

```bash
unset OPENSPACE_SKILL_DB_URL
```

The next `SkillStore()` instantiation will use SQLite.  Data already written
to Postgres remains there; it is not copied back to SQLite automatically.
