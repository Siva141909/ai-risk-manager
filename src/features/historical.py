"""Phase 2E/2F — point-in-time-safe historical/velocity features.

The single hardest leakage risk in this project (docs/FEATURE_AUDIT.md §F):
any aggregate computed per customer_proxy_id or card1 must use STRICTLY
PAST rows only, relative to each row's own TransactionDT. Every function
here is vectorized (no groupby.apply — avoided for both speed at 590K
rows and to keep the "current row excluded" logic explicit and testable)
and is checked directly in tests/unit/test_historical_features_leakage.py
by recomputing a sample by brute force and comparing.

Convention: the input dataframe MUST already be sorted by TransactionDT
(callers are responsible — src/features/pipeline.py enforces this once,
rather than every function re-sorting).
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _require_sorted(df: pd.DataFrame) -> None:
    if not df["TransactionDT"].is_monotonic_increasing:
        raise ValueError("historical features require the dataframe sorted by TransactionDT first")


def add_group_velocity_features(df: pd.DataFrame, group_col: str, prefix: str) -> pd.DataFrame:
    """Add {prefix}_txn_count_so_far, {prefix}_time_since_last_txn,
    {prefix}_txn_count_prior_24h — all computed from strictly-prior rows
    within the same group_col value.
    """
    _require_sorted(df)
    out = df.copy()
    grp = out.groupby(group_col, sort=False)

    # Count of PRIOR rows in the same group — cumcount() is 0 for the
    # first occurrence, 1 for the second, etc. -> naturally excludes
    # the current row by construction.
    out[f"{prefix}_txn_count_so_far"] = grp.cumcount()

    # Time since the previous transaction in the same group (NaT/NaN for
    # the first occurrence — no prior transaction exists).
    out[f"{prefix}_time_since_last_txn"] = grp["TransactionDT"].diff()

    # Count of prior transactions within a 24h window [t-86400, t),
    # STRICTLY excluding the current row (even a row sharing the exact
    # same TransactionDT is excluded, since the comparison is a strict
    # '<'). Computed via searchsorted, NOT pandas' groupby().rolling() —
    # that was tried first and found to silently misalign results:
    # groupby(...).rolling(...) returns values grouped-then-ordered, not
    # in original row order, and converting straight to .to_numpy() for
    # positional assignment corrupted the result whenever groups
    # interleave in time (which they always do) — caught by
    # tests/integration/test_pipeline_leakage.py against real data,
    # where a customer with exactly ONE transaction ever showed a
    # nonzero prior-24h count. searchsorted on each group's own
    # (already time-sorted, per _require_sorted) DT array is both
    # correct and index-preserving via groupby().transform().
    def _prior_24h_count(dt_series: pd.Series) -> pd.Series:
        dt = dt_series.to_numpy()
        hi = np.searchsorted(dt, dt, side="left")             # count of values < dt[i]
        lo = np.searchsorted(dt, dt - 86400, side="left")       # count of values < dt[i]-86400
        return pd.Series(hi - lo, index=dt_series.index)

    out[f"{prefix}_txn_count_prior_24h"] = grp["TransactionDT"].transform(_prior_24h_count)

    return out


def add_group_amount_stats(df: pd.DataFrame, group_col: str, prefix: str) -> pd.DataFrame:
    """Add {prefix}_amount_mean_so_far, {prefix}_amount_std_so_far,
    {prefix}_amount_zscore_vs_history — computed from strictly-prior rows.

    Vectorized via cumulative-sum algebra (not groupby.apply, for speed
    at 590K rows): prior_mean = (cumsum_including_self - self) / count_prior.
    """
    _require_sorted(df)
    out = df.copy()
    grp = out.groupby(group_col, sort=False)["TransactionAmt"]

    cumcount = out.groupby(group_col, sort=False).cumcount()  # count of PRIOR rows
    cumsum_incl_self = grp.cumsum()
    cumsumsq_incl_self = grp.transform(lambda s: (s ** 2).cumsum())

    prior_sum = cumsum_incl_self - out["TransactionAmt"]
    prior_sumsq = cumsumsq_incl_self - out["TransactionAmt"] ** 2

    n_prior = cumcount.replace(0, np.nan)  # avoid div-by-zero; first occurrence -> NaN stats
    prior_mean = prior_sum / n_prior
    prior_var = (prior_sumsq / n_prior) - prior_mean ** 2
    prior_var = prior_var.clip(lower=0)  # guard tiny negative values from float error
    prior_std = np.sqrt(prior_var)

    out[f"{prefix}_amount_mean_so_far"] = prior_mean
    out[f"{prefix}_amount_std_so_far"] = prior_std
    out[f"{prefix}_amount_zscore_vs_history"] = (out["TransactionAmt"] - prior_mean) / (prior_std + 1e-6)

    return out
