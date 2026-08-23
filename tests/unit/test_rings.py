"""Unit tests for src/generator/rings.py (Phase 1F)."""

from __future__ import annotations

import pandas as pd

from src.generator.entity_assignment import assign_entities
from src.generator.rings import RingTypeConfig, inject_rings


def _toy_transactions(n_customers: int, amt_start: float = 100.0) -> pd.DataFrame:
    rows = []
    for i in range(n_customers):
        rows.append(
            {
                "TransactionID": i,
                "isFraud": 0,
                "TransactionDT": 86400 + i * 60,  # 1 minute apart -> all within a burst window
                "TransactionAmt": amt_start + i,
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


def test_ring_core_members_share_the_attribute():
    df = _toy_transactions(30)
    assigned = assign_entities(df, seed=42)
    ring_types = (
        RingTypeConfig(
            "shared_device", count=1, size_min=5, size_max=5, burst_window_minutes=60,
            amount_pattern="near_identical", noise_ratio=0.0, shared_attrs=("device",),
        ),
    )
    out, records, _ = inject_rings(assigned, seed=42, ring_types=ring_types, decoy_attach_probability=0.0)

    assert len(records) == 1
    r = records[0]
    assert r["abuse_type"] == "shared_device"
    assert len(r["core_members"]) == 5  # noise_ratio=0 -> all core
    sub = out[out["customer_proxy_id"].isin(r["core_members"])]
    assert sub["device_synthetic_id"].nunique() == 1


def test_noise_members_labeled_but_not_sharing_attribute():
    df = _toy_transactions(30)
    assigned = assign_entities(df, seed=42)
    ring_types = (
        RingTypeConfig(
            "shared_device", count=1, size_min=10, size_max=10, burst_window_minutes=60,
            amount_pattern="near_identical", noise_ratio=0.3, shared_attrs=("device",),
        ),
    )
    out, records, _ = inject_rings(assigned, seed=42, ring_types=ring_types, decoy_attach_probability=0.0)

    r = records[0]
    assert len(r["noise_members"]) == 3  # round(10 * 0.3)
    core_device = out.loc[out["customer_proxy_id"].isin(r["core_members"]), "device_synthetic_id"].unique()
    assert len(core_device) == 1
    for noise_member in r["noise_members"]:
        noise_device = out.loc[out["customer_proxy_id"] == noise_member, "device_synthetic_id"].iloc[0]
        assert noise_device != core_device[0]
        # still labeled as a ring member in ground truth
        assert out.loc[out["customer_proxy_id"] == noise_member, "synthetic_ring_id"].iloc[0] == r["ring_id"]


def test_ring_members_disjoint_across_ring_instances():
    df = _toy_transactions(60)
    assigned = assign_entities(df, seed=42)
    ring_types = (
        RingTypeConfig(
            "shared_device", count=3, size_min=5, size_max=5, burst_window_minutes=60,
            amount_pattern="near_identical", noise_ratio=0.0, shared_attrs=("device",),
        ),
    )
    out, records, used = inject_rings(assigned, seed=42, ring_types=ring_types, decoy_attach_probability=0.0)
    all_members: list[str] = []
    for r in records:
        all_members.extend(r["core_members"] + r["noise_members"])
    assert len(all_members) == len(set(all_members))


def test_multi_attribute_ring_shares_all_configured_attrs():
    df = _toy_transactions(20)
    assigned = assign_entities(df, seed=42)
    ring_types = (
        RingTypeConfig(
            "multi_attribute", count=1, size_min=6, size_max=6, burst_window_minutes=60,
            amount_pattern="near_identical", noise_ratio=0.0, shared_attrs=("device", "ip", "bank_account"),
        ),
    )
    out, records, _ = inject_rings(assigned, seed=42, ring_types=ring_types, decoy_attach_probability=0.0)
    r = records[0]
    sub = out[out["customer_proxy_id"].isin(r["core_members"])]
    assert sub["device_synthetic_id"].nunique() == 1
    assert sub["ip_synthetic_id"].nunique() == 1
    assert sub["bank_account_synthetic_id"].nunique() == 1


def test_real_columns_never_modified_by_ring_injection():
    df = _toy_transactions(30)
    assigned = assign_entities(df, seed=42)
    real_cols = ["TransactionID", "isFraud", "TransactionDT", "TransactionAmt", "card1", "addr1", "P_emaildomain"]
    before = assigned[real_cols].copy()
    out, _, _ = inject_rings(assigned, seed=42)
    pd.testing.assert_frame_equal(before, out[real_cols])


def test_deterministic_across_runs():
    df = _toy_transactions(60)
    assigned = assign_entities(df, seed=42)
    out1, records1, _ = inject_rings(assigned, seed=42)
    out2, records2, _ = inject_rings(assigned, seed=42)
    assert records1 == records2
    pd.testing.assert_frame_equal(out1, out2)


def test_skips_ring_type_when_not_enough_candidates():
    df = _toy_transactions(3)
    assigned = assign_entities(df, seed=42)
    ring_types = (
        RingTypeConfig(
            "shared_device", count=1, size_min=8, size_max=8, burst_window_minutes=60,
            amount_pattern="near_identical", noise_ratio=0.0, shared_attrs=("device",),
        ),
    )
    out, records, _ = inject_rings(assigned, seed=42, ring_types=ring_types)
    assert records == []
