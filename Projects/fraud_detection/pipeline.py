"""Extract -> transform -> load for transaction data.

* Extract:   stream the CSV in chunks, everything read as text.
* Transform: txn_etl.clean (repair what's repairable, quarantine the rest).
* Load:      idempotent. Clean rows go to a staging table, then
             INSERT OR IGNORE into the target keyed on trans_num, so
             re-running the same file inserts nothing new.
* Audit:     one row per run in etl_runs (counts in/clean/rejected/inserted).

SQLite keeps the repo runnable anywhere. The same shape works on SQL Server
(MERGE) or Postgres (INSERT ... ON CONFLICT DO NOTHING); see README.
"""
from __future__ import annotations

import argparse
import logging
import sqlite3
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .clean import REQUIRED_COLUMNS, clean_transactions, summarize_rejects

log = logging.getLogger("txn_etl")

DDL = """
CREATE TABLE IF NOT EXISTS transactions (
    "trans_num"             TEXT PRIMARY KEY,
    "trans_date_trans_time" TEXT NOT NULL,
    "cc_num"                TEXT NOT NULL,
    "merchant"              TEXT NOT NULL,
    "category"              TEXT NOT NULL,
    "amt"                   REAL NOT NULL CHECK ("amt" >= 0),
    "first"                 TEXT NOT NULL,
    "last"                  TEXT NOT NULL,
    "gender"                TEXT NOT NULL CHECK ("gender" IN ('M','F')),
    "street"                TEXT NOT NULL,
    "city"                  TEXT NOT NULL,
    "state"                 TEXT NOT NULL,
    "zip"                   TEXT NOT NULL,
    "lat"                   REAL NOT NULL,
    "long"                  REAL NOT NULL,
    "city_pop"              INTEGER NOT NULL,
    "job"                   TEXT,
    "dob"                   TEXT NOT NULL,
    "unix_time"             INTEGER NOT NULL,
    "merch_lat"             REAL NOT NULL,
    "merch_long"            REAL NOT NULL,
    "is_fraud"              INTEGER NOT NULL CHECK ("is_fraud" IN (0,1)),
    "loaded_at"             TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_transactions_time ON transactions ("trans_date_trans_time");

CREATE TABLE IF NOT EXISTS etl_runs (
    run_id                INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at            TEXT NOT NULL,
    finished_at           TEXT NOT NULL,
    input_file            TEXT NOT NULL,
    rows_in               INTEGER NOT NULL,
    rows_clean            INTEGER NOT NULL,
    rows_rejected         INTEGER NOT NULL,
    rows_inserted         INTEGER NOT NULL,
    rows_skipped_existing INTEGER NOT NULL
);
"""

COLS_SQL = ", ".join(f'"{c}"' for c in REQUIRED_COLUMNS)


@dataclass
class RunStats:
    rows_in: int = 0
    rows_clean: int = 0
    rows_rejected: int = 0
    rows_inserted: int = 0
    rows_skipped_existing: int = 0
    reject_reasons: Counter = field(default_factory=Counter)


def load(conn: sqlite3.Connection, clean: pd.DataFrame) -> tuple[int, int]:
    """Idempotent load. Returns (rows_inserted, rows_skipped_existing)."""
    if clean.empty:
        return 0, 0
    out = clean.copy()
    out["trans_date_trans_time"] = out["trans_date_trans_time"].dt.strftime("%Y-%m-%d %H:%M:%S")
    out["dob"] = out["dob"].dt.strftime("%Y-%m-%d")

    out.to_sql("stg_transactions", conn, if_exists="replace", index=False)
    cur = conn.execute(
        f"INSERT OR IGNORE INTO transactions ({COLS_SQL}) "
        f"SELECT {COLS_SQL} FROM stg_transactions"
    )
    inserted = cur.rowcount
    conn.execute("DROP TABLE stg_transactions")
    conn.commit()
    return inserted, len(out) - inserted


def run(input_path: Path, db_path: Path, rejects_path: Path,
        chunksize: int = 100_000) -> RunStats:
    started = datetime.now(timezone.utc)
    stats = RunStats()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    rejects_path.parent.mkdir(parents=True, exist_ok=True)
    rejects_path.unlink(missing_ok=True)  # rejects reflect THIS run only

    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(DDL)
        for i, chunk in enumerate(pd.read_csv(input_path, dtype=str, chunksize=chunksize), 1):
            clean, rejects = clean_transactions(chunk)
            inserted, skipped = load(conn, clean)

            if not rejects.empty:
                rejects.to_csv(rejects_path, mode="a", index=False,
                               header=not rejects_path.exists())

            stats.rows_in += len(chunk)
            stats.rows_clean += len(clean)
            stats.rows_rejected += len(rejects)
            stats.rows_inserted += inserted
            stats.rows_skipped_existing += skipped
            stats.reject_reasons.update(summarize_rejects(rejects).to_dict())
            log.info("chunk %d: in=%d clean=%d rejected=%d inserted=%d",
                     i, len(chunk), len(clean), len(rejects), inserted)

        rejects_path.touch(exist_ok=True)
        conn.execute(
            "INSERT INTO etl_runs (started_at, finished_at, input_file, rows_in, "
            "rows_clean, rows_rejected, rows_inserted, rows_skipped_existing) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (started.isoformat(timespec="seconds"),
             datetime.now(timezone.utc).isoformat(timespec="seconds"),
             str(input_path), stats.rows_in, stats.rows_clean, stats.rows_rejected,
             stats.rows_inserted, stats.rows_skipped_existing),
        )
        conn.commit()
    finally:
        conn.close()
    return stats


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--input", type=Path, default=Path("data/messy.csv"))
    p.add_argument("--db", type=Path, default=Path("out/warehouse.db"))
    p.add_argument("--rejects", type=Path, default=Path("out/rejects.csv"))
    p.add_argument("--chunksize", type=int, default=100_000)
    a = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    s = run(a.input, a.db, a.rejects, a.chunksize)

    print("\n=== run summary ===")
    print(f"rows in:               {s.rows_in:,}")
    print(f"rows clean:            {s.rows_clean:,}")
    print(f"rows rejected:         {s.rows_rejected:,}")
    print(f"rows inserted:         {s.rows_inserted:,}")
    print(f"skipped (already in):  {s.rows_skipped_existing:,}")
    if s.reject_reasons:
        print("\nreject reasons:")
        for reason, n in s.reject_reasons.most_common():
            print(f"  {reason:<35} {n:>6,}")


if __name__ == "__main__":
    main()