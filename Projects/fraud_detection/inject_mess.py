"""Deliberately corrupt a clean transactions file and record exactly what was done.

The manifest lets you prove the pipeline works: injected problems vs. problems
the pipeline actually caught (see tests/test_end_to_end.py).

Two kinds of mess:
  * recoverable  -> pipeline should REPAIR these (row ends up in the warehouse)
  * unrecoverable -> pipeline should QUARANTINE these (row ends up in rejects.csv)
Injections touch disjoint rows, so each rejected row has exactly one reason.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

# (name, fraction of rows, expected reject reason or None if recoverable)
PLAN = [
    ("mixed_timestamp_format", 0.03, None),
    ("messy_text_whitespace_case", 0.03, None),
    ("zip_float_and_lost_leading_zero", 0.02, None),
    ("duplicate_row", 0.01, "duplicate_trans_num"),
    ("missing_merchant", 0.01, "missing_merchant"),
    ("negative_amt", 0.01, "negative_amt"),
    ("cc_num_scientific_notation", 0.01, "cc_num_precision_lost"),
    ("garbage_timestamp", 0.01, "invalid_trans_date_trans_time"),
    ("invalid_state", 0.01, "invalid_state"),
    ("invalid_gender", 0.01, "invalid_gender"),
]


def inject_mess(clean: pd.DataFrame, seed: int = 7) -> tuple[pd.DataFrame, dict]:
    rng = np.random.default_rng(seed)
    df = clean.astype(str).reset_index(drop=True)  # text, like read_csv(dtype=str)
    n = len(df)

    order = rng.permutation(n)
    rows: dict[str, pd.Index] = {}
    cursor = 0
    for name, frac, _ in PLAN:
        k = max(1, round(frac * n))
        rows[name] = df.index[order[cursor:cursor + k]]
        cursor += k
    assert cursor <= n, "not enough rows for the injection plan"

    # --- recoverable ---
    i = rows["mixed_timestamp_format"]
    df.loc[i, "trans_date_trans_time"] = (
        pd.to_datetime(df.loc[i, "trans_date_trans_time"]).dt.strftime("%m/%d/%Y %H:%M:%S")
    )
    i = rows["messy_text_whitespace_case"]
    for c in ("first", "last", "city"):
        df.loc[i, c] = "  " + df.loc[i, c].str.upper() + " "
    df.loc[i, "state"] = df.loc[i, "state"].str.lower()
    df.loc[i, "category"] = df.loc[i, "category"].str.upper()
    i = rows["zip_float_and_lost_leading_zero"]
    df.loc[i, "zip"] = df.loc[i, "zip"].astype(int).astype(str) + ".0"

    # --- unrecoverable ---
    df.loc[rows["missing_merchant"], "merchant"] = ""
    df.loc[rows["negative_amt"], "amt"] = "-" + df.loc[rows["negative_amt"], "amt"]
    i = rows["cc_num_scientific_notation"]
    df.loc[i, "cc_num"] = df.loc[i, "cc_num"].map(lambda v: f"{float(v):.5E}")
    df.loc[rows["garbage_timestamp"], "trans_date_trans_time"] = "not a date"
    df.loc[rows["invalid_state"], "state"] = "Texas"
    df.loc[rows["invalid_gender"], "gender"] = "X"

    # --- duplicates: exact copies placed right after the original ---
    df["_order"] = np.arange(n, dtype=float)
    dupes = df.loc[rows["duplicate_row"]].copy()
    dupes["_order"] += 0.5
    messy = (pd.concat([df, dupes]).sort_values("_order", kind="stable")
             .drop(columns="_order").reset_index(drop=True))

    manifest = {
        "rows_original": n,
        "rows_after_injection": len(messy),
        "injected": {name: len(idx) for name, idx in rows.items()},
        "expected_reject_reasons": {
            reason: len(rows[name]) for name, _, reason in PLAN if reason
        },
    }
    manifest["expected_rows_rejected"] = sum(manifest["expected_reject_reasons"].values())
    manifest["expected_rows_clean"] = len(messy) - manifest["expected_rows_rejected"]
    return messy, manifest


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=Path("data/clean.csv"))
    p.add_argument("--out", type=Path, default=Path("data/messy.csv"))
    p.add_argument("--manifest", type=Path, default=Path("data/manifest.json"))
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()

    messy, manifest = inject_mess(pd.read_csv(a.input, dtype=str), a.seed)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    messy.to_csv(a.out, index=False)
    a.manifest.write_text(json.dumps(manifest, indent=2))
    print(f"wrote {len(messy):,} messy rows -> {a.out}")
    print(f"manifest -> {a.manifest}")


if __name__ == "__main__":
    main()
