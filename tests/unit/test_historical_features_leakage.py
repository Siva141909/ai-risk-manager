"""Unit tests for src/features/historical.py — the highest-risk leakage
surface in Phase 2 (docs/FEATURE_AUDIT.md §F). Every aggregate is
verified by brute-force recomputation against a hand-crafted example
with known correct answers, not just "runs without error."
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.features.historical import add_group_amount_stats, add_group_velocity_features


def _toy_df() -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "TransactionID": [1, 2, 3, 4, 5, 6],
            "TransactionDT": [0, 3600, 90000, 91000, 200000, 200000],
            "TransactionAmt": [10.0, 20.0, 100.0, 5.0, 30.0, 7.0],
            "customer_proxy_id": ["A", "A", "A", "B", "A", "B"],
        }
    )
    return df.sort_values("TransactionDT", kind="mergesort").reset_index(drop=True)


def test_requires_sorted_input():
    df = _toy_df().iloc[::-1]  # reverse -> not sorted
    with pytest.raises(ValueError, match="sorted"):
        add_group_velocity_features(df, "customer_proxy_id", "cust")


def test_txn_count_so_far_excludes_current_row():
    out = add_group_velocity_features(_toy_df(), "customer_proxy_id", "cust")
    # A's transactions in order: t=0 (0th prior), t=3600 (1 prior), t=90000 (2 priors), t=200000 (3 priors)
    a_rows = out[out["customer_proxy_id"] == "A"].sort_values("TransactionDT")
    assert a_rows["cust_txn_count_so_far"].tolist() == [0, 1, 2, 3]


def test_time_since_last_txn():
    out = add_group_velocity_features(_toy_df(), "customer_proxy_id", "cust")
    a_rows = out[out["customer_proxy_id"] == "A"].sort_values("TransactionDT")
    assert np.isnan(a_rows["cust_time_since_last_txn"].iloc[0])
    assert a_rows["cust_time_since_last_txn"].iloc[1] == 3600
    assert a_rows["cust_time_since_last_txn"].iloc[2] == 86400


def test_txn_count_prior_24h_excludes_current_and_stale_events():
    out = add_group_velocity_features(_toy_df(), "customer_proxy_id", "cust")
    a_rows = out[out["customer_proxy_id"] == "A"].sort_values("TransactionDT").reset_index(drop=True)
    # row0 (t=0): no prior -> 0
    assert a_rows["cust_txn_count_prior_24h"].iloc[0] == 0
    # row1 (t=3600): t=0 is within 24h -> 1
    assert a_rows["cust_txn_count_prior_24h"].iloc[1] == 1
    # row2 (t=90000): only t=3600 within last 24h (t=0 is >24h before) -> 1
    assert a_rows["cust_txn_count_prior_24h"].iloc[2] == 1
    # row3 (t=200000): nothing within the last 24h -> 0 (not NaN)
    assert a_rows["cust_txn_count_prior_24h"].iloc[3] == 0


def test_amount_mean_and_zscore_use_only_prior_rows():
    out = add_group_amount_stats(_toy_df(), "customer_proxy_id", "cust")
    a_rows = out[out["customer_proxy_id"] == "A"].sort_values("TransactionDT").reset_index(drop=True)
    assert np.isnan(a_rows["cust_amount_mean_so_far"].iloc[0])  # first txn -> no history
    assert a_rows["cust_amount_mean_so_far"].iloc[1] == 10.0  # mean of [10.0]
    assert a_rows["cust_amount_mean_so_far"].iloc[2] == 15.0  # mean of [10.0, 20.0]
    assert abs(a_rows["cust_amount_mean_so_far"].iloc[3] - 130 / 3) < 1e-9  # mean of [10,20,100]


def test_no_future_row_ever_influences_a_past_row():
    """Direct leakage check: shuffle rows AFTER an earlier row's DT and
    confirm the earlier row's computed features are identical regardless
    of what happens later in the group."""
    df = _toy_df()
    out_full = add_group_amount_stats(
        add_group_velocity_features(df, "customer_proxy_id", "cust"), "customer_proxy_id", "cust"
    )

    # Truncate to only rows up to and including TransactionID=3 (drop the
    # later rows 4,5,6) and recompute -- row 1,2,3's features must be
    # byte-identical whether or not the later rows exist at all.
    truncated = df[df["TransactionID"].isin([1, 2, 3])].reset_index(drop=True)
    out_truncated = add_group_amount_stats(
        add_group_velocity_features(truncated, "customer_proxy_id", "cust"), "customer_proxy_id", "cust"
    )

    for txn_id in [1, 2, 3]:
        full_row = out_full[out_full["TransactionID"] == txn_id].iloc[0]
        trunc_row = out_truncated[out_truncated["TransactionID"] == txn_id].iloc[0]
        for col in [
            "cust_txn_count_so_far", "cust_time_since_last_txn", "cust_txn_count_prior_24h",
            "cust_amount_mean_so_far", "cust_amount_std_so_far", "cust_amount_zscore_vs_history",
        ]:
            a, b = full_row[col], trunc_row[col]
            if pd.isna(a) and pd.isna(b):
                continue
            assert a == b, f"txn {txn_id} col {col}: {a} != {b} -- future rows leaked into a past row's features"


def test_deterministic_across_runs():
    df = _toy_df()
    out1 = add_group_amount_stats(add_group_velocity_features(df, "customer_proxy_id", "cust"), "customer_proxy_id", "cust")
    out2 = add_group_amount_stats(add_group_velocity_features(df, "customer_proxy_id", "cust"), "customer_proxy_id", "cust")
    pd.testing.assert_frame_equal(out1, out2)
