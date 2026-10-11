"""Мінімальний мігратор: застосовує SQL-файли з migrations/ у порядку номерів
і запам'ятовує застосовані версії в таблиці schema_migrations.
Запуск: python migrate.py [--no-seed]"""

import os
import sys
import time
from pathlib import Path

import psycopg

from app.config import settings

MIGRATIONS = Path(__file__).parent / "migrations"


def dsn(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://")


def apply(url: str, seed: bool = True, verbose: bool = True) -> list[str]:
    applied_now = []
    with psycopg.connect(dsn(url), autocommit=False) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP NOT NULL DEFAULT now())"
        )
        done = {r[0] for r in conn.execute("SELECT version FROM schema_migrations")}
        conn.commit()
        for f in sorted(MIGRATIONS.glob("*.sql")):
            if f.name in done or (not seed and "seed" in f.name):
                continue
            t = time.perf_counter()
            conn.execute(f.read_text(encoding="utf-8"))
            conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (f.name,))
            conn.commit()
            applied_now.append(f.name)
            if verbose:
                print(f"  applied {f.name:<16} {1000 * (time.perf_counter() - t):6.1f} ms")
    return applied_now


def wait_for_db(url: str, attempts: int = 30):
    for i in range(attempts):
        try:
            with psycopg.connect(dsn(url), connect_timeout=2):
                return
        except psycopg.OperationalError:
            print(f"  waiting for database... ({i + 1}/{attempts})")
            time.sleep(1)
    sys.exit("Database is not available")


if __name__ == "__main__":
    url = os.getenv("DATABASE_URL", settings.database_url)
    wait_for_db(url)
    print(f"Migrations: {MIGRATIONS}")
    new = apply(url, seed="--no-seed" not in sys.argv)
    print(f"Done: {len(new)} new migration(s)" if new else "Database is up to date")
