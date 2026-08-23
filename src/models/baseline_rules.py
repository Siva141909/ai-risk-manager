"""Phase 2B — BASELINE 1: deterministic rule baseline.

Intentionally simple (per Phase 2B's instruction not to over-optimize)
— four rules, combined with OR, using only information available at
transaction time (the same point-in-time-safe features from
src/features/historical.py, never a future-looking value). Thresholds
are round numbers chosen by a quick look at VALIDATION distribution,
not extensively tuned — this is meant to be the naive floor the ML
baselines have to beat, not a competitive model in its own right (design
doc Section 12).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class RuleThresholds:
    amount_zscore_threshold: float = 3.0          # amount far outside the customer's own history
    velocity_24h_threshold: int = 3                 # >=3 transactions by the same customer_proxy in 24h
    card_velocity_24h_threshold: int = 5              # >=5 transactions on the same card1 in 24h
    global_amount_percentile: float = 99.5             # extreme-amount cutoff, fit from TRAIN only


def fit_rule_thresholds(train_amounts: pd.Series, base: RuleThresholds = RuleThresholds()) -> dict:
    """The only 'fit' step: the global extreme-amount cutoff, computed from
    TRAIN amounts only (never validation/test) — everything else is a
    fixed round-number rule, not a fit statistic."""
    return {
        "amount_zscore_threshold": base.amount_zscore_threshold,
        "velocity_24h_threshold": base.velocity_24h_threshold,
        "card_velocity_24h_threshold": base.card_velocity_24h_threshold,
        "global_amount_cutoff": float(train_amounts.quantile(base.global_amount_percentile / 100)),
    }


def apply_rules(df: pd.DataFrame, fitted_thresholds: dict) -> pd.DataFrame:
    """Return a DataFrame with one boolean column per rule plus `flagged`
    (OR of all rules). df must contain cust_amount_zscore_vs_history,
    cust_txn_count_prior_24h, card1_txn_count_prior_24h, TransactionAmt.
    """
    out = pd.DataFrame(index=df.index)
    out["rule_amount_anomaly"] = (
        df["cust_amount_zscore_vs_history"].abs() > fitted_thresholds["amount_zscore_threshold"]
    ).fillna(False)
    out["rule_velocity"] = df["cust_txn_count_prior_24h"] >= fitted_thresholds["velocity_24h_threshold"]
    out["rule_card_repeated"] = df["card1_txn_count_prior_24h"] >= fitted_thresholds["card_velocity_24h_threshold"]
    out["rule_extreme_amount"] = df["TransactionAmt"] > fitted_thresholds["global_amount_cutoff"]
    out["flagged"] = (
        out["rule_amount_anomaly"] | out["rule_velocity"] | out["rule_card_repeated"] | out["rule_extreme_amount"]
    )
    return out


def rule_contribution_summary(rules_df: pd.DataFrame) -> dict:
    """How often each rule fires, and how often it's the ONLY rule firing
    for a flagged row — useful for reporting which rule carries the baseline."""
    rule_cols = [c for c in rules_df.columns if c.startswith("rule_")]
    summary = {}
    for col in rule_cols:
        summary[col] = {
            "n_fired": int(rules_df[col].sum()),
            "pct_of_flagged_where_only_this_fired": (
                round(
                    float(
                        (
                            rules_df[col]
                            & (rules_df[rule_cols].sum(axis=1) == 1)
                        ).sum()
                        / max(rules_df["flagged"].sum(), 1)
                        * 100
                    ),
                    2,
                )
            ),
        }
    return summary
