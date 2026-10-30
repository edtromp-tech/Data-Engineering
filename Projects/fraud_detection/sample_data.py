"""Generate a small, fully synthetic, *clean* transactions file.

Lets the repo run end-to-end without downloading anything. The columns match
the public Sparkov-style credit-card fraud dataset, so you can point the
pipeline at that file instead (check the license of whichever copy you use).
"""
from __future__ import annotations

import argparse
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

COLUMNS = [
    "trans_date_trans_time", "cc_num", "merchant", "category", "amt",
    "first", "last", "gender", "street", "city", "state", "zip",
    "lat", "long", "city_pop", "job", "dob", "trans_num", "unix_time",
    "merch_lat", "merch_long", "is_fraud",
]

# zip, city, state, lat, long, population (approximate, for realism only)
CITIES = [
    ("02134", "Boston", "MA", 42.3601, -71.1330, 645966),
    ("10001", "New York", "NY", 40.7506, -73.9972, 8419000),
    ("60601", "Chicago", "IL", 41.8858, -87.6181, 2696000),
    ("78701", "Austin", "TX", 30.2711, -97.7437, 961855),
    ("29577", "Myrtle Beach", "SC", 33.6891, -78.8867, 34695),
    ("57007", "Brookings", "SD", 44.3114, -96.7984, 24000),
    ("98101", "Seattle", "WA", 47.6101, -122.3344, 737015),
    ("80202", "Denver", "CO", 39.7525, -104.9995, 715522),
]
FIRST = ["Ava", "Liam", "Noah", "Emma", "Olivia", "Mason", "Sofia", "Ethan"]
LAST = ["McDonald", "O'Brien", "Nguyen", "Garcia", "Smith", "Johnson", "Patel", "Kim"]
JOBS = ["Engineer", "Teacher", "Nurse", "Accountant", "Chef", "Electrician"]
CATEGORIES = ["grocery_pos", "gas_transport", "entertainment", "shopping_net", "food_dining"]
MERCHANTS = ["Kuhn LLC", "Rice Group", "Stokes Inc", "Hudson Ltd", "Bauch Co", "Vega PLC"]


def make_clean_sample(n: int = 1000, seed: int = 42) -> pd.DataFrame:
    rng = random.Random(seed)
    start = datetime(2020, 1, 1)
    span = 2 * 365 * 24 * 3600
    rows = []
    for _ in range(n):
        zip_, city, state, lat, lon, pop = rng.choice(CITIES)
        ts = start + timedelta(seconds=rng.randrange(span))
        rows.append({
            "trans_date_trans_time": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "cc_num": str(rng.randrange(10**15, 10**16)),
            "merchant": rng.choice(MERCHANTS),
            "category": rng.choice(CATEGORIES),
            "amt": max(0.01, round(min(rng.lognormvariate(3.5, 1.0), 5000), 2)),
            "first": rng.choice(FIRST),
            "last": rng.choice(LAST),
            "gender": rng.choice(["M", "F"]),
            "street": f"{rng.randrange(1, 9999)} Main St",
            "city": city,
            "state": state,
            "zip": zip_,
            "lat": lat,
            "long": lon,
            "city_pop": pop,
            "job": rng.choice(JOBS),
            "dob": (date(1950, 1, 1) + timedelta(days=rng.randrange(365 * 50))).isoformat(),
            "trans_num": f"{rng.getrandbits(128):032x}",
            "unix_time": int(ts.replace(tzinfo=timezone.utc).timestamp()),
            "merch_lat": round(lat + rng.uniform(-0.5, 0.5), 4),
            "merch_long": round(lon + rng.uniform(-0.5, 0.5), 4),
            "is_fraud": int(rng.random() < 0.01),
        })
    return pd.DataFrame(rows, columns=COLUMNS)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rows", type=int, default=20_000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", type=Path, default=Path("data/clean.csv"))
    a = p.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    make_clean_sample(a.rows, a.seed).to_csv(a.out, index=False)
    print(f"wrote {a.rows:,} clean rows -> {a.out}")


if __name__ == "__main__":
    main()
