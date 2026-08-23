"""Unit tests for src/graph/signals.py (Phase 3G) and src/graph/explain.py (Phase 3K)."""

from __future__ import annotations

import pandas as pd

from src.graph.explain import build_evidence_and_narrative, build_narrative
from src.graph.case_interface import GraphEvidence
from src.graph.signals import GRAPH_FLAG_MIN_COMMUNITY_SIZE, compute_customer_graph_signals


def _toy_df() -> pd.DataFrame:
    # 3 customers sharing a device (a-b-c), 1 customer sharing an IP with 'a' too,
    # and 2 isolated customers sharing nothing.
    return pd.DataFrame(
        {
            "customer_proxy_id": ["a", "b", "c", "d", "e", "f"],
            "TransactionDT": [0, 3600, 7200, 10800, 100000, 200000],
            "device_synthetic_id": ["DEV-1", "DEV-1", "DEV-1", None, None, None],
            "ip_synthetic_id": ["1.1.1.1", None, None, "1.1.1.1", None, None],
            "bank_account_synthetic_id": [None, None, None, None, None, None],
        }
    )


def test_isolated_customers_absent_from_signals():
    signals = compute_customer_graph_signals(_toy_df())
    ids = set(signals["customer_proxy_id"])
    assert "e" not in ids
    assert "f" not in ids


def test_shared_device_customers_grouped_in_same_community():
    signals = compute_customer_graph_signals(_toy_df())
    a = signals[signals["customer_proxy_id"] == "a"].iloc[0]
    b = signals[signals["customer_proxy_id"] == "b"].iloc[0]
    assert a["community_id"] == b["community_id"]
    assert a["community_size"] >= 3  # a,b,c,d all connected via a's shared device+IP


def test_multi_attribute_overlap_flag():
    signals = compute_customer_graph_signals(_toy_df())
    a = signals[signals["customer_proxy_id"] == "a"].iloc[0]
    assert a["n_shared_devices"] > 0
    assert a["n_shared_ips"] > 0
    assert a["multi_attribute_overlap"] is True or bool(a["multi_attribute_overlap"]) is True

    b = signals[signals["customer_proxy_id"] == "b"].iloc[0]
    assert b["n_shared_devices"] > 0
    assert b["n_shared_ips"] == 0
    assert not bool(b["multi_attribute_overlap"])


def test_graph_flagged_threshold():
    signals = compute_customer_graph_signals(_toy_df())
    for _, row in signals.iterrows():
        expected = row["community_size"] >= GRAPH_FLAG_MIN_COMMUNITY_SIZE
        assert bool(row["graph_flagged"]) == expected


def test_deterministic_across_runs():
    s1 = compute_customer_graph_signals(_toy_df())
    s2 = compute_customer_graph_signals(_toy_df())
    pd.testing.assert_frame_equal(s1.sort_values("customer_proxy_id").reset_index(drop=True),
                                   s2.sort_values("customer_proxy_id").reset_index(drop=True))


def test_narrative_deterministic_same_input_same_output():
    evidence = GraphEvidence(
        community_id=1, community_size=7, n_shared_devices=2, n_shared_ips=1, n_shared_bank_accounts=1,
        multi_attribute_overlap=True, relationship_rarity_score=0.5, temporal_concentration_hours=14.0,
        detected_relationship_types=["SHARED_DEVICE", "SHARED_IP", "SHARED_BANK_ACCOUNT"], narrative="",
    )
    n1 = build_narrative(evidence)
    n2 = build_narrative(evidence)
    assert n1 == n2
    assert "7 customer proxies" in n1
    assert "2 shared devices" in n1
    assert "1 shared IP" in n1
    assert "14.0 hours" in n1


def test_narrative_handles_no_shared_infra_gracefully():
    evidence = GraphEvidence(
        community_id=1, community_size=1, n_shared_devices=0, n_shared_ips=0, n_shared_bank_accounts=0,
        multi_attribute_overlap=False, relationship_rarity_score=0.0, temporal_concentration_hours=None,
        detected_relationship_types=[], narrative="",
    )
    n = build_narrative(evidence)
    assert "no shared infrastructure" in n


def test_build_evidence_and_narrative_from_signals_row():
    signals = compute_customer_graph_signals(_toy_df())
    row = signals[signals["customer_proxy_id"] == "a"].iloc[0]
    evidence = build_evidence_and_narrative(row)
    assert evidence.narrative != ""
    assert "customer proxies are connected through" in evidence.narrative
