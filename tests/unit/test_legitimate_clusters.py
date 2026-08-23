"""Unit tests for src/generator/legitimate_clusters.py (Phase 1E)."""

from __future__ import annotations

import pandas as pd

from src.generator.customer_proxy import resolve_customer_proxy
from src.generator.entity_assignment import assign_entities
from src.generator.legitimate_clusters import ClusterTypeConfig, inject_legitimate_clusters


def _toy_transactions(n_customers: int) -> pd.DataFrame:
    """n_customers distinct singleton customer_proxy entities (one txn each)."""
    rows = []
    for i in range(n_customers):
        rows.append(
            {
                "TransactionID": i,
                "isFraud": 0,
                "TransactionDT": 86400 + i * 1000,
                "TransactionAmt": 50.0 + i,
                "card1": f"C{i}",
                "card2": "100",
                "card3": "150",
                "card4": "visa",
                "card5": "200",
                "card6": "debit",
                "addr1": "300",
                "P_emaildomain": "gmail.com",
            }
        )
    return pd.DataFrame(rows)


def test_household_cluster_shares_device_ip_and_address_when_probability_is_one():
    df = _toy_transactions(50)
    assigned = assign_entities(df, seed=42)
    cluster_types = (
        ClusterTypeConfig(
            "household", count=1, size_min=4, size_max=4,
            share_prob={"device": 1.0, "ip": 1.0, "address": 1.0, "bank_account": 0.0},
        ),
    )
    out, records = inject_legitimate_clusters(assigned, seed=42, cluster_types=cluster_types)

    assert len(records) == 1
    members = records[0]["members"]
    assert len(members) == 4
    assert set(records[0]["shared_attributes"]) == {"device", "ip", "address"}
    sub = out[out["customer_proxy_id"].isin(members)]
    assert sub["device_synthetic_id"].nunique() == 1
    assert sub["ip_synthetic_id"].nunique() == 1
    assert sub["address_synthetic_id"].nunique() == 1
    assert (sub["legitimate_cluster_type"] == "household").all()


def test_household_cluster_shares_nothing_when_probability_is_zero():
    df = _toy_transactions(50)
    assigned = assign_entities(df, seed=42)
    cluster_types = (
        ClusterTypeConfig(
            "household", count=1, size_min=4, size_max=4,
            share_prob={"device": 0.0, "ip": 0.0, "address": 0.0, "bank_account": 0.0},
        ),
    )
    out, records = inject_legitimate_clusters(assigned, seed=42, cluster_types=cluster_types)
    assert records[0]["shared_attributes"] == []
    members = records[0]["members"]
    sub = out[out["customer_proxy_id"].isin(members)]
    # still a labeled legitimate cluster, just with no shared attribute this instance
    assert (sub["legitimate_cluster_type"] == "household").all()
    assert sub["device_synthetic_id"].nunique() == len(members)  # each kept their individual device


def test_campus_cluster_shares_range_not_exact_ip():
    df = _toy_transactions(100)
    assigned = assign_entities(df, seed=42)
    cluster_types = (
        ClusterTypeConfig(
            "campus", count=1, size_min=20, size_max=20,
            share_prob={"device": 0.0, "ip": 0.0, "address": 0.0, "bank_account": 0.0},
            ip_range_share_prob=1.0,
        ),
    )
    out, records = inject_legitimate_clusters(assigned, seed=42, cluster_types=cluster_types)

    members = records[0]["members"]
    sub = out[out["customer_proxy_id"].isin(members)]
    assert sub["ip_range_synthetic"].nunique() == 1     # shared subnet
    assert sub["ip_synthetic_id"].nunique() > 1          # but distinct hosts


def test_no_cluster_member_reused_across_cluster_types():
    df = _toy_transactions(200)
    assigned = assign_entities(df, seed=42)
    out, records = inject_legitimate_clusters(assigned, seed=42)  # default cluster types
    all_members: list[str] = []
    for r in records:
        all_members.extend(r["members"])
    assert len(all_members) == len(set(all_members))


def test_deterministic_across_runs():
    df = _toy_transactions(200)
    assigned = assign_entities(df, seed=42)
    out1, records1 = inject_legitimate_clusters(assigned, seed=42)
    out2, records2 = inject_legitimate_clusters(assigned, seed=42)
    assert records1 == records2
    pd.testing.assert_frame_equal(out1, out2)


def test_skips_cluster_type_when_not_enough_candidates():
    df = _toy_transactions(5)  # too few for a 20-60 member campus
    assigned = assign_entities(df, seed=42)
    cluster_types = (
        ClusterTypeConfig(
            "campus", count=1, size_min=20, size_max=60,
            share_prob={"device": 0.0, "ip": 0.0, "address": 0.0, "bank_account": 0.0},
            ip_range_share_prob=1.0,
        ),
    )
    out, records = inject_legitimate_clusters(assigned, seed=42, cluster_types=cluster_types)
    assert records == []  # gracefully skipped, not an error
