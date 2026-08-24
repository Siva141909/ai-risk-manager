"""Phase 4A/4S — CaseGroundTruth isolation tests.

The agent must never receive CaseGroundTruth. Verified structurally:
AgentInput's only constructor (build_agent_input) takes a Case and
nothing else — there is no parameter through which ground truth could
be passed even by mistake.
"""

from __future__ import annotations

import dataclasses
import inspect

import pandas as pd

from src.agents.case_contract import AgentInput, DetectionEvidence, build_agent_input
from src.generator.ground_truth import GROUND_TRUTH_COLUMNS
from src.graph.case_interface import build_case


def _txn_row() -> pd.Series:
    return pd.Series(
        {
            "TransactionID": 999,
            "TransactionDT": 50000,
            "customer_proxy_id": "customer_proxy-xyz",
            "customer_proxy_confidence": "small",
            "device_synthetic_id": "DEV-1",
            "ip_synthetic_id": "1.2.3.4",
            "bank_account_synthetic_id": None,
        }
    )


def test_build_agent_input_signature_has_no_ground_truth_parameter():
    sig = inspect.signature(build_agent_input)
    param_names = set(sig.parameters.keys())
    assert param_names == {"case"}


def test_agent_input_dataclass_has_no_ground_truth_field():
    for cls in (AgentInput, DetectionEvidence):
        field_names = {f.name for f in dataclasses.fields(cls)}
        for gt_col in GROUND_TRUTH_COLUMNS:
            assert gt_col not in field_names
        assert "isFraud" not in field_names
        assert "original_isFraud" not in field_names


def test_agent_input_serialization_never_contains_ground_truth_keys():
    row = _txn_row()
    case = build_case(row, ml_risk_score=0.5, ml_risk_tier="MEDIUM", graph_evidence=None)
    agent_input = build_agent_input(case)
    serialized = dataclasses.asdict(agent_input)

    def _flatten_keys(obj):
        keys = set()
        if isinstance(obj, dict):
            keys |= set(obj.keys())
            for v in obj.values():
                keys |= _flatten_keys(v)
        elif isinstance(obj, list):
            for v in obj:
                keys |= _flatten_keys(v)
        return keys

    all_keys = _flatten_keys(serialized)
    for gt_col in GROUND_TRUTH_COLUMNS:
        assert gt_col not in all_keys


def test_detection_evidence_reflects_fixed_ml_score_agent_cannot_change_it():
    row = _txn_row()
    case = build_case(row, ml_risk_score=0.73, ml_risk_tier="HIGH", graph_evidence=None)
    agent_input = build_agent_input(case)
    assert agent_input.detection_evidence.ml_risk_score == 0.73
    assert agent_input.detection_evidence.ml_risk_tier == "HIGH"
    # DetectionEvidence is a frozen dataclass -- structurally immutable
    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        agent_input.detection_evidence.ml_risk_score = 0.99
