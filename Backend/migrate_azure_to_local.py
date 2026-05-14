"""
Migrate user data tables from Azure SQL to local SQL Server.

Usage:
    cd Backend
    .\.venv\Scripts\activate
    python migrate_azure_to_local.py

What it does:
  1. Connects to Azure SQL using the values from the AZURE block of
     unified.env (preserved as comments there for rollback).
  2. Connects to local SQL Server using the active LOCAL SQL SERVER block.
  3. Enumerates every user table in the source dbo schema (ignoring system
     tables and sysdiagrams).
  4. For each table, reads the data into a pandas DataFrame, then
     bulk-loads it into the destination database. Existing tables of the
     same name in the target are replaced (``if_exists='replace'``).
  5. After loading, verifies row counts match between source and target.

Limitations (deliberate trade-offs for simplicity):
  - Does NOT preserve indexes, FK constraints, computed columns, or
    sequences. For an LLM that just runs SELECTs, this is fine.
  - For very large tables (>1M rows) consider sqlpackage / bcp instead --
    pandas is slower but doesn't need an extra install.
  - Column types in the target are inferred by pandas. NVARCHAR length
    may differ from source (pandas picks NVARCHAR(MAX) for object cols).
    Functionally equivalent for SELECT workloads.

Re-run safety:
  - Idempotent. Each run drops + recreates the target tables. Safe to
    run multiple times.
"""

import os
import sys
import time
import urllib.parse

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text


# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
load_dotenv("unified.env")

# Source: Azure SQL (mirrors the commented AZURE block in unified.env)
SRC = {
    "host":     "uniview-database.database.windows.net",
    "database": "uniview",
    "user":     "uniview",
    "password": "Affine@2025",
}

# Target: local SQL Server (read from the active LOCAL block in unified.env)
DST = {
    "host":     os.getenv("SQL_HOST",     "localhost,1433").strip("'\" "),
    "database": os.getenv("SQL_DATABASE", "unified").strip("'\" "),
    "user":     os.getenv("SQL_USERNAME", "sa").strip("'\" "),
    "password": os.getenv("SQL_PASSWORD", "").strip("'\" "),
}

DRIVER = os.getenv("SQL_DRIVER", "ODBC Driver 18 for SQL Server").strip("'\" ")


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def build_url(cfg: dict) -> str:
    """Build a SQLAlchemy URL for an MSSQL / Azure SQL endpoint."""
    odbc = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={cfg['host']};"
        f"DATABASE={cfg['database']};"
        f"UID={cfg['user']};"
        f"PWD={cfg['password']};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
        "Connection Timeout=30;"
    )
    return "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(odbc)


def connect(label: str, cfg: dict):
    print(f"  {label:7s}: {cfg['user']}@{cfg['host']}/{cfg['database']} ...", end=" ", flush=True)
    engine = create_engine(build_url(cfg), future=True)
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    print("OK")
    return engine


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main() -> int:
    print("=" * 72)
    print("  Azure SQL  ->  Local SQL Server migration")
    print("=" * 72)

    print("\nConnecting:")
    src = connect("source", SRC)
    dst = connect("target", DST)

    print("\nEnumerating user tables in source dbo schema...")
    src_inspector = inspect(src)
    tables = sorted(
        t for t in src_inspector.get_table_names(schema="dbo")
        if not t.lower().startswith("sysdiagrams")
        and not t.lower().startswith("__")
    )
    if not tables:
        print("No user tables found in source dbo schema.  Nothing to migrate.")
        return 0
    print(f"Found {len(tables)} table(s):")
    for t in tables:
        print(f"    - dbo.[{t}]")

    print(f"\nMigrating to [{DST['database']}].dbo:")
    print("-" * 72)

    successes: list[tuple[str, int, float]] = []
    failures:  list[tuple[str, str]]        = []

    overall_start = time.time()
    for i, table in enumerate(tables, 1):
        t0 = time.time()
        print(f"[{i:2d}/{len(tables)}] {table:42s}", end=" ", flush=True)
        try:
            # Use bracket-quoted table name to handle reserved words like [Order]
            df = pd.read_sql(text(f"SELECT * FROM dbo.[{table}]"), src)

            df.to_sql(
                name=table,
                con=dst,
                schema="dbo",
                if_exists="replace",
                index=False,
                chunksize=1000,
            )

            elapsed = time.time() - t0
            successes.append((table, len(df), elapsed))
            print(f"OK     {len(df):>8} rows  in {elapsed:5.1f}s")
        except Exception as e:
            elapsed = time.time() - t0
            err = str(e).splitlines()[0][:120]
            failures.append((table, err))
            print(f"FAIL   ({elapsed:.1f}s)  {err}")

    print("-" * 72)
    total = time.time() - overall_start
    print(f"\nDone in {total:.1f}s.  Success: {len(successes)}.  Failures: {len(failures)}.")

    # Verify row counts on the target side
    if successes:
        print("\nVerifying destination row counts:")
        with dst.connect() as conn:
            for table, src_rows, _ in successes:
                dst_rows = conn.exec_driver_sql(
                    f"SELECT COUNT(*) FROM dbo.[{table}]"
                ).scalar()
                flag = "OK" if dst_rows == src_rows else "MISMATCH"
                print(f"  {flag:9s} dbo.[{table:<42s}] src={src_rows:>8}  dst={dst_rows:>8}")

    if failures:
        print("\nFailed tables (re-run after addressing):")
        for table, err in failures:
            print(f"  - dbo.[{table}]: {err}")
        return 1

    print(
        "\nMigration complete.  You can now restart uvicorn and the app "
        "will read from the local SQL Server."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
