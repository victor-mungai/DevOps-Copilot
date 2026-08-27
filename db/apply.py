"""Apply a .sql migration file to the database in $MIGRATION_DB_URL.

Usage:
    set MIGRATION_DB_URL=postgresql://user:pass@host:5432/db?sslmode=require   (do NOT commit this)
    python db/apply.py db/migrations/0001_core_schema.sql

The URL is read from the environment so no secret is ever stored in the repo.
"""

import os
import sys
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import psycopg2


def _psycopg2_url(url: str) -> str:
    if url.startswith("postgresql+psycopg2://"):
        url = "postgresql://" + url[len("postgresql+psycopg2://") :]
    elif url.startswith("postgres+psycopg2://"):
        url = "postgresql://" + url[len("postgres+psycopg2://") :]

    parts = urlsplit(url)
    query = parse_qs(parts.query, keep_blank_values=True)
    query["sslmode"] = ["require"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query, doseq=True), parts.fragment))


def main() -> None:
    url = os.environ.get("MIGRATION_DB_URL")
    if not url:
        sys.exit("MIGRATION_DB_URL is not set")
    if len(sys.argv) < 2:
        sys.exit("usage: python db/apply.py <path-to-sql>")

    path = sys.argv[1]
    with open(path, "r", encoding="utf-8") as fh:
        sql = fh.read()

    conn = psycopg2.connect(_psycopg2_url(url))
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            # Report resulting tables for confirmation.
            cur.execute(
                "select table_name from information_schema.tables "
                "where table_schema = 'public' order by table_name"
            )
            tables = [r[0] for r in cur.fetchall()]
        print(f"Applied {path}")
        print("public tables:", ", ".join(tables) if tables else "(none)")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
