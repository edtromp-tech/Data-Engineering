"""Inject known mess, run the pipeline, and check the pipeline caught exactly it."""
import sqlite3

import pandas as pd

from clean import clean_transactions, summarize_rejects
from inject_mess import inject_mess
from pipeline import run
from sample_data import make_clean_sample


def test_clean_catches_exactly_what_was_injected():
    messy, manifest = inject_mess(make_clean_sample(2000, seed=1), seed=2)
    clean, rejects = clean_transactions(messy)

    assert summarize_rejects(rejects).to_dict() == manifest["expected_reject_reasons"]
    assert len(rejects) == manifest["expected_rows_rejected"]
    assert len(clean) == manifest["expected_rows_clean"]


def test_recoverable_mess_is_repaired_not_rejected():
    messy, _ = inject_mess(make_clean_sample(500, seed=3), seed=4)
    clean, _ = clean_transactions(messy)
    assert clean["state"].str.fullmatch(r"[A-Z]{2}").all()
    assert clean["zip"].str.fullmatch(r"\d{5}").all()
    assert (clean["category"] == clean["category"].str.lower()).all()
    assert clean["trans_date_trans_time"].notna().all()


def test_pipeline_is_idempotent(tmp_path):
    messy, manifest = inject_mess(make_clean_sample(1000, seed=5), seed=6)
    src = tmp_path / "messy.csv"
    messy.to_csv(src, index=False)
    db, rej = tmp_path / "wh.db", tmp_path / "rejects.csv"

    first = run(src, db, rej, chunksize=10_000)
    assert first.rows_in == manifest["rows_after_injection"]
    assert first.rows_rejected == manifest["expected_rows_rejected"]
    assert first.rows_inserted == manifest["expected_rows_clean"]
    assert len(pd.read_csv(rej)) == first.rows_rejected

    second = run(src, db, rej, chunksize=10_000)  # same file again
    assert second.rows_inserted == 0
    assert second.rows_skipped_existing == second.rows_clean

    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == first.rows_inserted
        assert conn.execute("SELECT COUNT(*) FROM etl_runs").fetchone()[0] == 2


def test_chunked_run_matches_single_chunk(tmp_path):
    messy, _ = inject_mess(make_clean_sample(1500, seed=7), seed=8)
    src = tmp_path / "messy.csv"
    messy.to_csv(src, index=False)

    one = run(src, tmp_path / "a.db", tmp_path / "a.csv", chunksize=100_000)
    many = run(src, tmp_path / "b.db", tmp_path / "b.csv", chunksize=137)

    # Adjacent duplicates can straddle a chunk boundary; those are then
    # skipped by the idempotent load instead of rejected. Totals must agree.
    assert many.rows_in == one.rows_in
    assert many.rows_inserted == one.rows_inserted
    assert many.rows_rejected + many.rows_skipped_existing == one.rows_rejected + one.rows_skipped_existing
