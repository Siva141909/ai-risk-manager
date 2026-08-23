"""Phase 2L — final, one-time TEST-set evaluation.

This is the ONLY script in Phase 2 that touches the test split. Every
model, threshold, and calibrator used here was already fixed by
scripts/train_baseline.py and scripts/calibrate_and_threshold.py, both
of which used train/validation only. Running this script twice re-reads
the same fixed artifacts and produces the same numbers — it does not
retrain or re-tune anything.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import xgboost as xgb

from src.evaluation.cost import CostModel, total_cost
from src.evaluation.metrics import classification_metrics, metrics_by_slice
from src.models.baseline_rules import apply_rules
from src.models.explainability import explain_case, global_feature_importance
from src.models.logistic_regression import predict_proba as lr_predict_proba
from src.models.thresholds import RiskThresholds, classify_risk_tiers
from src.models.xgboost_model import predict_proba as xgb_predict_proba

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "processed"


def amount_bucket(amt: float) -> str:
    if amt < 25:
        return "0-25"
    if amt < 100:
        return "25-100"
    if amt < 250:
        return "100-250"
    if amt < 1000:
        return "250-1000"
    return "1000+"


def main() -> None:
    df = pd.read_parquet(OUT_DIR / "features.parquet")
    with (OUT_DIR / "features_metadata.json").open() as f:
        all_feature_columns = json.load(f)["feature_columns"]
    with (OUT_DIR / "final_feature_columns.json").open() as f:
        xgb_feature_columns = json.load(f)
    with (OUT_DIR / "baseline_training_results.json").open() as f:
        training_results = json.load(f)
    with (OUT_DIR / "risk_thresholds.json").open() as f:
        threshold_data = json.load(f)

    cost_model = CostModel(**training_results["cost_model"])

    test = df[df["split"] == "test"]
    print(f"TEST split: {len(test)} rows, fraud rate {test['isFraud'].mean()*100:.3f}% — evaluated ONCE, now.")

    y_test = test["isFraud"]
    results: dict = {}

    # ---- RULES ----
    rule_thresholds = training_results["rules"]["thresholds"]
    rules_test = apply_rules(test, rule_thresholds)
    rules_metrics = classification_metrics(y_test, rules_test["flagged"].to_numpy().astype(int))
    rules_metrics["cost"] = total_cost(rules_metrics["confusion_matrix"], cost_model)
    results["rules"] = rules_metrics
    print(f"RULES test: precision={rules_metrics['precision']} recall={rules_metrics['recall']} f1={rules_metrics['f1']}")

    # ---- Logistic Regression ----
    lr_model = joblib.load(OUT_DIR / "model_logistic_regression.joblib")
    lr_test_scores = lr_predict_proba(lr_model, test[all_feature_columns])
    lr_metrics = classification_metrics(y_test, (lr_test_scores >= 0.5).astype(int), lr_test_scores)
    results["logistic_regression"] = lr_metrics
    print(f"LOGISTIC REGRESSION test: pr_auc={lr_metrics['pr_auc']} roc_auc={lr_metrics['roc_auc']}")

    # ---- XGBoost (the selected primary baseline) ----
    booster = xgb.Booster()
    booster.load_model(str(OUT_DIR / "model_xgboost.json"))
    xgb_test_scores = xgb_predict_proba(booster, test[xgb_feature_columns])

    calibrator_name = threshold_data["calibrator"]
    calibrator = joblib.load(OUT_DIR / f"calibrator_{calibrator_name}.joblib")
    calibrated_test_scores = calibrator.transform(xgb_test_scores)

    xgb_metrics = classification_metrics(y_test, (xgb_test_scores >= 0.5).astype(int), xgb_test_scores)
    xgb_metrics_calibrated_scores = classification_metrics(
        y_test, (calibrated_test_scores >= threshold_data["thresholds"]["high"]).astype(int), calibrated_test_scores
    )
    thresholds = RiskThresholds(**threshold_data["thresholds"])
    tiers_test = classify_risk_tiers(calibrated_test_scores, thresholds)
    tier_counts_test = pd.Series(tiers_test).value_counts().to_dict()
    tier_fraud_rates_test = (
        pd.DataFrame({"tier": tiers_test, "isFraud": y_test.to_numpy()})
        .groupby("tier")["isFraud"].mean().mul(100).to_dict()
    )

    xgb_metrics["cost_at_high_threshold"] = total_cost(
        xgb_metrics_calibrated_scores["confusion_matrix"], cost_model
    )
    xgb_metrics["test_tier_counts"] = tier_counts_test
    xgb_metrics["test_tier_fraud_rate_pct"] = {k: round(v, 3) for k, v in tier_fraud_rates_test.items()}
    results["xgboost"] = xgb_metrics
    print(f"XGBOOST test: pr_auc={xgb_metrics['pr_auc']} roc_auc={xgb_metrics['roc_auc']}")
    print(f"XGBOOST test tier distribution: {tier_counts_test}")
    print(f"XGBOOST test tier fraud rates (%): {tier_fraud_rates_test}")

    # ---- Slice breakdowns (XGBoost, the selected baseline) — Phase 2L ----
    slices = {}
    slices["by_amount_bucket"] = metrics_by_slice(
        y_test, xgb_test_scores, 0.5, test["TransactionAmt"].apply(amount_bucket)
    )
    slices["by_identity_data_presence"] = metrics_by_slice(
        y_test, xgb_test_scores, 0.5, test["has_identity_data"].map({0: "no_identity_data", 1: "has_identity_data"})
    )
    n = len(test)
    temporal_quarter = pd.Series(pd.qcut(range(n), 4, labels=["Q1", "Q2", "Q3", "Q4"]), index=test.index)
    slices["by_temporal_quarter_within_test"] = metrics_by_slice(y_test, xgb_test_scores, 0.5, temporal_quarter)
    results["slices"] = slices

    # ---- Explainability (Phase 2K) ----
    importance = global_feature_importance(booster, top_n=20)
    results["feature_importance_top20"] = importance.to_dict(orient="records")

    example_fraud_idx = test[test["isFraud"] == 1].index[:2]
    example_explanations = []
    for idx in example_fraud_idx:
        row = test.loc[[idx], xgb_feature_columns]
        explanation = explain_case(booster, row, top_n=5)
        example_explanations.append(
            {"TransactionID": int(test.loc[idx, "TransactionID"]), "signals": explanation}
        )
    results["example_case_explanations"] = example_explanations

    with (OUT_DIR / "final_test_evaluation.json").open("w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nFinal test evaluation written to {OUT_DIR / 'final_test_evaluation.json'}")


if __name__ == "__main__":
    main()
