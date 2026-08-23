"""Phase 2I — deterministic risk-tier threshold policy.

The LLM (or any future agent) never determines the risk tier — this is a
pure, deterministic function of (risk_score, fixed thresholds). The
thresholds themselves are selected from VALIDATION data using an
explicit, documented framework (docs/RISK_THRESHOLD_POLICY.md), never
chosen as round numbers picked without evidence, and never touched by
the test split.

Three independently-justified boundaries, mirroring the design doc's
Section 20 LOW/MEDIUM/HIGH/CRITICAL structure:
  - `high` (MEDIUM/HIGH boundary) — the single cost-minimizing threshold
    from src/evaluation/cost.py's sweep (false-positive vs false-negative
    vs investigation cost).
  - `low` (LOW/MEDIUM boundary) — the largest threshold that still
    captures at least `low_recall_capture` of validation fraud above it
    (so auto-clearing below it sacrifices at most a small, stated
    fraction of recall).
  - `critical` (HIGH/CRITICAL boundary) — the smallest threshold at or
    above `high` where precision reaches `critical_precision` (a
    business-interpretable "more likely fraud than not" bar).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.evaluation.cost import CostModel, cost_at_each_threshold


@dataclass(frozen=True)
class RiskThresholds:
    low: float
    high: float
    critical: float
    method: str
    low_recall_capture: float
    critical_precision: float


def select_thresholds(
    y_val: pd.Series,
    val_scores: np.ndarray,
    cost_model: CostModel,
    low_recall_capture: float = 0.98,
    critical_precision: float = 0.85,
    grid_size: int = 1001,
) -> RiskThresholds:
    """critical_precision default of 0.85, not 0.5 — checked empirically
    (docs/RISK_THRESHOLD_POLICY.md §4): at 0.5, the search for "smallest
    threshold >= high with this precision" immediately returns `high`
    itself (precision at the cost-minimizing threshold was already
    ~0.66), collapsing the HIGH tier to empty. 0.85 was chosen by sweeping
    precision targets against the actual validation precision curve and
    picking the value that produces a real HIGH band between `high` and
    `critical`, not a threshold picked to look good in isolation.
    """
    grid = np.linspace(0.0, 1.0, grid_size)
    cost_df = cost_at_each_threshold(y_val, val_scores, cost_model, grid)

    high = float(cost_df.loc[cost_df["total_cost_inr"].idxmin(), "threshold"])

    fraud_scores = np.sort(val_scores[np.asarray(y_val) == 1])
    if len(fraud_scores) > 0:
        idx = int(np.floor((1 - low_recall_capture) * len(fraud_scores)))
        idx = min(idx, len(fraud_scores) - 1)
        low = float(fraud_scores[idx])
    else:
        low = 0.0
    low = min(low, high)  # the LOW/MEDIUM boundary must never exceed the primary MEDIUM/HIGH boundary

    candidates = cost_df[cost_df["threshold"] >= high].copy()
    denom = (candidates["tp"] + candidates["fp"]).replace(0, np.nan)
    candidates["precision"] = candidates["tp"] / denom
    above_bar = candidates[candidates["precision"] >= critical_precision]
    critical = float(above_bar["threshold"].min()) if len(above_bar) else float(grid[-1])

    return RiskThresholds(
        low=round(low, 4),
        high=round(high, 4),
        critical=round(critical, 4),
        method=(
            f"low=recall-floor({low_recall_capture*100:.0f}% fraud capture); "
            f"high=cost-minimizing; critical=precision>={critical_precision}"
        ),
        low_recall_capture=low_recall_capture,
        critical_precision=critical_precision,
    )


def classify_risk_tier(score: float, thresholds: RiskThresholds) -> str:
    """Deterministic, reproducible — pure function of (score, thresholds)."""
    if score < thresholds.low:
        return "LOW"
    if score < thresholds.high:
        return "MEDIUM"
    if score < thresholds.critical:
        return "HIGH"
    return "CRITICAL"


def classify_risk_tiers(scores: np.ndarray, thresholds: RiskThresholds) -> np.ndarray:
    tiers = np.full(len(scores), "LOW", dtype=object)
    tiers[scores >= thresholds.low] = "MEDIUM"
    tiers[scores >= thresholds.high] = "HIGH"
    tiers[scores >= thresholds.critical] = "CRITICAL"
    return tiers
