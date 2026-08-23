"""Read-only IEEE-CIS dataset audit.

Reads the raw CSVs from data/raw/, computes and prints evidence-based
statistics (shape, dtypes, missingness, target distribution, temporal
range, candidate graph-anchor cardinality, identity join coverage,
train/test schema diff, correlation-based leakage scan). Writes nothing
back to data/raw/ — strictly read-only.

This is inspection tooling, not the ingestion/feature pipeline (Phase 1+).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT = Path(__file__).resolve().parent.parent / "scratch_audit_output.json"


def section(title: str) -> None:
    print(f"\n{'=' * 80}\n{title}\n{'=' * 80}")


def dtype_summary(df: pd.DataFrame) -> dict:
    return df.dtypes.astype(str).value_counts().to_dict()


def missingness(df: pd.DataFrame) -> pd.Series:
    return (df.isna().mean() * 100).round(3).sort_values(ascending=False)


results: dict = {}

section("LOADING train_transaction.csv")
train_txn = pd.read_csv(RAW / "train_transaction.csv")
print(train_txn.shape)

section("LOADING train_identity.csv")
train_id = pd.read_csv(RAW / "train_identity.csv")
print(train_id.shape)

section("LOADING test_transaction.csv")
test_txn = pd.read_csv(RAW / "test_transaction.csv")
print(test_txn.shape)

section("LOADING test_identity.csv")
test_id = pd.read_csv(RAW / "test_identity.csv")
print(test_id.shape)

section("LOADING sample_submission.csv")
sample_sub = pd.read_csv(RAW / "sample_submission.csv")
print(sample_sub.shape)

# ---------------------------------------------------------------------------
section("SHAPES")
shapes = {
    "train_transaction": train_txn.shape,
    "train_identity": train_id.shape,
    "test_transaction": test_txn.shape,
    "test_identity": test_id.shape,
    "sample_submission": sample_sub.shape,
}
print(shapes)
results["shapes"] = {k: list(v) for k, v in shapes.items()}

# ---------------------------------------------------------------------------
section("DTYPE SUMMARY")
results["dtypes"] = {}
for name, df in [
    ("train_transaction", train_txn),
    ("train_identity", train_id),
    ("test_transaction", test_txn),
    ("test_identity", test_id),
]:
    ds = dtype_summary(df)
    print(name, ds)
    results["dtypes"][name] = ds

# ---------------------------------------------------------------------------
section("TARGET DISTRIBUTION (train_transaction.isFraud)")
target_counts = train_txn["isFraud"].value_counts().to_dict()
target_pct = (train_txn["isFraud"].value_counts(normalize=True) * 100).round(4).to_dict()
print("counts:", target_counts)
print("pct:", target_pct)
results["target_distribution"] = {"counts": target_counts, "pct": target_pct}

# ---------------------------------------------------------------------------
section("TRANSACTIONID RANGE / OVERLAP")
train_id_range = (int(train_txn.TransactionID.min()), int(train_txn.TransactionID.max()))
test_id_range = (int(test_txn.TransactionID.min()), int(test_txn.TransactionID.max()))
print("train TransactionID range:", train_id_range)
print("test TransactionID range:", test_id_range)
overlap = set(train_txn.TransactionID).intersection(set(test_txn.TransactionID))
print("TransactionID overlap between train/test:", len(overlap))
results["transaction_id_range"] = {
    "train": train_id_range,
    "test": test_id_range,
    "overlap_count": len(overlap),
}

# ---------------------------------------------------------------------------
section("TEMPORAL FIELD: TransactionDT")
dt_train_min, dt_train_max = train_txn.TransactionDT.min(), train_txn.TransactionDT.max()
dt_test_min, dt_test_max = test_txn.TransactionDT.min(), test_txn.TransactionDT.max()
print("train TransactionDT range (seconds):", dt_train_min, dt_train_max)
print("train range in days:", (dt_train_max - dt_train_min) / 86400)
print("test TransactionDT range (seconds):", dt_test_min, dt_test_max)
print("test range in days:", (dt_test_max - dt_test_min) / 86400)
print("gap between train max and test min (days):", (dt_test_min - dt_train_max) / 86400)
# Is TransactionID monotonically related to TransactionDT (i.e. is row order == time order)?
is_dt_sorted_train = train_txn.TransactionDT.is_monotonic_increasing
is_id_sorted_train = train_txn.TransactionID.is_monotonic_increasing
corr_id_dt_train = train_txn.TransactionID.corr(train_txn.TransactionDT)
print("train TransactionDT monotonic increasing by row order:", is_dt_sorted_train)
print("train TransactionID monotonic increasing by row order:", is_id_sorted_train)
print("train corr(TransactionID, TransactionDT):", corr_id_dt_train)
results["temporal"] = {
    "train_dt_min": float(dt_train_min),
    "train_dt_max": float(dt_train_max),
    "train_range_days": float((dt_train_max - dt_train_min) / 86400),
    "test_dt_min": float(dt_test_min),
    "test_dt_max": float(dt_test_max),
    "test_range_days": float((dt_test_max - dt_test_min) / 86400),
    "gap_days": float((dt_test_min - dt_train_max) / 86400),
    "train_dt_monotonic": bool(is_dt_sorted_train),
    "train_id_monotonic": bool(is_id_sorted_train),
    "corr_id_dt_train": float(corr_id_dt_train),
}

# ---------------------------------------------------------------------------
section("MISSINGNESS: train_transaction (top 20 + summary stats)")
miss_train_txn = missingness(train_txn)
print(miss_train_txn.head(20))
print("summary stats over all columns:")
print(miss_train_txn.describe())
n_cols_0pct = (miss_train_txn == 0).sum()
n_cols_gt50pct = (miss_train_txn > 50).sum()
n_cols_gt90pct = (miss_train_txn > 90).sum()
print(f"cols with 0% missing: {n_cols_0pct}")
print(f"cols with >50% missing: {n_cols_gt50pct}")
print(f"cols with >90% missing: {n_cols_gt90pct}")
results["missingness_train_transaction"] = {
    "top20": miss_train_txn.head(20).to_dict(),
    "describe": miss_train_txn.describe().to_dict(),
    "n_cols_0pct": int(n_cols_0pct),
    "n_cols_gt50pct": int(n_cols_gt50pct),
    "n_cols_gt90pct": int(n_cols_gt90pct),
}

section("MISSINGNESS: key named (non-V) columns in train_transaction")
named_cols = [
    "TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD",
    "card1", "card2", "card3", "card4", "card5", "card6",
    "addr1", "addr2", "dist1", "dist2",
    "P_emaildomain", "R_emaildomain",
] + [f"C{i}" for i in range(1, 15)] + [f"D{i}" for i in range(1, 16)] + [f"M{i}" for i in range(1, 10)]
named_cols = [c for c in named_cols if c in train_txn.columns]
miss_named = missingness(train_txn[named_cols])
print(miss_named)
results["missingness_named_columns"] = miss_named.to_dict()

section("MISSINGNESS: train_identity")
miss_train_id = missingness(train_id)
print(miss_train_id)
results["missingness_train_identity"] = miss_train_id.to_dict()

# ---------------------------------------------------------------------------
section("CARDINALITY: candidate graph-anchor fields (train_transaction)")
anchor_cols = ["card1", "card2", "card3", "card4", "card5", "card6",
               "addr1", "addr2", "P_emaildomain", "R_emaildomain", "ProductCD"]
anchor_card = {}
for c in anchor_cols:
    if c in train_txn.columns:
        nun = int(train_txn[c].nunique(dropna=True))
        anchor_card[c] = nun
        print(f"{c}: nunique={nun}")
results["anchor_cardinality_transaction"] = anchor_card

section("CARDINALITY: card1-6 combined tuple (payment-instrument proxy)")
card_cols = ["card1", "card2", "card3", "card4", "card5", "card6"]
combo = train_txn[card_cols].astype("string").fillna("NA").agg("|".join, axis=1)
n_combo = combo.nunique()
n_rows = len(train_txn)
print(f"unique card1-6 combinations: {n_combo} out of {n_rows} rows")
vc = combo.value_counts()
print("top 10 combo frequencies:")
print(vc.head(10))
print("combos appearing more than once:", (vc > 1).sum(), "covering", int(vc[vc > 1].sum()), "rows")
results["card_combo_cardinality"] = {
    "n_unique_combos": int(n_combo),
    "n_rows": int(n_rows),
    "combos_appearing_gt1": int((vc > 1).sum()),
    "rows_covered_by_repeat_combos": int(vc[vc > 1].sum()),
}

section("CARDINALITY: identity fields (train_identity)")
id_anchor_cols = ["DeviceType", "DeviceInfo", "id_30", "id_31", "id_33"]
id_card = {}
for c in id_anchor_cols:
    if c in train_id.columns:
        nun = int(train_id[c].nunique(dropna=True))
        id_card[c] = nun
        print(f"{c}: nunique={nun}")
results["anchor_cardinality_identity"] = id_card

# ---------------------------------------------------------------------------
section("IDENTITY JOIN COVERAGE")
train_join_ids = set(train_id.TransactionID)
train_txn_ids = set(train_txn.TransactionID)
train_covered = len(train_txn_ids.intersection(train_join_ids))
print(f"train: {train_covered} / {len(train_txn_ids)} transactions have a matching identity row "
      f"({100*train_covered/len(train_txn_ids):.2f}%)")

test_join_ids = set(test_id.TransactionID)
test_txn_ids = set(test_txn.TransactionID)
test_covered = len(test_txn_ids.intersection(test_join_ids))
print(f"test: {test_covered} / {len(test_txn_ids)} transactions have a matching identity row "
      f"({100*test_covered/len(test_txn_ids):.2f}%)")

# fraud rate among transactions WITH identity vs WITHOUT (train only, since only train has isFraud)
train_txn_with_id = train_txn[train_txn.TransactionID.isin(train_join_ids)]
train_txn_without_id = train_txn[~train_txn.TransactionID.isin(train_join_ids)]
fraud_rate_with_id = train_txn_with_id.isFraud.mean() * 100
fraud_rate_without_id = train_txn_without_id.isFraud.mean() * 100
print(f"fraud rate WITH identity match: {fraud_rate_with_id:.3f}%  (n={len(train_txn_with_id)})")
print(f"fraud rate WITHOUT identity match: {fraud_rate_without_id:.3f}%  (n={len(train_txn_without_id)})")
results["identity_join_coverage"] = {
    "train_covered": train_covered,
    "train_total": len(train_txn_ids),
    "train_pct": 100 * train_covered / len(train_txn_ids),
    "test_covered": test_covered,
    "test_total": len(test_txn_ids),
    "test_pct": 100 * test_covered / len(test_txn_ids),
    "fraud_rate_with_identity_pct": float(fraud_rate_with_id),
    "fraud_rate_without_identity_pct": float(fraud_rate_without_id),
}

# ---------------------------------------------------------------------------
section("DeviceInfo / DeviceType QUALITY (train_identity)")
print("DeviceType value_counts:")
print(train_id.DeviceType.value_counts(dropna=False).head(10))
print("\nDeviceInfo value_counts top 20:")
print(train_id.DeviceInfo.value_counts(dropna=False).head(20))
print("\nDeviceInfo missing pct:", train_id.DeviceInfo.isna().mean() * 100)
results["device_info"] = {
    "device_type_counts": train_id.DeviceType.value_counts(dropna=False).head(10).to_dict(),
    "device_info_top20": train_id.DeviceInfo.value_counts(dropna=False).head(20).to_dict(),
    "device_info_missing_pct": float(train_id.DeviceInfo.isna().mean() * 100),
}

# ---------------------------------------------------------------------------
section("TRAIN vs TEST SCHEMA DIFF: transaction files")
train_txn_cols = set(train_txn.columns)
test_txn_cols = set(test_txn.columns)
print("in train_transaction but not test_transaction:", train_txn_cols - test_txn_cols)
print("in test_transaction but not train_transaction:", test_txn_cols - train_txn_cols)
results["schema_diff_transaction"] = {
    "train_only": sorted(train_txn_cols - test_txn_cols),
    "test_only": sorted(test_txn_cols - train_txn_cols),
}

section("TRAIN vs TEST SCHEMA DIFF: identity files")
train_id_cols = set(train_id.columns)
test_id_cols = set(test_id.columns)
print("in train_identity but not test_identity (raw names):", train_id_cols - test_id_cols)
print("in test_identity but not train_identity (raw names):", test_id_cols - train_id_cols)
# normalize hyphens to underscores and re-check
test_id_cols_normalized = {c.replace("-", "_") for c in test_id_cols}
print("after normalizing '-' to '_' in test_identity column names, diff:",
      train_id_cols - test_id_cols_normalized, test_id_cols_normalized - train_id_cols)
results["schema_diff_identity"] = {
    "train_only_raw": sorted(train_id_cols - test_id_cols),
    "test_only_raw": sorted(test_id_cols - train_id_cols),
    "diff_after_normalizing_hyphen": sorted(train_id_cols - test_id_cols_normalized),
}

# ---------------------------------------------------------------------------
section("POTENTIAL TARGET LEAKAGE: correlation with isFraud")
numeric_cols = train_txn.select_dtypes(include="number").columns.tolist()
numeric_cols = [c for c in numeric_cols if c not in ("isFraud", "TransactionID")]
corrs = train_txn[numeric_cols].corrwith(train_txn["isFraud"]).abs().sort_values(ascending=False)
print("Top 15 |correlation| with isFraud:")
print(corrs.head(15))
results["leakage_top_correlations"] = corrs.head(15).round(4).to_dict()

# Check for any column that is a near-perfect predictor (duplicate of target)
suspicious = corrs[corrs > 0.5]
print("\nColumns with |corr| > 0.5 (suspicious):", suspicious.to_dict())
results["leakage_suspicious_gt_0.5"] = suspicious.round(4).to_dict()

# ---------------------------------------------------------------------------
section("EXACT FILE ROW COUNTS (post-load, minus header)")
row_counts = {
    "train_transaction": len(train_txn),
    "train_identity": len(train_id),
    "test_transaction": len(test_txn),
    "test_identity": len(test_id),
    "sample_submission": len(sample_sub),
}
print(row_counts)
results["row_counts"] = row_counts

with open(OUT, "w") as f:
    json.dump(results, f, indent=2, default=str)
print(f"\nFull structured results written to {OUT}")
