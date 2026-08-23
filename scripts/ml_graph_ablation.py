"""Phase 3H/3I/3J — ML + graph ablation, missed-by-ML analysis, quadrant matrix.

Operates on VALIDATION + TEST only (the only rows with honest
out-of-sample ML scores, scripts/score_val_test_for_graph_fusion.py).
Ground truth (original_isFraud, synthetic_entity_label, etc.) is used
ONLY for evaluation in this script — never passed to anything that would
stand in for the future agent (Phase 4+).

Does NOT retrain or modify the Phase 2 XGBoost model in any way (the
explicit Phase 3 experimental rule) — it only combines the model's
already-frozen predictions with graph structure.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score, precision_score, recall_score

from src.evaluation.cost import CostModel
from src.graph.signals import compute_customer_graph_signals
from src.models.baseline_rules import apply_rules

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT_ROOT / "data" / "processed"
FULL_DIR = PROJECT_ROOT / "data" / "synthetic" / "full"
OUT = PROCESSED / "ml_graph_ablation_report.json"

INVESTIGATION_COST_INR = 150.0  # matches src/evaluation/cost.py's illustrative per-case cost


def load_joined_data() -> pd.DataFrame:
    ml_scores = pd.read_parquet(PROCESSED / "val_test_ml_scores.parquet")
    features = pd.read_parquet(PROCESSED / "features.parquet")
    rule_cols = ["TransactionID", "cust_amount_zscore_vs_history", "cust_txn_count_prior_24h",
                 "card1_txn_count_prior_24h", "TransactionAmt"]
    features_sub = features[features["split"].isin(["validation", "test"])][rule_cols]

    synthetic = pd.read_parquet(FULL_DIR / "transactions.parquet")
    synthetic_cols = [
        "TransactionID", "synthetic_ring_id", "synthetic_abuse_type", "synthetic_ring_role",
        "legitimate_cluster_id", "legitimate_cluster_type", "synthetic_entity_label",
    ]

    df = ml_scores.merge(features_sub, on="TransactionID", how="left")
    df = df.merge(synthetic[synthetic_cols], on="TransactionID", how="left")

    print("Computing full-benchmark graph signals (Phase 3G)...")
    signals = compute_customer_graph_signals(synthetic)
    df = df.merge(signals, on="customer_proxy_id", how="left")
    df["graph_flagged"] = df["graph_flagged"].fillna(False)
    return df


def transaction_level_metrics(y_true: pd.Series, y_pred: np.ndarray, y_score: np.ndarray | None) -> dict:
    m = {
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "n_flagged": int(y_pred.sum()),
    }
    m["pr_auc"] = round(float(average_precision_score(y_true, y_score)), 4) if y_score is not None else None
    return m


def classify_missed_by_ml(row: pd.Series) -> str:
    """Phase 3I categorization — mutually exclusive, ground-truth-driven."""
    if row["synthetic_entity_label"] == "ring_member":
        return "genuine_additional_signal"
    if row["synthetic_entity_label"] in ("legitimate_shared_infra", "decoy_bystander"):
        return "legitimate_shared_infrastructure"
    if row["synthetic_entity_label"] == "normal" and row["isFraud"] == 1:
        return "model_blind_spot"
    if row["synthetic_entity_label"] == "normal" and row["isFraud"] == 0:
        return "synthetic_artifact"
    return "ambiguous"


def main() -> None:
    df = load_joined_data()
    print(f"Joined dataset: {len(df)} rows (validation+test)")

    fitted_thresholds = json.loads((PROCESSED / "baseline_training_results.json").read_text())["rules"]["thresholds"]
    rules_out = apply_rules(df, fitted_thresholds)
    df["rules_flagged"] = rules_out["flagged"]

    df["ml_flagged"] = df["ml_risk_tier"].isin(["HIGH", "CRITICAL"])
    df["flagged_A"] = df["rules_flagged"]
    df["flagged_B"] = df["rules_flagged"] | df["ml_flagged"]
    df["flagged_C"] = df["flagged_B"] | df["graph_flagged"]

    y_true = df["isFraud"]
    report: dict = {"n_rows": len(df)}

    report["A_rules_only"] = transaction_level_metrics(y_true, df["flagged_A"].to_numpy(), None)
    report["B_rules_plus_ml"] = transaction_level_metrics(
        y_true, df["flagged_B"].to_numpy(), df["ml_score_calibrated"].to_numpy()
    )
    report["C_rules_plus_ml_plus_graph"] = transaction_level_metrics(
        y_true, df["flagged_C"].to_numpy(), df["ml_score_calibrated"].to_numpy()
    )
    report["C_pr_auc_note"] = (
        "PR-AUC for B and C is identical: graph contributes a discrete community-membership "
        "flag, not a continuous ranking score, so it cannot change a rank-based metric. Its "
        "contribution shows up in the binary flagged-set metrics above and the incremental "
        "recall analysis below, not in PR-AUC."
    )

    # incremental contribution: transactions caught by C but NOT by B
    incremental_mask = df["flagged_C"] & ~df["flagged_B"]
    report["incremental_from_graph"] = {
        "n_additional_transactions_flagged": int(incremental_mask.sum()),
        "n_additional_true_fraud_caught": int((incremental_mask & (y_true == 1)).sum()),
        "n_additional_false_positives": int((incremental_mask & (y_true == 0)).sum()),
    }

    for stage, col in [("A_rules_only", "flagged_A"), ("B_rules_plus_ml", "flagged_B"), ("C_rules_plus_ml_plus_graph", "flagged_C")]:
        n_flagged = int(df[col].sum())
        report[stage]["operational"] = {
            "n_cases_generated": n_flagged,
            "estimated_analyst_workload_inr": round(n_flagged * INVESTIGATION_COST_INR, 2),
        }

    # ---- Phase 3I: missed-by-ML analysis ----
    missed_by_ml = df[(df["ml_risk_tier"].isin(["LOW", "MEDIUM"])) & (df["graph_flagged"])].copy()
    missed_by_ml["category"] = missed_by_ml.apply(classify_missed_by_ml, axis=1)
    category_counts = missed_by_ml["category"].value_counts().to_dict()
    report["missed_by_ml_analysis"] = {
        "n_total_missed_by_ml_but_graph_flagged": len(missed_by_ml),
        "category_counts": category_counts,
        "examples": missed_by_ml[
            ["TransactionID", "customer_proxy_id", "ml_risk_tier", "isFraud", "synthetic_entity_label", "category"]
        ].head(20).to_dict(orient="records"),
    }
    print(f"Missed-by-ML (ML low/medium, graph flagged): {len(missed_by_ml)} rows")
    print(f"  Category breakdown: {category_counts}")

    # ---- Phase 3J: quadrant matrix ----
    ml_high = df["ml_risk_tier"].isin(["HIGH", "CRITICAL"])
    graph_high = df["graph_flagged"]
    quadrants = {
        "A_ml_low_graph_low": ~ml_high & ~graph_high,
        "B_ml_low_graph_high": ~ml_high & graph_high,
        "C_ml_high_graph_low": ml_high & ~graph_high,
        "D_ml_high_graph_high": ml_high & graph_high,
    }
    quadrant_report = {}
    for name, mask in quadrants.items():
        n = int(mask.sum())
        quadrant_report[name] = {
            "n": n,
            "real_fraud_rate_pct": round(float(df.loc[mask, "isFraud"].mean() * 100), 3) if n else None,
            "ring_member_rate_pct": round(
                float((df.loc[mask, "synthetic_entity_label"] == "ring_member").mean() * 100), 3
            ) if n else None,
            "legitimate_shared_infra_rate_pct": round(
                float(df.loc[mask, "synthetic_entity_label"].isin(["legitimate_shared_infra", "decoy_bystander"]).mean() * 100), 3
            ) if n else None,
        }
    report["quadrant_matrix"] = quadrant_report
    print("Quadrant matrix:")
    for name, entry in quadrant_report.items():
        print(f"  {name}: {entry}")

    with OUT.open("w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nWritten to {OUT}")


if __name__ == "__main__":
    main()
