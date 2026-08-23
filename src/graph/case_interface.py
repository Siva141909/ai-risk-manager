"""Phase 2J/3F — ML/graph case interface.

**Strict separation, enforced by type:** `Case` (PRODUCTION CASE DATA) is
what the future investigation agent will eventually see — it contains
ZERO synthetic ground-truth information, by construction (no field on
the dataclass could hold it). `CaseGroundTruth` (EVALUATION-ONLY) is a
completely separate object, built separately, used only by the Phase
3H/3I/3J evaluation scripts. There is no code path that merges them into
one object — this is a structural guarantee, not just a convention
(tested, `tests/unit/test_case_interface_leakage.py`).

**Real-time vs. retrospective (Phase 3L):** `ml_risk_score`/`ml_risk_tier`
are REAL-TIME features — computed from `src/features/` at transaction
time, using only strictly-past data (Phase 2's leak-safe historical
features). `graph_evidence` is RETROSPECTIVE INVESTIGATION evidence —
computed from `src/graph/signals.py` against the FULL graph (all
transactions, all times), so it may include relationships formed by
transactions that happened AFTER the trigger transaction. This is
appropriate for case investigation (an analyst benefits from the
complete picture) but `graph_evidence` must never be fed into
`src/features/` as if it were known at transaction time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass(frozen=True)
class GraphEvidence:
    """Deterministic, human-readable structural evidence (Phase 3G/3K) —
    no LLM involved in producing any field here."""

    community_id: int
    community_size: int
    n_shared_devices: int
    n_shared_ips: int
    n_shared_bank_accounts: int
    multi_attribute_overlap: bool
    relationship_rarity_score: float
    temporal_concentration_hours: float | None
    detected_relationship_types: list[str]
    narrative: str  # deterministic human-readable sentence, src/graph/explain.py


@dataclass(frozen=True)
class Case:
    """PRODUCTION CASE DATA — what the agent (Phase 4+) will eventually
    receive. No ground-truth field exists on this class."""

    case_id: str
    trigger_transaction_ids: list[int]
    trigger_transaction_dt: int  # real TransactionDT of the (first) trigger transaction — reproducible, not wall-clock
    ml_risk_score: float
    ml_risk_tier: str
    customer_proxy_id: str
    customer_proxy_confidence: str
    graph_lookup_keys: dict[str, str | None]
    graph_evidence: GraphEvidence | None  # None if this customer shares nothing with anyone


@dataclass(frozen=True)
class CaseGroundTruth:
    """EVALUATION-ONLY — never constructed alongside a Case in the same
    code path that would hand data to an agent. Used exclusively by
    Phase 3H/3I/3J evaluation scripts."""

    case_id: str
    original_isFraud: int
    synthetic_ring_id: str | None
    synthetic_abuse_type: str | None
    synthetic_ring_role: str | None
    legitimate_cluster_id: str | None
    legitimate_cluster_type: str | None
    synthetic_entity_label: str


def build_case_ground_truth(case_id: str, ground_truth_row: pd.Series) -> CaseGroundTruth:
    """ground_truth_row: a row from the synthetic-generator output
    (data/synthetic/full/transactions.parquet), NEVER from a feature
    matrix an agent would see."""

    def _get(col: str):
        val = ground_truth_row.get(col)
        return None if pd.isna(val) else val

    return CaseGroundTruth(
        case_id=case_id,
        original_isFraud=int(ground_truth_row["original_isFraud"]),
        synthetic_ring_id=_get("synthetic_ring_id"),
        synthetic_abuse_type=_get("synthetic_abuse_type"),
        synthetic_ring_role=_get("synthetic_ring_role"),
        legitimate_cluster_id=_get("legitimate_cluster_id"),
        legitimate_cluster_type=_get("legitimate_cluster_type"),
        synthetic_entity_label=str(ground_truth_row["synthetic_entity_label"]),
    )


def build_case(
    transaction_row: pd.Series,
    ml_risk_score: float,
    ml_risk_tier: str,
    graph_evidence: GraphEvidence | None,
) -> Case:
    """transaction_row: a row carrying real + derived-proxy + synthetic
    LOOKUP KEY columns (device_synthetic_id etc.) — those key VALUES are
    fine here (they're graph join keys, not ground-truth labels); the
    ground-truth LABEL columns (synthetic_ring_id etc.) are never read
    by this function.
    """
    txn_id = int(transaction_row["TransactionID"])
    return Case(
        case_id=f"CASE-{txn_id}",
        trigger_transaction_ids=[txn_id],
        trigger_transaction_dt=int(transaction_row["TransactionDT"]),
        ml_risk_score=float(ml_risk_score),
        ml_risk_tier=ml_risk_tier,
        customer_proxy_id=str(transaction_row["customer_proxy_id"]),
        customer_proxy_confidence=str(transaction_row["customer_proxy_confidence"]),
        graph_lookup_keys={
            "device_synthetic_id": transaction_row.get("device_synthetic_id"),
            "ip_synthetic_id": transaction_row.get("ip_synthetic_id"),
            "bank_account_synthetic_id": transaction_row.get("bank_account_synthetic_id"),
        },
        graph_evidence=graph_evidence,
    )
