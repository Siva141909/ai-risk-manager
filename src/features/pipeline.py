"""Phase 2E/2F orchestration — raw transactions to a point-in-time-safe
feature matrix.

Historical/velocity features (src/features/historical.py) are computed
on the FULL chronological stream (train+validation+test together,
sorted by TransactionDT) BEFORE the split is applied — this is correct,
not a leak: a validation/test row's "transactions in the last 24h"
legitimately includes real transactions from the training period, the
same way it would at inference time in production. What must never
happen (and is what src/ingestion/split.py + the temporal ordering
enforce) is a later row's data influencing an EARLIER row's features —
verified directly in tests/unit/test_historical_features_leakage.py and
tests/integration/test_pipeline_leakage.py.

Frequency encoders are fit on the TRAIN split only, then applied to all
three splits — fitting on the full dataset would leak validation/test
category-frequency information into what the model effectively sees.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.features.engineering import (
    FrequencyEncoders,
    add_amount_features,
    add_missingness_indicators,
    add_temporal_features,
    add_v_block_features,
)
from src.features.historical import add_group_amount_stats, add_group_velocity_features
from src.features.leakage_guard import NON_FEATURE_COLUMNS, assert_no_leakage
from src.features.schema import (
    ADDRESS_NUMERIC,
    MODERATE_MISSINGNESS_NUMERIC,
    SAFE_NUMERIC,
    SEVERE_MISSINGNESS_NUMERIC,
    V_BLOCK,
)
from src.generator.customer_proxy import resolve_customer_proxy, resolve_payment_instrument_proxy
from src.ingestion.split import assign_split

RAW_TRANSACTION_COLUMNS = (
    ["TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "ProductCD"]
    + [f"card{i}" for i in range(1, 7)]
    + ["addr1", "addr2", "dist1", "dist2", "P_emaildomain", "R_emaildomain"]
    + [f"C{i}" for i in range(1, 15)]
    + [f"D{i}" for i in range(1, 16)]
    + [f"M{i}" for i in range(1, 10)]
    + V_BLOCK
)

CATEGORICAL_ENCODE_COLUMNS = [
    "ProductCD", "card4", "card6",
    "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9",
    "P_emaildomain", "R_emaildomain", "DeviceType",
]

# Confidence tiers reflect decreasing trust in the proxy resolution
# (docs/ENTITY_MODEL.md §3) — an ordinal encoding preserves that order,
# unlike frequency encoding which would not.
CONFIDENCE_ORDINAL_MAP = {"singleton": 0, "small": 1, "large_low_confidence": 2, "mega_unresolved": 3}


def load_raw_transactions(raw_dir: Path) -> pd.DataFrame:
    """Load train_transaction.csv + a minimal real-identity join (DeviceType only —
    the full id_01-38 block is documented at summary level, docs/FEATURE_AUDIT.md,
    but not individually engineered in this baseline; noted as a limitation, not hidden).
    """
    df = pd.read_csv(raw_dir / "train_transaction.csv", usecols=RAW_TRANSACTION_COLUMNS)
    identity = pd.read_csv(raw_dir / "train_identity.csv", usecols=["TransactionID", "DeviceType"])
    df = df.merge(identity, on="TransactionID", how="left")
    df["has_identity_data"] = df["DeviceType"].notna().astype("int8")
    return df


@dataclass
class FeatureArtifact:
    df: pd.DataFrame  # full frame: real columns + engineered features + meta (split, proxies, isFraud)
    feature_columns: list[str]
    encoders: FrequencyEncoders


def build_feature_matrix(raw_df: pd.DataFrame) -> FeatureArtifact:
    df = raw_df.sort_values("TransactionDT", kind="mergesort").reset_index(drop=True)

    cust_id, cust_conf = resolve_customer_proxy(df)
    pi_id, pi_conf = resolve_payment_instrument_proxy(df)
    # Batched via pd.concat rather than repeated single-column assignment —
    # avoids pandas' O(n^2)-ish DataFrame fragmentation at ~450 columns / 590K rows.
    df = pd.concat(
        [
            df,
            pd.DataFrame(
                {
                    "customer_proxy_id": cust_id,
                    "customer_proxy_confidence": cust_conf,
                    "payment_instrument_proxy_id": pi_id,
                    "payment_instrument_proxy_confidence": pi_conf,
                    "customer_proxy_confidence_ordinal": cust_conf.map(CONFIDENCE_ORDINAL_MAP),
                    "payment_instrument_proxy_confidence_ordinal": pi_conf.map(CONFIDENCE_ORDINAL_MAP),
                    "split": assign_split(df),
                }
            ),
        ],
        axis=1,
    ).copy()

    df = add_amount_features(df)
    df = add_temporal_features(df)
    df = add_missingness_indicators(df)
    df = add_v_block_features(df, V_BLOCK)

    # Historical/velocity features on the full chronological stream — see module docstring.
    df = add_group_velocity_features(df, "customer_proxy_id", "cust")
    df = add_group_amount_stats(df, "customer_proxy_id", "cust")
    df = add_group_velocity_features(df, "card1", "card1")
    df = add_group_amount_stats(df, "card1", "card1")

    train_mask = df["split"] == "train"
    encoders = FrequencyEncoders().fit(df.loc[train_mask], CATEGORICAL_ENCODE_COLUMNS)
    df = encoders.transform(df)

    feature_columns = _feature_columns(df)
    return FeatureArtifact(df=df, feature_columns=feature_columns, encoders=encoders)


def _feature_columns(df: pd.DataFrame) -> list[str]:
    engineered_suffixes = ("_freq_encoded", "_is_missing", "_so_far", "_prior_24h", "_time_since_last_txn")
    candidates = (
        SAFE_NUMERIC
        + MODERATE_MISSINGNESS_NUMERIC
        + SEVERE_MISSINGNESS_NUMERIC
        + ADDRESS_NUMERIC
        + ["card1"]
        + V_BLOCK
        + [
            "amount_log1p", "amount_cents", "amount_is_round_dollar",
            "hour_of_day", "hour_sin", "hour_cos", "day_of_week_relative", "day_sin", "day_cos",
            "v_block_missing_count", "has_identity_data",
            "customer_proxy_confidence_ordinal", "payment_instrument_proxy_confidence_ordinal",
        ]
        + [c for c in df.columns if c.endswith(engineered_suffixes)]
    )
    seen = set()
    ordered_unique = [c for c in candidates if c in df.columns and not (c in seen or seen.add(c))]
    return [c for c in ordered_unique if c not in NON_FEATURE_COLUMNS]


def get_split(artifact: FeatureArtifact, split_name: str) -> tuple[pd.DataFrame, pd.Series]:
    """Return (X, y) for one split, guaranteed leakage-checked."""
    mask = artifact.df["split"] == split_name
    X = artifact.df.loc[mask, artifact.feature_columns]
    assert_no_leakage(X)
    y = artifact.df.loc[mask, "isFraud"]
    return X, y
