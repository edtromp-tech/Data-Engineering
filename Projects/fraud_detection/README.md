# A messy-data ETL pipeline with quarantine, idempotent loads, and an audit trail

A small, tested pipeline that ingests credit-card transaction CSVs, **repairs what can be
repaired deterministically, quarantines what can't**, and loads the rest into a warehouse
table without ever creating duplicates on re-runs.

Most portfolio ETL projects load a tidy CSV into a table. This one starts from the
assumption that source data is wrong and shows what you do about it.

## What it demonstrates

| Skill | Where |
|---|---|
| Data cleaning and validation at scale (vectorized, no row loops) | `/clean.py` |
| Quarantine pattern: bad rows go to `rejects.csv` with reason codes, never silently "fixed" | `clean_transactions()` |
| Idempotent loads (staging table + keyed `INSERT OR IGNORE`), safe to re-run | `/pipeline.py` |
| Chunked processing of files larger than memory | `--chunksize` |
| Run auditing (`etl_runs` table: rows in / clean / rejected / inserted) | `/pipeline.py` |
| Proving correctness: inject known mess, assert the pipeline caught exactly that | `tests/test_end_to_end.py` |
| Unit tests per rule, CI on GitHub Actions | `tests/`, `.github/workflows/` |

## Quickstart

```bash
pip install -r requirements.txt

# 1. Generate a clean synthetic file (no download needed)
python -m sample_data --rows 20000

# 2. Corrupt it in known ways and write a manifest of what was done
python -m inject_mess

# 3. Run the pipeline
python -m pipeline

# 4. Run the tests
pytest -q
```

To use real data, point the pipeline at any CSV with the columns listed in
`REQUIRED_COLUMNS` (e.g. the public Sparkov-style credit-card fraud dataset; check the
license of whichever copy you use):
`python -m pipeline --input path/to/file.csv`

All data in this repo is synthetic.

## Results on the demo file

Injected mess vs. what the pipeline did (20,000 rows + 200 injected duplicates):

| Problem injected | Rows | Pipeline action |
|---|---:|---|
| Mixed timestamp formats (`06/21/2020 12:14:25`) | 600 | **Repaired** |
| Stray whitespace / ALL CAPS / lowercase state | 600 | **Repaired** |
| Zip stored as float with lost leading zero (`2134.0`) | 400 | **Repaired** |
| Duplicate transactions | 200 | Quarantined: `duplicate_trans_num` |
| Missing merchant | 200 | Quarantined: `missing_merchant` |
| Negative amount | 200 | Quarantined: `negative_amt` |
| Card number in scientific notation (`5.99542E+15`) | 200 | Quarantined: `cc_num_precision_lost` |
| Garbage timestamp | 200 | Quarantined: `invalid_trans_date_trans_time` |
| Invalid state (`Texas`) | 200 | Quarantined: `invalid_state` |
| Invalid gender (`X`) | 200 | Quarantined: `invalid_gender` |

```
rows in:               20,200
rows clean:            18,800
rows rejected:         1,400
rows inserted:         18,800
```

Re-running the same file inserts **0** new rows and skips 18,800 already loaded.
On a 505,000-row file the full run (clean + load) took about 27 seconds in my test
environment.

## Design decisions (and what went wrong along the way)

**Read everything as text.** My first draft let pandas infer types. Card numbers came in as
floats (`2.29116E+15`) and zip codes as ints, which silently destroys data: a 16-digit
card number stored as a float has already lost digits and can't be recovered. Now every
column is read as a string and the cleaner decides the types.

**Quarantine instead of "fixing" ambiguous values.** The first version took `abs()` of negative
amounts. But a negative might be a refund or a sign error and there's no way to know, so
those rows now go to `rejects.csv` with a reason. Same for unparseable dates, which used to
pass through unchanged.

**Row objects were the wrong tool.** The first version built one Python dataclass per row. That
is easy to read but orders of magnitude slower than vectorized pandas on a million rows.

**Only repair what's deterministic.** Trimming whitespace, restoring a dropped leading zero on a
zip, and trying a fixed list of date formats are all reversible-in-principle and
unambiguous. Each separator style maps to exactly one day/month order, so nothing is guessed.

**Duplicates: first occurrence wins.** Within a chunk, later copies are rejected. Across chunks
(or across runs), the keyed load skips rows already in the warehouse and reports them as
`skipped_existing` rather than `rejected`.

## Known limitations

- ALL-CAPS names lose information: `MCDONALD` becomes `Mcdonald`. Mixed-case names are left alone.
- Duplicate detection uses `trans_num` only. A real system might also match on
  card + merchant + amount + time window.
- Duplicates that straddle a chunk boundary are skipped at load time instead of rejected.
  The totals match; the label differs (covered by `test_chunked_run_matches_single_chunk`).
- SQLite is used so the repo runs anywhere. It is not a substitute for a real warehouse.

## Where to take it next

- **SQL Server / Postgres target.** Swap `load()` for `MERGE ... WHEN NOT MATCHED THEN INSERT`
  (SQL Server) or `INSERT ... ON CONFLICT (trans_num) DO NOTHING` (Postgres) through SQLAlchemy.
  The staging-table-then-merge shape stays the same.
- **Orchestration.** Wrap `run()` in an Airflow DAG or a Fabric/Data Factory pipeline with
  retries and failure alerts.
- **Data quality in dbt or Great Expectations** on top of the loaded table.
- **Containerize** with Docker and a compose file that includes the database.
- **Dimensional model.** Build customer, merchant, and date dimensions from `transactions`.

## Project layout

```
  clean.py        vectorized cleaning + validation, returns (clean, rejects)
  pipeline.py     chunked extract -> transform -> idempotent load + audit table
  sample_data.py  synthetic clean data generator
  inject_mess.py  controlled corruption + manifest of what was injected
  test_clean.py        one test per cleaning rule
  test_end_to_end.py   injected mess == caught mess; idempotency; chunking
```
