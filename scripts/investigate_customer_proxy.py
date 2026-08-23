"""Phase 1C — customer-proxy candidate investigation.

Read-only. Tests several candidate strategies for grouping IEEE-CIS
transactions into a synthetic "customer_proxy" entity, and measures
whether each candidate is defensible or misleading. This does NOT choose
a proxy because it produces a convenient graph — it measures evidence
and lets the evidence decide. See docs/ENTITY_MODEL.md for the write-up
and final decision this script's output feeds into.

Candidates tested:
  A. card1-card6 tuple (baseline — already known unsafe from docs/DATASET_AUDIT.md,
     included here for a side-by-side comparison, not as a live option)
  B. card1-card6 + addr1 + addr2
  C. card1-card6 + P_emaildomain
  D. card1-card6 + addr1 + P_emaildomain
  E. card1 + card2 + addr1 + P_emaildomain (drops card3/5/6, keeps the
     two highest-cardinality card fields only)
  F. card1-card6 narrowed by a 24h time window (same tuple AND within the
     same rolling day-bucket) — tests whether temporal narrowing alone
     fixes the mega-cluster problem
  G. Identity-linked subset only: card1-card6 + DeviceInfo (only defined
     for the ~24% of rows with a matching identity record)
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
OUT = Path(__file__).resolve().parent.parent / "scratch_customer_proxy_output.json"

MEGA_CLUSTER_THRESHOLD = 500  # a cluster this size cannot plausibly be one customer


def combo_key(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    return df[cols].astype("string").fillna("NA").agg("|".join, axis=1)


def evaluate_candidate(name: str, df: pd.DataFrame, key: pd.Series) -> dict:
    n_rows = len(df)
    sizes = key.value_counts()
    n_unique = len(sizes)
    singleton_rate = (sizes == 1).sum() / n_unique if n_unique else 0.0
    mega_clusters = sizes[sizes >= MEGA_CLUSTER_THRESHOLD]
    mega_cluster_row_share = mega_clusters.sum() / n_rows if n_rows else 0.0

    # fraud rate inside top 5 largest clusters vs. overall base rate
    base_rate = df["isFraud"].mean() * 100
    top5 = sizes.head(5)
    top5_fraud_rates = []
    for cluster_key, size in top5.items():
        mask = key == cluster_key
        top5_fraud_rates.append(
            {
                "size": int(size),
                "fraud_rate_pct": float(df.loc[mask, "isFraud"].mean() * 100),
            }
        )

    # temporal persistence: for clusters with size > 1, span in days between
    # first and last transaction in the cluster
    tmp = pd.DataFrame({"key": key, "dt": df["TransactionDT"]})
    grouped = tmp.groupby("key")["dt"].agg(["min", "max", "count"])
    multi = grouped[grouped["count"] > 1].copy()
    multi["span_days"] = (multi["max"] - multi["min"]) / 86400
    span_stats = {
        "n_multi_member_clusters": int(len(multi)),
        "mean_span_days": float(multi["span_days"].mean()) if len(multi) else None,
        "median_span_days": float(multi["span_days"].median()) if len(multi) else None,
    }

    result = {
        "candidate": name,
        "n_rows": n_rows,
        "n_unique_clusters": int(n_unique),
        "singleton_rate_pct": round(float(singleton_rate) * 100, 3),
        "mega_cluster_threshold": MEGA_CLUSTER_THRESHOLD,
        "n_mega_clusters": int(len(mega_clusters)),
        "mega_cluster_row_share_pct": round(float(mega_cluster_row_share) * 100, 3),
        "largest_cluster_size": int(sizes.max()) if n_unique else 0,
        "base_fraud_rate_pct": round(float(base_rate), 3),
        "top5_cluster_fraud_rates": top5_fraud_rates,
        "cluster_size_describe": {k: float(v) for k, v in sizes.describe().to_dict().items()},
        "temporal_persistence": span_stats,
    }
    print(f"\n=== {name} ===")
    print(json.dumps(result, indent=2))
    return result


def main() -> None:
    cols = [
        "TransactionID", "isFraud", "TransactionDT",
        "card1", "card2", "card3", "card4", "card5", "card6",
        "addr1", "addr2", "P_emaildomain",
    ]
    df = pd.read_csv(RAW / "train_transaction.csv", usecols=cols)

    results = []

    results.append(evaluate_candidate("A_card1_6_baseline", df, combo_key(df, ["card1", "card2", "card3", "card4", "card5", "card6"])))
    results.append(evaluate_candidate("B_card1_6_plus_addr", df, combo_key(df, ["card1", "card2", "card3", "card4", "card5", "card6", "addr1", "addr2"])))
    results.append(evaluate_candidate("C_card1_6_plus_email", df, combo_key(df, ["card1", "card2", "card3", "card4", "card5", "card6", "P_emaildomain"])))
    results.append(evaluate_candidate("D_card1_6_plus_addr_plus_email", df, combo_key(df, ["card1", "card2", "card3", "card4", "card5", "card6", "addr1", "P_emaildomain"])))
    results.append(evaluate_candidate("E_card1_2_plus_addr_plus_email", df, combo_key(df, ["card1", "card2", "addr1", "P_emaildomain"])))

    # F: time-windowed narrowing — same card1-6 tuple AND same 24h bucket
    day_bucket = (df["TransactionDT"] // 86400).astype("string")
    card_key = combo_key(df, ["card1", "card2", "card3", "card4", "card5", "card6"])
    windowed_key = card_key + "|" + day_bucket
    results.append(evaluate_candidate("F_card1_6_24h_window", df, windowed_key))

    # G: identity-linked subset only (card1-6 + DeviceInfo), evaluated on the subset
    identity = pd.read_csv(RAW / "train_identity.csv", usecols=["TransactionID", "DeviceInfo"])
    df_id = df.merge(identity, on="TransactionID", how="inner")
    device_key = combo_key(df_id, ["card1", "card2", "card3", "card4", "card5", "card6", "DeviceInfo"])
    results.append(evaluate_candidate("G_card1_6_plus_deviceinfo_identity_subset", df_id, device_key))

    with open(OUT, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nFull results written to {OUT}")


if __name__ == "__main__":
    main()
