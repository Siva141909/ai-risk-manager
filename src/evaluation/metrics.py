"""Phase 2B/2C/2L — shared classification metrics.

One place for every metric reported across baselines (rules, Logistic
Regression, XGBoost) so RULES vs LR vs XGBoost are compared apples-to-apples
(Phase 2L: "do not cherry-pick metrics").
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def classification_metrics(y_true: pd.Series, y_pred_binary: np.ndarray, y_score: np.ndarray | None = None) -> dict:
    """Precision/recall/F1/confusion matrix, plus PR-AUC/ROC-AUC if a
    continuous score is given (undefined for a pure binary rule output)."""
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred_binary, labels=[0, 1]).ravel()

    metrics = {
        "precision": round(float(precision_score(y_true, y_pred_binary, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred_binary, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred_binary, zero_division=0)), 4),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "n_flagged": int(y_pred_binary.sum()),
        "n_total": int(len(y_true)),
        "n_actual_fraud": int(y_true.sum()),
    }

    if y_score is not None:
        metrics["pr_auc"] = round(float(average_precision_score(y_true, y_score)), 4)
        metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_score)), 4)
        metrics["brier_score"] = round(float(brier_score_loss(y_true, y_score)), 4)

    return metrics


def metrics_by_slice(
    y_true: pd.Series, y_score: np.ndarray, threshold: float, slice_series: pd.Series, min_slice_size: int = 30
) -> dict:
    """PR-AUC/precision/recall broken out per value of slice_series
    (e.g. amount bucket, temporal quarter) — Phase 2L's "report performance
    by ... slice" requirement. Slices smaller than min_slice_size are
    skipped (too few rows for a stable estimate) rather than silently reported.
    """
    y_pred = (y_score >= threshold).astype(int)
    results = {}
    for slice_value in sorted(slice_series.dropna().unique(), key=str):
        mask = (slice_series == slice_value).values
        n = int(mask.sum())
        if n < min_slice_size:
            results[str(slice_value)] = {"n": n, "note": f"skipped — fewer than {min_slice_size} rows"}
            continue
        y_true_s = y_true[mask]
        if y_true_s.nunique() < 2:
            results[str(slice_value)] = {
                "n": n,
                "fraud_rate_pct": round(float(y_true_s.mean() * 100), 3),
                "note": "skipped — single class present, PR-AUC undefined",
            }
            continue
        m = classification_metrics(y_true_s, y_pred[mask], y_score[mask])
        m["n"] = n
        m["fraud_rate_pct"] = round(float(y_true_s.mean() * 100), 3)
        results[str(slice_value)] = m
    return results
