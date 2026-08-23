"""Phase 2H — probability calibration.

The downstream system needs interpretable risk scores (design doc
Section 11: "the downstream cost model needs probabilities, not just a
ranking"), not merely good ranking performance. Both Platt scaling
(sigmoid) and isotonic regression are fit and compared here — on
VALIDATION predictions only, never train (which would let the
calibrator memorize the same rows the model was fit on) and never test
(reserved for final evaluation).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss


class PlattCalibrator:
    """Platt scaling: a 1-D logistic regression of y on the raw score."""

    def __init__(self) -> None:
        self._lr = LogisticRegression()

    def fit(self, scores: np.ndarray, y: pd.Series) -> "PlattCalibrator":
        self._lr.fit(scores.reshape(-1, 1), y)
        return self

    def transform(self, scores: np.ndarray) -> np.ndarray:
        return self._lr.predict_proba(scores.reshape(-1, 1))[:, 1]


class IsotonicCalibrator:
    def __init__(self) -> None:
        self._iso = IsotonicRegression(out_of_bounds="clip")

    def fit(self, scores: np.ndarray, y: pd.Series) -> "IsotonicCalibrator":
        self._iso.fit(scores, y)
        return self

    def transform(self, scores: np.ndarray) -> np.ndarray:
        return self._iso.predict(scores)


def fit_calibrators(val_scores: np.ndarray, y_val: pd.Series) -> dict:
    return {
        "platt": PlattCalibrator().fit(val_scores, y_val),
        "isotonic": IsotonicCalibrator().fit(val_scores, y_val),
    }


def compare_calibration(
    val_scores: np.ndarray, y_val: pd.Series, calibrators: dict, n_bins: int = 10
) -> dict:
    """Brier score + reliability-curve bins for the raw score and each
    calibrator, evaluated on the SAME validation set used to fit them
    (a held-out test-set comparison happens separately at final
    evaluation time, not here) — this function's job is to pick which
    calibrator to use, using validation only, per Phase 2H."""
    results = {}

    raw_brier = brier_score_loss(y_val, val_scores)
    raw_frac_pos, raw_mean_pred = calibration_curve(y_val, val_scores, n_bins=n_bins, strategy="quantile")
    results["raw"] = {
        "brier_score": round(float(raw_brier), 5),
        "reliability_curve": {
            "mean_predicted": [round(float(x), 4) for x in raw_mean_pred],
            "fraction_positive": [round(float(x), 4) for x in raw_frac_pos],
        },
    }

    for name, calibrator in calibrators.items():
        calibrated = calibrator.transform(val_scores)
        brier = brier_score_loss(y_val, calibrated)
        frac_pos, mean_pred = calibration_curve(y_val, calibrated, n_bins=n_bins, strategy="quantile")
        results[name] = {
            "brier_score": round(float(brier), 5),
            "reliability_curve": {
                "mean_predicted": [round(float(x), 4) for x in mean_pred],
                "fraction_positive": [round(float(x), 4) for x in frac_pos],
            },
        }

    return results
