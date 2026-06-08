# Database migrations

Plain SQL migrations for the shared PostgreSQL database (Supabase).

| File | What | When |
|---|---|---|
| `migrations/0001_core_schema.sql` | `tenants`, `aws_accounts`, `insights` | **Required for first run** |
| `migrations/0002_conversations.sql` | `conversations`, `session_summaries` | Phase 2 (conversation memory) — optional now |

## Apply on Supabase

**Option A — SQL editor (simplest):** open the Supabase project → SQL Editor →
paste the contents of `0001_core_schema.sql` → Run. Repeat for `0002` when you
start Phase 2.

**Option B — psql / CLI:**
```bash
psql "postgresql://postgres:<password>@<host>:5432/postgres?sslmode=require" \
  -f db/migrations/0001_core_schema.sql
```

All migrations are idempotent (`CREATE ... IF NOT EXISTS`), so re-running is safe.

## Important ordering note
Run the migration **before** starting the services. Each service also calls
SQLAlchemy `create_all` on startup, but that uses `checkfirst=True`, so once the
tables exist from the migration it is a no-op — the migration stays the single
source of truth and avoids two services racing to create the same tables with
slightly different definitions.

## Connection string
Use the Supabase **direct** connection (port 5432) for migrations and services,
with `sslmode=require`. SQLAlchemy URL form used by the services:
```
postgresql+psycopg2://postgres:<password>@<host>:5432/postgres?sslmode=require
```
