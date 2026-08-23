"""Unit tests for src/generator/customer_proxy.py — the Phase 1C decision.

Uses small fabricated dataframes to test the tiering/resolution logic
itself (mega-cluster individualization, tier boundaries, determinism).
Does not assert facts about the real dataset here — see
tests/integration/test_customer_proxy_real_data.py for that.
"""

from __future__ import annotations

import pandas as pd

from src.generator.customer_proxy import (
    LARGE_MAX,
    SMALL_MAX,
    resolve_customer_proxy,
    resolve_payment_instrument_proxy,
)


def _make_df(card_combo_sizes: dict[str, int]) -> pd.DataFrame:
    """Build a toy df where each key in card_combo_sizes repeats that many times."""
    rows = []
    txn_id = 0
    for combo, size in card_combo_sizes.items():
        card1 = combo
        for _ in range(size):
            rows.append(
                {
                    "TransactionID": txn_id,
                    "card1": card1,
                    "card2": "100",
                    "card3": "150",
                    "card4": "visa",
                    "card5": "200",
                    "card6": "debit",
                    "addr1": "300",
                    "P_emaildomain": "gmail.com",
                }
            )
            txn_id += 1
    return pd.DataFrame(rows)


def test_singleton_tier_assigned_correctly():
    df = _make_df({"A": 1, "B": 1, "C": 1})
    _, conf = resolve_customer_proxy(df)
    assert (conf == "singleton").all()


def test_small_tier_boundary():
    df = _make_df({"A": SMALL_MAX})
    _, conf = resolve_customer_proxy(df)
    assert (conf == "small").all()


def test_large_low_confidence_tier_boundary():
    df = _make_df({"A": SMALL_MAX + 1})
    _, conf = resolve_customer_proxy(df)
    assert (conf == "large_low_confidence").all()


def test_mega_unresolved_tier_and_individualization():
    """Clusters >= 500 must NOT be merged into one shared ID."""
    n = LARGE_MAX + 1
    df = _make_df({"A": n})
    proxy_id, conf = resolve_customer_proxy(df)
    assert (conf == "mega_unresolved").all()
    # every mega-cluster member gets a UNIQUE id, not one shared id
    assert proxy_id.nunique() == n


def test_every_row_gets_exactly_one_non_null_id():
    df = _make_df({"A": 3, "B": 700, "C": 60})
    proxy_id, conf = resolve_customer_proxy(df)
    assert proxy_id.notna().all()
    assert conf.notna().all()
    assert len(proxy_id) == len(df)


def test_small_and_large_clusters_still_share_one_id():
    df = _make_df({"A": 5})
    proxy_id, _ = resolve_customer_proxy(df)
    assert proxy_id.nunique() == 1


def test_deterministic_across_runs():
    df = _make_df({"A": 3, "B": 700})
    id1, conf1 = resolve_customer_proxy(df)
    id2, conf2 = resolve_customer_proxy(df)
    pd.testing.assert_series_equal(id1, id2)
    pd.testing.assert_series_equal(conf1, conf2)


def test_payment_instrument_proxy_uses_narrower_field_set():
    """Two rows with the same card1-6 but different addr1/email must still
    collide under payment_instrument_proxy (narrower key) even though they
    would NOT collide under customer_proxy (wider key)."""
    df = pd.DataFrame(
        [
            {
                "TransactionID": 1, "card1": "X", "card2": "100", "card3": "150",
                "card4": "visa", "card5": "200", "card6": "debit",
                "addr1": "300", "P_emaildomain": "gmail.com",
            },
            {
                "TransactionID": 2, "card1": "X", "card2": "100", "card3": "150",
                "card4": "visa", "card5": "200", "card6": "debit",
                "addr1": "999", "P_emaildomain": "yahoo.com",
            },
        ]
    )
    pi_id, _ = resolve_payment_instrument_proxy(df)
    cust_id, _ = resolve_customer_proxy(df)
    assert pi_id.nunique() == 1     # same card -> same payment_instrument_proxy
    assert cust_id.nunique() == 2   # different addr/email -> different customer_proxy


def test_customer_proxy_id_prefix_distinguishes_from_payment_instrument():
    df = _make_df({"A": 2})
    cust_id, _ = resolve_customer_proxy(df)
    pi_id, _ = resolve_payment_instrument_proxy(df)
    assert cust_id.iloc[0].startswith("customer_proxy-")
    assert pi_id.iloc[0].startswith("payment_instrument_proxy-")
