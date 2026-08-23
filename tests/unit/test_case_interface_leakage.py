"""Phase 3L — structural leakage guarantees for the case interface.

The key property: `Case` (production data) and `CaseGroundTruth`
(evaluation-only) are built by separate functions reading disjoint sets
of source columns, and `Case` has no field capable of holding a
ground-truth value at all — checked by field-name inspection, not just
by convention.
"""

from __future__ import annotations

import dataclasses

import pandas as pd

from src.generator.ground_truth import GROUND_TRUTH_COLUMNS
from src.graph.case_interface import Case, CaseGroundTruth, build_case, build_case_ground_truth


def _txn_row() -> pd.Series:
    return pd.Series(
        {
            "TransactionID": 12345,
            "TransactionDT": 86500,
            "customer_proxy_id": "customer_proxy-abc",
            "customer_proxy_confidence": "small",
            "device_synthetic_id": "DEV-1",
            "ip_synthetic_id": "1.2.3.4",
            "bank_account_synthetic_id": "BANK-1",
        }
    )


def _ground_truth_row() -> pd.Series:
    return pd.Series(
        {
            "original_isFraud": 1,
            "synthetic_ring_id": "RING-SHARED_DEVICE-000",
            "synthetic_abuse_type": "shared_device",
            "synthetic_ring_role": "core_member",
            "legitimate_cluster_id": None,
            "legitimate_cluster_type": None,
            "synthetic_entity_label": "ring_member",
        }
    )


def test_case_dataclass_has_no_ground_truth_field():
    field_names = {f.name for f in dataclasses.fields(Case)}
    for gt_col in GROUND_TRUTH_COLUMNS:
        assert gt_col not in field_names
    assert "isFraud" not in field_names
    assert "synthetic_ring_id" not in field_names


def test_build_case_never_reads_ground_truth_columns():
    """Even if the input row happens to carry ground-truth columns
    (e.g. because the caller passed the full synthetic dataframe by
    mistake), build_case must not surface them anywhere in the Case object."""
    row = pd.concat([_txn_row(), _ground_truth_row()])
    case = build_case(row, ml_risk_score=0.7, ml_risk_tier="HIGH", graph_evidence=None)
    case_str = str(case)
    assert "RING-SHARED_DEVICE-000" not in case_str
    assert "ring_member" not in case_str
    assert "core_member" not in case_str


def test_case_and_ground_truth_are_separate_objects():
    txn_row = _txn_row()
    gt_row = _ground_truth_row()
    case = build_case(txn_row, ml_risk_score=0.7, ml_risk_tier="HIGH", graph_evidence=None)
    gt = build_case_ground_truth(case.case_id, gt_row)

    assert isinstance(case, Case)
    assert isinstance(gt, CaseGroundTruth)
    assert not isinstance(case, CaseGroundTruth)
    assert gt.case_id == case.case_id
    assert gt.synthetic_ring_id == "RING-SHARED_DEVICE-000"


def test_case_id_deterministic():
    row = _txn_row()
    case1 = build_case(row, 0.5, "MEDIUM", None)
    case2 = build_case(row, 0.5, "MEDIUM", None)
    assert case1.case_id == case2.case_id == "CASE-12345"


def test_case_uses_real_transaction_dt_not_wall_clock():
    row = _txn_row()
    case = build_case(row, 0.5, "MEDIUM", None)
    assert case.trigger_transaction_dt == 86500
