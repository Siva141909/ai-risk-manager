"""Phase 2M leakage test #6 continued + reproducibility (Phase 2 "threshold
determinism" requirement): the risk-tier classification function must be
a pure, deterministic function of (score, thresholds) — the LLM/agent
must never determine the tier (design doc Section 20, Phase 2I)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.evaluation.cost import CostModel
from src.models.thresholds import RiskThresholds, classify_risk_tier, classify_risk_tiers, select_thresholds


def test_classify_risk_tier_is_deterministic():
    thresholds = RiskThresholds(low=0.1, high=0.5, critical=0.8, method="test", low_recall_capture=0.98, critical_precision=0.85)
    for score in [0.05, 0.3, 0.6, 0.9]:
        r1 = classify_risk_tier(score, thresholds)
        r2 = classify_risk_tier(score, thresholds)
        assert r1 == r2


def test_classify_risk_tier_boundaries():
    thresholds = RiskThresholds(low=0.1, high=0.5, critical=0.8, method="test", low_recall_capture=0.98, critical_precision=0.85)
    assert classify_risk_tier(0.05, thresholds) == "LOW"
    assert classify_risk_tier(0.1, thresholds) == "MEDIUM"   # boundary is inclusive on the upper side
    assert classify_risk_tier(0.49, thresholds) == "MEDIUM"
    assert classify_risk_tier(0.5, thresholds) == "HIGH"
    assert classify_risk_tier(0.79, thresholds) == "HIGH"
    assert classify_risk_tier(0.8, thresholds) == "CRITICAL"
    assert classify_risk_tier(1.0, thresholds) == "CRITICAL"


def test_classify_risk_tiers_vectorized_matches_scalar():
    thresholds = RiskThresholds(low=0.1, high=0.5, critical=0.8, method="test", low_recall_capture=0.98, critical_precision=0.85)
    scores = np.array([0.05, 0.3, 0.6, 0.9, 0.1, 0.5, 0.8])
    vectorized = classify_risk_tiers(scores, thresholds)
    scalar = [classify_risk_tier(s, thresholds) for s in scores]
    assert list(vectorized) == scalar


def test_select_thresholds_deterministic_across_runs():
    rng = np.random.default_rng(42)
    y_val = pd.Series(rng.integers(0, 2, size=2000) < 0.05, dtype=int)  # ~5% positive
    scores = rng.random(2000)
    cost_model = CostModel(false_positive_cost_inr=500.0, false_negative_cost_inr=1000.0, investigation_cost_inr=150.0)

    t1 = select_thresholds(y_val, scores, cost_model)
    t2 = select_thresholds(y_val, scores, cost_model)
    assert t1 == t2


def test_thresholds_are_monotonically_ordered():
    """low <= high <= critical must always hold, by construction."""
    rng = np.random.default_rng(7)
    y_val = pd.Series(rng.integers(0, 2, size=2000) < 0.05, dtype=int)
    scores = rng.random(2000)
    cost_model = CostModel(false_positive_cost_inr=500.0, false_negative_cost_inr=1000.0, investigation_cost_inr=150.0)

    thresholds = select_thresholds(y_val, scores, cost_model)
    assert thresholds.low <= thresholds.high <= thresholds.critical
