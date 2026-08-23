"""Phase 2E — transaction-time feature engineering.

Every function here is either (a) a pure per-row transform of columns
already available at transaction time (amount, temporal-from-DT,
missingness indicators), or (b) a fit-on-train/apply-everywhere encoder
(frequency encoding) — never a statistic computed from the full dataset
including validation/test, which would leak distributional information
across the temporal split (docs/FEATURE_AUDIT.md §F). Historical/
velocity aggregates live in src/features/historical.py (Phase 2F).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from src.features.schema import (
    HIGH_MISSINGNESS_CATEGORICAL,
    MODERATE_MISSINGNESS_NUMERIC,
    SEVERE_MISSINGNESS_NUMERIC,
)

MISSINGNESS_INDICATOR_COLUMNS = (
    SEVERE_MISSINGNESS_NUMERIC + MODERATE_MISSINGNESS_NUMERIC + HIGH_MISSINGNESS_CATEGORICAL + ["addr1", "addr2", "R_emaildomain"]
)


def add_amount_features(df: pd.DataFrame) -> pd.DataFrame:
    """Per-row transforms of TransactionAmt — no fitting required."""
    out = df.copy()
    out["amount_log1p"] = np.log1p(out["TransactionAmt"])
    cents = (out["TransactionAmt"] * 100).round().astype("int64") % 100
    out["amount_cents"] = cents
    out["amount_is_round_dollar"] = (cents == 0).astype("int8")
    return out


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Derived-only from TransactionDT — the raw column itself is never
    used as a feature (docs/FEATURE_AUDIT.md §C/§F, temporal-shift risk).
    """
    out = df.copy()
    seconds_into_day = out["TransactionDT"] % 86400
    hour_of_day = seconds_into_day // 3600
    out["hour_of_day"] = hour_of_day.astype("int16")
    out["hour_sin"] = np.sin(2 * np.pi * hour_of_day / 24)
    out["hour_cos"] = np.cos(2 * np.pi * hour_of_day / 24)

    day_index = (out["TransactionDT"] // 86400).astype("int32")
    day_of_cycle = day_index % 7  # relative 7-day cyclical position (no absolute-calendar anchor available)
    out["day_of_week_relative"] = day_of_cycle.astype("int8")
    out["day_sin"] = np.sin(2 * np.pi * day_of_cycle / 7)
    out["day_cos"] = np.cos(2 * np.pi * day_of_cycle / 7)
    return out


def add_missingness_indicators(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Add {col}_is_missing for each column — docs/FEATURE_AUDIT.md §D's
    central finding: for several columns, missingness itself is a
    stronger fraud signal than the raw value.
    """
    out = df.copy()
    cols = columns if columns is not None else MISSINGNESS_INDICATOR_COLUMNS
    for col in cols:
        if col in out.columns:
            out[f"{col}_is_missing"] = out[col].isna().astype("int8")
    return out


def add_v_block_features(df: pd.DataFrame, v_columns: list[str], high_missing_threshold: float = 80.0) -> pd.DataFrame:
    """Block-level treatment for V1-V339 (docs/FEATURE_AUDIT.md §D):
    a single 'v_block_missing_count' summarizing how many V-columns are
    null for this row (captures the block-correlated missingness pattern
    documented in docs/DATASET_AUDIT.md §6 as one feature instead of 339
    near-duplicate indicators), plus indicators for the specific
    high-missingness (>threshold%) subset where the present/absent
    fraud-rate gap was measured to be real.
    """
    out = df.copy()
    present_cols = [c for c in v_columns if c in out.columns]
    if not present_cols:
        return out
    out["v_block_missing_count"] = out[present_cols].isna().sum(axis=1)
    return out


@dataclass
class FrequencyEncoders:
    """Fit-on-train categorical frequency encoders — applying a val/test
    row's OWN frequency count (rather than the train-fit map) would leak
    information about the val/test distribution back into what the model
    effectively sees, so encoders are always fit on the train split only.
    """

    maps: dict[str, dict] = field(default_factory=dict)

    def fit(self, train_df: pd.DataFrame, columns: list[str]) -> "FrequencyEncoders":
        for col in columns:
            if col in train_df.columns:
                self.maps[col] = train_df[col].value_counts(normalize=True).to_dict()
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        for col, freq_map in self.maps.items():
            out[f"{col}_freq_encoded"] = out[col].map(freq_map).fillna(0.0)
        return out
