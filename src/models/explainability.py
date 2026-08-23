"""Phase 2K — model explainability.

Uses XGBoost's native `pred_contribs` (exact SHAP values for tree
ensembles, computed by the same C++ path the `shap` package itself uses
for tree models) rather than adding the external `shap` dependency —
keeps the dependency footprint minimal (Phase 2's performance/resource
constraints) while still producing genuine per-prediction SHAP
attributions, not an approximation.

Raw column names are never shown to an end user — every feature is
mapped to a short, human-readable signal description
(FEATURE_SIGNAL_DESCRIPTIONS) before being surfaced. These descriptions
are what will later become evidence text for the investigation agent
(Phase 3+), not implemented here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import xgboost as xgb

FEATURE_SIGNAL_DESCRIPTIONS: dict[str, str] = {
    "cust_amount_zscore_vs_history": "unusual amount relative to this customer's own transaction history",
    "cust_txn_count_prior_24h": "high transaction velocity for this customer in the last 24 hours",
    "card1_txn_count_prior_24h": "this payment card used unusually often in the last 24 hours",
    "cust_time_since_last_txn": "unusual time gap since this customer's previous transaction",
    "TransactionAmt": "transaction amount",
    "amount_log1p": "transaction amount (log scale)",
    "amount_is_round_dollar": "round-number transaction amount",
    "D7_is_missing": "presence/absence of a specific Vesta time-delta signal (D7) — measured to be strongly fraud-correlated when present",
    "D12_is_missing": "presence/absence of a specific Vesta time-delta signal (D12)",
    "D8_is_missing": "presence/absence of a specific Vesta time-delta signal (D8)",
    "addr1_is_missing": "missing billing address information",
    "addr2_is_missing": "missing billing address information",
    "R_emaildomain_is_missing": "absence of a recipient email domain",
    "P_emaildomain_freq_encoded": "rarity of the purchaser's email domain",
    "R_emaildomain_freq_encoded": "rarity of the recipient's email domain",
    "ProductCD_freq_encoded": "rarity of the product category",
    "card4_freq_encoded": "rarity of the card network for this transaction",
    "card6_freq_encoded": "rarity of the card type (debit/credit) for this transaction",
    "v_block_missing_count": "unusual pattern of missing Vesta-engineered features",
    "hour_of_day": "time of day of the transaction",
    "hour_sin": "time of day of the transaction (cyclical)",
    "hour_cos": "time of day of the transaction (cyclical)",
    "customer_proxy_confidence_ordinal": "confidence level of the customer grouping used for this transaction",
    "has_identity_data": "availability of device/identity data for this transaction",
}


def describe_feature(col: str) -> str:
    if col in FEATURE_SIGNAL_DESCRIPTIONS:
        return FEATURE_SIGNAL_DESCRIPTIONS[col]
    if col.endswith("_is_missing"):
        return f"missingness of {col.removesuffix('_is_missing')} (measured as fraud-correlated, docs/FEATURE_AUDIT.md)"
    if col.endswith("_freq_encoded"):
        return f"rarity of {col.removesuffix('_freq_encoded')} value"
    if col.startswith("V"):
        return f"anonymized Vesta-engineered signal ({col})"
    return f"raw signal: {col}"


def global_feature_importance(booster: xgb.Booster, importance_type: str = "gain", top_n: int = 25) -> pd.DataFrame:
    scores = booster.get_score(importance_type=importance_type)
    df = pd.DataFrame({"feature": list(scores.keys()), "importance": list(scores.values())})
    df = df.sort_values("importance", ascending=False).head(top_n).reset_index(drop=True)
    df["description"] = df["feature"].map(describe_feature)
    return df


def shap_values(booster: xgb.Booster, X: pd.DataFrame) -> np.ndarray:
    """Exact per-row SHAP contributions (last column is the base value)."""
    dmat = xgb.DMatrix(X, missing=np.nan)
    return booster.predict(dmat, pred_contribs=True)


def explain_case(booster: xgb.Booster, X_row: pd.DataFrame, top_n: int = 5) -> list[dict]:
    """Top-N human-readable signals driving one specific prediction —
    this is the shape of evidence the investigation agent (Phase 3+)
    would consume."""
    contribs = shap_values(booster, X_row)[0]  # last element is the base value, drop it
    feature_contribs = contribs[:-1]
    order = np.argsort(-np.abs(feature_contribs))[:top_n]

    explanations = []
    for i in order:
        col = X_row.columns[i]
        explanations.append(
            {
                "feature": col,
                "description": describe_feature(col),
                "shap_contribution": round(float(feature_contribs[i]), 5),
                "direction": "increases risk" if feature_contribs[i] > 0 else "decreases risk",
                "value": X_row.iloc[0][col] if pd.notna(X_row.iloc[0][col]) else None,
            }
        )
    return explanations
