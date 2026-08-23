"""Phase 1H — synthetic-label leakage protection.

The synthetic ground-truth columns (Phase 1G) exist to EVALUATE ring/graph
detection later — they must never become model input features, or any
detector trained on them would just be re-learning the generator's own
injection rules instead of learning anything transferable. This module is
the single source of truth for which columns are ground truth
(denylisted from features) vs. allowed as model input.

No feature engineering happens in this module or this phase — this is a
guard/contract for the future feature pipeline (Phase 3+) to import and
respect, matching Section 25's "Validation" stage boundary.
"""

from __future__ import annotations

import pandas as pd

from src.generator.ground_truth import GROUND_TRUTH_COLUMNS

# The real fraud label is the ML target, not a feature — same
# denylist-from-X-matrix treatment applies to it as to the synthetic
# ground truth, for the same reason (a column can't be both target and
# feature). Identifier/join-key columns are also excluded — see
# docs/DATASET_AUDIT.md Section 12 ("exclude TransactionID from modeling").
NON_FEATURE_COLUMNS = frozenset(
    GROUND_TRUTH_COLUMNS
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
