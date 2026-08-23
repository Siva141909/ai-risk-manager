"""Phase 2B/2C/2F — train and save all three baselines.

Loads the persisted feature matrix (scripts/prepare_features.py must
have been run first), fits:
  1. RULES (src/models/baseline_rules.py) — thresholds fit on TRAIN only
  2. Logistic Regression — fit on TRAIN, class_weight='balanced'
  3. XGBoost — fit on TRAIN with early stopping on VALIDATION

Also runs the Phase 2F ablation: does including customer_proxy-based
historical features (cust_*) actually improve XGBoost's VALIDATION
PR-AUC over card1-based features alone? Reported and acted on — if they
hurt or are neutral, they are dropped from the final feature set, per
Phase 2F's explicit instruction.

The TEST split is never touched in this script — only train/validation.
Final test-set evaluation happens in scripts/evaluate_baseline.py, once.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from src.config import get_seed
from src.evaluation.cost import fit_cost_model
from src.evaluation.metrics import classification_metrics
from src.features.leakage_guard import assert_no_leakage
from src.models.baseline_rules import apply_rules, fit_rule_thresholds, rule_contribution_summary
from src.models.logistic_regression import fit_logistic_regression
from src.models.logistic_regression import predict_proba as lr_predict_proba
from src.models.xgboost_model import XGBParams, fit_xgboost
from src.models.xgboost_model import predict_proba as xgb_predict_proba

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FEATURES_PARQUET = PROJECT_ROOT / "data" / "processed" / "features.parquet"
OUT_DIR = PROJECT_ROOT / "data" / "processed"


def main() -> None:
    seed = get_seed()
    print(f"Loading {FEATURES_PARQUET} ...")
    df = pd.read_parquet(FEATURES_PARQUET)

    with (OUT_DIR / "features_metadata.json").open() as f:
        meta = json.load(f)
    feature_columns = meta["feature_columns"]

    train = df[df["split"] == "train"]
    val = df[df["split"] == "validation"]
    print(f"train={len(train)} val={len(val)} (test untouched in this script)")

    X_train, y_train = train[feature_columns], train["isFraud"]
    X_val, y_val = val[feature_columns], val["isFraud"]
    assert_no_leakage(X_train)
    assert_no_leakage(X_val)

    # ---- cost model (fit from TRAIN fraud amounts only) ----
    cost_model = fit_cost_model(y_train, train["TransactionAmt"])
    print(f"Cost model: {cost_model}")

    results: dict = {"seed": seed, "cost_model": cost_model.__dict__}

    # ---- BASELINE 1: RULES ----
    rule_thresholds = fit_rule_thresholds(train["TransactionAmt"])
    rules_val = apply_rules(val, rule_thresholds)
    rules_metrics = classification_metrics(y_val, rules_val["flagged"].to_numpy().astype(int))
    rules_metrics["rule_contributions"] = rule_contribution_summary(rules_val)
    results["rules"] = {"thresholds": rule_thresholds, "validation_metrics": rules_metrics}
    print(f"RULES validation: precision={rules_metrics['precision']} recall={rules_metrics['recall']} f1={rules_metrics['f1']}")

    # ---- BASELINE 2: Logistic Regression ----
    lr_model = fit_logistic_regression(X_train, y_train, seed)
    lr_val_scores = lr_predict_proba(lr_model, X_val)
    lr_metrics = classification_metrics(y_val, (lr_val_scores >= 0.5).astype(int), lr_val_scores)
    results["logistic_regression"] = {"validation_metrics": lr_metrics}
    print(f"LOGISTIC REGRESSION validation: pr_auc={lr_metrics['pr_auc']} roc_auc={lr_metrics['roc_auc']}")
    joblib.dump(lr_model, OUT_DIR / "model_logistic_regression.joblib")

    # ---- BASELINE 3: XGBoost (Phase 2F ablation: with vs without cust_* historical features) ----
    cust_feature_cols = [c for c in feature_columns if c.startswith("cust_")]
    non_cust_feature_cols = [c for c in feature_columns if not c.startswith("cust_")]
    print(f"Phase 2F ablation: {len(cust_feature_cols)} customer_proxy-derived features vs {len(non_cust_feature_cols)} without")

    xgb_with_cust = fit_xgboost(X_train, y_train, X_val, y_val, seed, XGBParams())
    scores_with_cust = xgb_predict_proba(xgb_with_cust, X_val)
    metrics_with_cust = classification_metrics(y_val, (scores_with_cust >= 0.5).astype(int), scores_with_cust)

    xgb_without_cust = fit_xgboost(
        X_train[non_cust_feature_cols], y_train, X_val[non_cust_feature_cols], y_val, seed, XGBParams()
    )
    scores_without_cust = xgb_predict_proba(xgb_without_cust, X_val[non_cust_feature_cols])
    metrics_without_cust = classification_metrics(y_val, (scores_without_cust >= 0.5).astype(int), scores_without_cust)

    print(f"XGBoost WITH customer_proxy features: val PR-AUC={metrics_with_cust['pr_auc']}")
    print(f"XGBoost WITHOUT customer_proxy features: val PR-AUC={metrics_without_cust['pr_auc']}")

    keep_cust_features = metrics_with_cust["pr_auc"] >= metrics_without_cust["pr_auc"]
    final_feature_columns = feature_columns if keep_cust_features else non_cust_feature_cols
    final_xgb_model = xgb_with_cust if keep_cust_features else xgb_without_cust
    final_xgb_val_scores = scores_with_cust if keep_cust_features else scores_without_cust
    final_xgb_metrics = metrics_with_cust if keep_cust_features else metrics_without_cust

    results["phase_2f_customer_proxy_ablation"] = {
        "with_customer_proxy_features_val_pr_auc": metrics_with_cust["pr_auc"],
        "without_customer_proxy_features_val_pr_auc": metrics_without_cust["pr_auc"],
        "decision": "keep" if keep_cust_features else "drop",
        "reasoning": (
            "customer_proxy-derived historical features measurably improved validation PR-AUC, kept"
            if keep_cust_features
            else "customer_proxy-derived historical features did not improve (or hurt) validation PR-AUC — "
            "dropped per Phase 2F's explicit instruction, consistent with docs/ENTITY_MODEL.md's caution "
            "that customer_proxy is a derived behavioral grouping, not verified identity"
        ),
    }
    results["xgboost"] = {
        "final_feature_count": len(final_feature_columns),
        "best_iteration": int(final_xgb_model.best_iteration),
        "validation_metrics": final_xgb_metrics,
    }
    print(f"XGBoost SELECTED: {'with' if keep_cust_features else 'without'} customer_proxy features, "
          f"val PR-AUC={final_xgb_metrics['pr_auc']}")

    final_xgb_model.save_model(str(OUT_DIR / "model_xgboost.json"))
    with (OUT_DIR / "final_feature_columns.json").open("w") as f:
        json.dump(final_feature_columns, f, indent=2)

    with (OUT_DIR / "baseline_training_results.json").open("w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\nModels and results saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
