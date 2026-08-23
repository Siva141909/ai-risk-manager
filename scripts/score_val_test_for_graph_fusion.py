"""Phase 3 prerequisite — calibrated ML scores for VAL+TEST, frozen from Phase 2.

The ML+graph fusion analysis (Phase 3H/3I/3J) needs a per-transaction ML
risk score. TRAIN rows are deliberately excluded here: the XGBoost model
was FIT on train, so a "score" on a train row would be in-sample and not
comparable to the honest out-of-sample scores on validation/test — using
it would silently bias the fusion analysis toward whatever the model
already memorized. This does not retrain or modify the Phase 2 model in
any way (the explicit Phase 3 experimental rule) — it only applies the
already-frozen model/calibrator to rows it has never seen the label for.
"""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
import xgboost as xgb

from src.models.thresholds import RiskThresholds, classify_risk_tiers
from src.models.xgboost_model import predict_proba as xgb_predict_proba

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED = PROJECT_ROOT / "data" / "processed"
OUT = PROCESSED / "val_test_ml_scores.parquet"


def main() -> None:
    df = pd.read_parquet(PROCESSED / "features.parquet")
    with (PROCESSED / "final_feature_columns.json").open() as f:
        feature_columns = json.load(f)
    with (PROCESSED / "risk_thresholds.json").open() as f:
        threshold_data = json.load(f)

    val_test = df[df["split"].isin(["validation", "test"])].copy()

    booster = xgb.Booster()
    booster.load_model(str(PROCESSED / "model_xgboost.json"))
    raw_scores = xgb_predict_proba(booster, val_test[feature_columns])

    calibrator = joblib.load(PROCESSED / f"calibrator_{threshold_data['calibrator']}.joblib")
    calibrated_scores = calibrator.transform(raw_scores)

    thresholds = RiskThresholds(**threshold_data["thresholds"])
    tiers = classify_risk_tiers(calibrated_scores, thresholds)

    out = val_test[["TransactionID", "split", "isFraud", "customer_proxy_id"]].copy()
    out["ml_score_raw"] = raw_scores
    out["ml_score_calibrated"] = calibrated_scores
    out["ml_risk_tier"] = tiers

    out.to_parquet(OUT, index=False)
    print(f"Scored {len(out)} rows (validation + test only, train excluded as in-sample).")
    print(out["ml_risk_tier"].value_counts())
    print(f"Written to {OUT}")


if __name__ == "__main__":
    main()
