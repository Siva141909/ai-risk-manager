"""Phase 2E — build and persist the point-in-time-safe feature matrix.

Reads data/raw/train_transaction.csv + train_identity.csv, builds the
full feature matrix once (src/features/pipeline.py), and writes it to
data/processed/features.parquet — a single persisted artifact that
scripts/train_baseline.py, scripts/calibrate_and_threshold.py, and
scripts/evaluate_baseline.py all reuse, instead of each re-running the
~450-column feature build (avoids repeated ~1-2 minute recomputation
across a multi-script workflow — "persisted feature artifacts only when
justified" per Phase 2's performance constraints).

Does NOT modify data/raw/. Read-only against the raw files.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.features.pipeline import build_feature_matrix, load_raw_transactions

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUT_PARQUET = PROJECT_ROOT / "data" / "processed" / "features.parquet"
OUT_META = PROJECT_ROOT / "data" / "processed" / "features_metadata.json"


def main() -> None:
    print("Loading raw transactions + identity join...")
    raw_df = load_raw_transactions(RAW_DIR)
    print(f"Raw shape: {raw_df.shape}")

    print("Building feature matrix (proxies, temporal split, engineered + historical features)...")
    artifact = build_feature_matrix(raw_df)
    print(f"Feature matrix shape: {artifact.df.shape}, {len(artifact.feature_columns)} feature columns")

    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    artifact.df.to_parquet(OUT_PARQUET, index=False)

    split_counts = artifact.df["split"].value_counts().to_dict()
    split_fraud_rates = artifact.df.groupby("split")["isFraud"].mean().mul(100).to_dict()
    metadata = {
        "n_rows": len(artifact.df),
        "n_feature_columns": len(artifact.feature_columns),
        "feature_columns": artifact.feature_columns,
        "split_row_counts": {k: int(v) for k, v in split_counts.items()},
        "split_fraud_rate_pct": {k: round(float(v), 4) for k, v in split_fraud_rates.items()},
    }
    with OUT_META.open("w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nWritten to {OUT_PARQUET}")
    print(f"Metadata written to {OUT_META}")
    print(json.dumps({k: v for k, v in metadata.items() if k != "feature_columns"}, indent=2))


if __name__ == "__main__":
    main()
