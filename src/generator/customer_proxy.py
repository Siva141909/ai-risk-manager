"""Customer-proxy and payment-instrument-proxy resolution — Phase 1C decision.

**Decision background (full evidence in docs/ENTITY_MODEL.md Section 3):**
raw card1-card6 tuple equality was rejected as a customer identity (it
produces a 14,112-row cluster at base-rate fraud — docs/DATASET_AUDIT.md
Section 8). Seven candidate strategies were measured
(scripts/investigate_customer_proxy.py). The chosen strategy —
`card1|card2|card3|card4|card5|card6|addr1|P_emaildomain` — still produces
oversized clusters for ~10% of rows; this module does NOT pretend those
clusters are single customers. It assigns a confidence tier and gives
oversized ("mega") clusters individualized, per-row IDs instead of
merging them, so every transaction gets exactly one customer_proxy_id,
but only tiers below "mega" should be trusted as plausibly-one-entity by
downstream graph/ring logic.

This is DERIVED PROXY data, not real customer identity — see
docs/ENTITY_MODEL.md for the REAL / DERIVED PROXY / SYNTHETIC boundary.
"""

from __future__ import annotations

import pandas as pd

# Tiering thresholds, chosen from the measured cluster-size distribution
# in docs/ENTITY_MODEL.md Section 3 (median 2, 75th pct 4, 90th pct 10,
# 95th pct 20, 99th pct 72 for the chosen combo) — not arbitrary round
# numbers picked without looking at the data.
SMALL_MAX = 49       # up to ~99.5th percentile-ish: plausible individual/household repeat use
LARGE_MAX = 499       # 50-499: still usable but low confidence, flagged
# >= 500 ("mega"): not treated as one entity at all — see resolve_customer_proxy()

CUSTOMER_PROXY_COLUMNS = ["card1", "card2", "card3", "card4", "card5", "card6", "addr1", "P_emaildomain"]
PAYMENT_INSTRUMENT_PROXY_COLUMNS = ["card1", "card2", "card3", "card4", "card5", "card6"]


def _combo_key(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    return df[cols].astype("string").fillna("NA").agg("|".join, axis=1)


def _tier(size: int) -> str:
    if size == 1:
        return "singleton"
    if size <= SMALL_MAX:
        return "small"
    if size <= LARGE_MAX:
        return "large_low_confidence"
    return "mega_unresolved"


def _resolve(df: pd.DataFrame, cols: list[str], prefix: str) -> tuple[pd.Series, pd.Series]:
    """Shared resolution logic for both proxy types.

    Returns (proxy_id, confidence_tier) aligned to df.index. Mega clusters
    (size >= 500) are NOT merged — each row gets its own unique
    '{prefix}-unresolved-{TransactionID}' id instead, so no downstream
    code can accidentally treat 500+ unrelated transactions as one entity.
    """
    key = _combo_key(df, cols)
    sizes = key.map(key.value_counts())
    tiers = sizes.map(_tier)

    proxy_id = key.copy()
    mega_mask = tiers == "mega_unresolved"
    if mega_mask.any():
        proxy_id.loc[mega_mask] = (
            prefix + "-unresolved-" + df.loc[mega_mask, "TransactionID"].astype(str)
        )
    proxy_id = prefix + "-" + proxy_id

    return proxy_id.rename(f"{prefix}_id"), tiers.rename(f"{prefix}_confidence")


def resolve_customer_proxy(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Assign customer_proxy_id and customer_proxy_confidence to every row.

    Required columns: card1-card6, addr1, P_emaildomain, TransactionID.
    """
    return _resolve(df, CUSTOMER_PROXY_COLUMNS, "customer_proxy")


def resolve_payment_instrument_proxy(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Assign payment_instrument_proxy_id and confidence to every row.

    Distinct from customer_proxy: represents "same card used," not "same
    customer" — narrower field set (card1-card6 only), same mega-cluster
    caution applies (raw card1-card6 alone has an even worse mega-cluster
    rate than the customer_proxy combo — docs/ENTITY_MODEL.md Section 3).
    """
    return _resolve(df, PAYMENT_INSTRUMENT_PROXY_COLUMNS, "payment_instrument_proxy")
