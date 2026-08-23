"""Phase 1H — synthetic-label leakage protection (extended Phase 2A/2M).

The synthetic ground-truth columns (Phase 1G) exist to EVALUATE ring/graph
detection later — they must never become model input features, or any
detector trained on them would just be re-learning the generator's own
injection rules instead of learning anything transferable. This module is
the single source of truth for which columns are ground truth or graph-only
synthetic overlay (denylisted from ML features) vs. allowed as model input.

Phase 2A extended this list beyond ground truth to include the fully
synthetic graph-entity columns (device/IP/bank_account/address —
docs/FEATURE_AUDIT.md §G): those belong to the graph layer only and were
never real signal to begin with, so they must never leak into the ML
model either, for the same reason as the ground-truth columns.

No feature engineering happens in this module — this is a guard/contract
the feature pipeline (src/features/) imports and respects, matching
Section 25's "Validation" stage boundary.
"""

from __future__ import annotations

import pandas as pd

from src.generator.ground_truth import GROUND_TRUTH_COLUMNS

# Fully synthetic graph-entity columns (Phase 1/1.5) — zero real signal,
# belong to the graph layer only. See docs/FEATURE_AUDIT.md §G.
SYNTHETIC_ENTITY_COLUMNS = [
    "device_synthetic_id",
    "device_type_synthetic",
    "ip_synthetic_id",
    "ip_range_synthetic",
    "bank_account_synthetic_id",
    "ifsc_prefix_synthetic",
    "address_synthetic_id",
    "pincode_synthetic",
]

# The real fraud label is the ML target, not a feature — same
# denylist-from-X-matrix treatment applies to it as to the synthetic
# ground truth, for the same reason (a column can't be both target and
# feature). Identifier/join-key columns are also excluded — see
# docs/DATASET_AUDIT.md Section 12 ("exclude TransactionID from modeling")
# and docs/FEATURE_AUDIT.md §E.
NON_FEATURE_COLUMNS = frozenset(
    GROUND_TRUTH_COLUMNS
    + SYNTHETIC_ENTITY_COLUMNS
    + [
        "isFraud",
        "TransactionID",
        "customer_proxy_id",
        "payment_instrument_proxy_id",
    ]
)


class LeakageError(ValueError):
    """Raised when a denylisted (ground-truth or identifier) column is found in a feature matrix."""


def assert_no_leakage(feature_df: pd.DataFrame) -> None:
    """Raise LeakageError if any denylisted column is present in feature_df."""
    present = NON_FEATURE_COLUMNS.intersection(feature_df.columns)
    if present:
        raise LeakageError(
            f"Denylisted column(s) present in feature matrix: {sorted(present)}. "
            "Ground-truth and identifier columns must never be used as model features."
        )


def filter_allowed_features(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with every denylisted column dropped."""
    return df.drop(columns=[c for c in NON_FEATURE_COLUMNS if c in df.columns])
