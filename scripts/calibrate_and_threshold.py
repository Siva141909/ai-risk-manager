"""Phase 2H/2I — calibration comparison + risk-tier threshold selection.

Uses the SELECTED XGBoost model (scripts/train_baseline.py's output —
already decided the Phase 2F customer_proxy-feature question) and
VALIDATION predictions only. Test is never touched here.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb

from src.evaluation.cost import fit_cost_model
from src.models.calibration import compare_calibration, fit_calibrators
from src.models.thresholds import classify_risk_tiers, select_thresholds
from src.models.xgboost_model import predict_proba as xgb_predict_proba

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT_ROOT / "data" / "processed"


def main() -> None:
    df = pd.read_parquet(OUT_DIR / "features.parquet")
    with (OUT_DIR / "final_feature_columns.json").open() as f:
        feature_columns = json.load(f)

    train = df[df["split"] == "train"]
    val = df[df["split"] == "validation"]

    booster = xgb.Booster()
    booster.load_model(str(OUT_DIR / "model_xgboost.json"))

    X_val, y_val = val[feature_columns], val["isFraud"]
    val_scores = xgb_predict_proba(booster, X_val)

    # ---- Phase 2H: calibration, validation only ----
    calibrators = fit_calibrators(val_scores, y_val)
    calibration_report = compare_calibration(val_scores, y_val, calibrators)

    brier_scores = {name: entry["brier_score"] for name, entry in calibration_report.items()}
    best_calibrator_name = min(brier_scores, key=brier_scores.get)
    print(f"Calibration Brier scores: {brier_scores}")
    print(f"Selected calibrator: {best_calibrator_name}")

    joblib.dump(calibrators["platt"], OUT_DIR / "calibrator_platt.joblib")
    joblib.dump(calibrators["isotonic"], OUT_DIR / "calibrator_isotonic.joblib")
    with (OUT_DIR / "calibration_comparison.json").open("w") as f:
        json.dump(
            {"brier_scores": brier_scores, "selected": best_calibrator_name, "detail": calibration_report},
            f, indent=2,
        )

    # calibrated scores used for threshold selection — the risk scores
    # downstream systems will actually see (design doc Section 11:
    # "the downstream cost model needs probabilities, not just a ranking")
    calibrated_val_scores = calibrators[best_calibrator_name].transform(val_scores)

    # ---- Phase 2I: cost model + threshold selection, validation only ----
    cost_model = fit_cost_model(train["isFraud"], train["TransactionAmt"])
    thresholds = select_thresholds(y_val, calibrated_val_scores, cost_model)
    print(f"Selected thresholds: {thresholds}")

    tiers = classify_risk_tiers(calibrated_val_scores, thresholds)
    tier_counts = pd.Series(tiers).value_counts().to_dict()
    tier_fraud_rates = (
        pd.DataFrame({"tier": tiers, "isFraud": y_val.to_numpy()}).groupby("tier")["isFraud"].mean().mul(100).to_dict()
    )
    print(f"Validation tier distribution: {tier_counts}")
    print(f"Validation fraud rate by tier (%): {tier_fraud_rates}")

    with (OUT_DIR / "risk_thresholds.json").open("w") as f:
        json.dump(
            {
                "thresholds": thresholds.__dict__,
                "calibrator": best_calibrator_name,
                "validation_tier_counts": tier_counts,
                "validation_tier_fraud_rate_pct": {k: round(v, 3) for k, v in tier_fraud_rates.items()},
            },
            f, indent=2,
        )

    print(f"\nArtifacts saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
