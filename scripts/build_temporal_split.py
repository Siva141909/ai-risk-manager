"""Compute and persist the temporal split metadata for train_transaction.csv.

Reads only TransactionID/TransactionDT/isFraud (not the full 394-column
file) since only those are needed to determine and describe the split.
Writes data/processed/split_metadata.json — boundaries, row counts, fraud
counts/rates. Does NOT persist a duplicate copy of the transaction table;
the split is a deterministic function of TransactionDT
(src/ingestion/split.py) and can be recomputed by any downstream code
that loads the real file.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from src.ingestion.split import assign_split, compute_split_boundaries, split_summary

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW = PROJECT_ROOT / "data" / "raw"
OUT = PROJECT_ROOT / "data" / "processed" / "split_metadata.json"


def main() -> None:
    df = pd.read_csv(RAW / "train_transaction.csv", usecols=["TransactionID", "TransactionDT", "isFraud"])

    boundaries = compute_split_boundaries(df)
    labels = assign_split(df)
    summary = split_summary(df, labels)

    # Integrity checks before persisting — fail loudly rather than write a bad artifact.
    assert labels.isin(["train", "validation", "test"]).all()
    assert sum(s["row_count"] for s in summary.values()) == len(df)
    assert df["TransactionID"].is_unique

    metadata = {
        "method": "row-time-order split: stable sort (mergesort) by TransactionDT ascending, "
        "then contiguous 70/15/15 row blocks",
        "train_frac": 0.70,
        "val_frac": 0.15,
        "test_frac": 0.15,
        "seed_note": "deterministic function of TransactionDT — no RNG seed needed for this split",
        "source_file": "data/raw/train_transaction.csv",
        "boundaries": asdict(boundaries),
        "summary": summary,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        json.dump(metadata, f, indent=2)

    print(json.dumps(metadata, indent=2))
    print(f"\nWritten to {OUT}")


if __name__ == "__main__":
    main()
