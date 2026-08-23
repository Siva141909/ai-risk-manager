"""Phase 2B/2I — illustrative financial cost model.

Matches the design doc's Section 24 approach: explicit, illustrative ₹
costs stated as assumptions for demonstration, not Razorpay's real cost
structure. False-negative cost is estimated from the mean fraud
transaction amount (fit from TRAIN only, never validation/test, to avoid
leaking evaluation-split information into a "cost" that then influences
threshold selection). False-positive cost is a flat illustrative analyst
investigation cost.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class CostModel:
    false_positive_cost_inr: float  # analyst investigation time + customer friction, illustrative
    false_negative_cost_inr: float  # mean fraud transaction amount lost, fit from TRAIN only
    investigation_cost_inr: float = 0.0  # additional per-flagged-case cost (e.g. agent/analyst time), illustrative


def fit_cost_model(
    train_y: pd.Series,
    train_amounts: pd.Series,
    false_positive_cost_inr: float = 500.0,
    investigation_cost_inr: float = 150.0,
    fraud_cost_multiplier: float = 10.0,
) -> CostModel:
    """Fit false_negative_cost from TRAIN fraud transaction amounts only.

    **Documented assumption, not a silent default:** false_negative_cost
    is `mean_fraud_amount * fraud_cost_multiplier`, not the raw mean
    fraud amount. Investigated directly (docs/RISK_THRESHOLD_POLICY.md
    §3): with multiplier=1 (the transaction's own face value only), the
    cost-minimizing threshold is degenerate — 0.975, capturing only
    3.8% of validation fraud — because the mean fraud amount here
    (₹145.64) is far cheaper than a single false-positive investigation
    (₹650), so pure per-transaction cost minimization rationally decides
    "don't bother flagging anything." A single fraudulent transaction's
    real cost is not just its face value — chargeback fees, reputational
    damage, and enabling repeat abuse by the same actor all compound
    beyond the one transaction. `fraud_cost_multiplier=10` is an
    explicit, illustrative correction for that (a common rule-of-thumb
    range in fraud-cost literature is 3-15x face value depending on
    merchant category) — swept and reported at several values in
    docs/RISK_THRESHOLD_POLICY.md §3, not asserted as precisely correct.
    """
    fraud_amounts = train_amounts[train_y == 1]
    fn_cost = float(fraud_amounts.mean()) * fraud_cost_multiplier if len(fraud_amounts) else 0.0
    return CostModel(
        false_positive_cost_inr=false_positive_cost_inr,
        false_negative_cost_inr=round(fn_cost, 2),
        investigation_cost_inr=investigation_cost_inr,
    )


def total_cost(confusion: dict, cost_model: CostModel) -> dict:
    """confusion: {'tn':.., 'fp':.., 'fn':.., 'tp':..} from src.evaluation.metrics."""
    fp_cost = confusion["fp"] * (cost_model.false_positive_cost_inr + cost_model.investigation_cost_inr)
    fn_cost = confusion["fn"] * cost_model.false_negative_cost_inr
    tp_investigation_cost = confusion["tp"] * cost_model.investigation_cost_inr
    total = fp_cost + fn_cost + tp_investigation_cost
    return {
        "false_positive_cost_inr": round(fp_cost, 2),
        "false_negative_cost_inr": round(fn_cost, 2),
        "true_positive_investigation_cost_inr": round(tp_investigation_cost, 2),
        "total_cost_inr": round(total, 2),
    }


def cost_at_each_threshold(
    y_true: pd.Series, y_score: np.ndarray, cost_model: CostModel, thresholds: np.ndarray
) -> pd.DataFrame:
    """Total cost swept across candidate thresholds — used to select the
    cost-minimizing threshold on VALIDATION only (Phase 2I)."""
    from sklearn.metrics import confusion_matrix

    rows = []
    for t in thresholds:
        y_pred = (y_score >= t).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
        costs = total_cost({"tn": tn, "fp": fp, "fn": fn, "tp": tp}, cost_model)
        rows.append({"threshold": round(float(t), 4), "tn": tn, "fp": fp, "fn": fn, "tp": tp, **costs})
    return pd.DataFrame(rows)
