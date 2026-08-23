"""Phase 2A — formal feature inventory audit.

Read-only. Computes, for every column in train_transaction.csv (+ a
summary pass over train_identity.csv), the statistics needed to classify
it into the 7 Phase 2A buckets: missingness, dtype, cardinality,
correlation/fraud-rate-spread with isFraud, and — for high-missingness
columns specifically — fraud rate when present vs. absent (does
missingness itself carry signal?).

Writes scratch_feature_audit_output.json (git-ignored) with the full
numbers; docs/FEATURE_AUDIT.md is written by hand from this output plus
judgment, not auto-generated, so the reasoning is legible.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT = Path(__file__).resolve().parent.parent / "scratch_feature_audit_output.json"


def missingness_when_present_vs_absent(df: pd.DataFrame, col: str, target: str = "isFraud") -> dict:
    present_mask = df[col].notna()
    return {
        "pct_missing": round(float(df[col].isna().mean() * 100), 3),
        "fraud_rate_when_present_pct": round(float(df.loc[present_mask, target].mean() * 100), 3)
        if present_mask.any() else None,
        "fraud_rate_when_missing_pct": round(float(df.loc[~present_mask, target].mean() * 100), 3)
        if (~present_mask).any() else None,
        "n_present": int(present_mask.sum()),
        "n_missing": int((~present_mask).sum()),
    }


def main() -> None:
    df = pd.read_csv(RAW / "train_transaction.csv")
    target = "isFraud"
    base_rate = df[target].mean() * 100

    results: dict = {"base_fraud_rate_pct": round(float(base_rate), 4), "n_rows": len(df)}

    named_cols = (
        ["TransactionID", "TransactionDT", "TransactionAmt", "ProductCD"]
        + [f"card{i}" for i in range(1, 7)]
        + ["addr1", "addr2", "dist1", "dist2", "P_emaildomain", "R_emaildomain"]
        + [f"C{i}" for i in range(1, 15)]
        + [f"D{i}" for i in range(1, 16)]
        + [f"M{i}" for i in range(1, 10)]
    )

    named_stats = {}
    for col in named_cols:
        entry = missingness_when_present_vs_absent(df, col, target)
        entry["dtype"] = str(df[col].dtype)
        if pd.api.types.is_numeric_dtype(df[col]):
            entry["nunique"] = int(df[col].nunique(dropna=True))
            entry["corr_with_target"] = round(float(df[col].corr(df[target])), 4) if df[col].notna().sum() > 1 else None
            entry["min"] = float(df[col].min()) if df[col].notna().any() else None
            entry["max"] = float(df[col].max()) if df[col].notna().any() else None
        else:
            entry["nunique"] = int(df[col].nunique(dropna=True))
            # fraud-rate spread across categories (max - min fraud rate among categories with >=50 rows)
            vc = df[col].value_counts()
            common_cats = vc[vc >= 50].index
            if len(common_cats) >= 2:
                rates = df[df[col].isin(common_cats)].groupby(col, observed=True)[target].mean() * 100
                entry["fraud_rate_spread_across_categories_pct"] = round(float(rates.max() - rates.min()), 3)
            else:
                entry["fraud_rate_spread_across_categories_pct"] = None
        named_stats[col] = entry

    results["named_columns"] = named_stats

    # V-block summary (V1-V339): missingness distribution + correlation distribution
    v_cols = [c for c in df.columns if c.startswith("V")]
    v_missing = df[v_cols].isna().mean() * 100
    v_corr = df[v_cols].corrwith(df[target]).abs()
    results["v_block_summary"] = {
        "n_columns": len(v_cols),
        "missingness_describe": v_missing.describe().to_dict(),
        "missingness_distinct_levels_top10": v_missing.round(3).value_counts().head(10).to_dict(),
        "abs_corr_with_target_describe": v_corr.describe().to_dict(),
        "top10_by_abs_corr": v_corr.sort_values(ascending=False).head(10).round(4).to_dict(),
        "n_cols_missingness_gt_80pct": int((v_missing > 80).sum()),
        "n_cols_missingness_lt_20pct": int((v_missing < 20).sum()),
    }

    # identity table summary (real, but only ~24% coverage)
    identity = pd.read_csv(RAW / "train_identity.csv")
    merged = df[["TransactionID", target]].merge(identity, on="TransactionID", how="left")
    merged["has_identity"] = merged["DeviceType"].notna() | merged["id_01"].notna()
    id_cols = [c for c in identity.columns if c != "TransactionID"]
    id_missing = identity[id_cols].isna().mean() * 100
    results["identity_summary"] = {
        "join_rate_pct": round(float((df["TransactionID"].isin(identity["TransactionID"])).mean() * 100), 3),
        "fraud_rate_with_identity_pct": round(float(merged.loc[merged["has_identity"], target].mean() * 100), 3),
        "fraud_rate_without_identity_pct": round(float(merged.loc[~merged["has_identity"], target].mean() * 100), 3),
        "device_type_fraud_rates": (
            merged.groupby("DeviceType", observed=True)[target].mean().mul(100).round(3).to_dict()
        ),
        "id_block_missingness_describe": id_missing.describe().to_dict(),
    }

    with OUT.open("w") as f:
        json.dump(results, f, indent=2, default=str)

    print(json.dumps({k: v for k, v in results.items() if k != "named_columns"}, indent=2, default=str))
    print("\nNamed column stats (abbreviated) — full detail in", OUT)
    for col, entry in named_stats.items():
        print(f"  {col:20s} missing={entry['pct_missing']:6.2f}%  dtype={entry['dtype']:8s}  "
              f"nunique={entry.get('nunique')}")
    print(f"\nFull results written to {OUT}")


if __name__ == "__main__":
    main()
