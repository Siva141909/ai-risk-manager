"""Phase 2J — ML/graph interface (schema only).

Per the approved Phase 2 architecture, ML risk scoring and graph ring
detection are NOT combined into one flow yet — this module only defines
the interface the next phase will consume: for a scored transaction, the
risk score/tier plus the entity identifiers and graph lookup keys needed
to later join into the multi-attribute graph
(device + IP + bank_account, per Phase 1.5's `docs/GRAPH_BENCHMARK.md`
recommendation).

**Graph labels stay hidden from the ML model, always.** `CaseRecord` is
built by combining (a) the ML model's OWN output (risk_score, risk_tier
— computed from features that never included any synthetic/graph
column, src/features/leakage_guard.py) with (b) identifiers read
directly off the original transaction row — never anything derived
from or influenced by the model.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CaseRecord:
    transaction_id: int
    risk_score: float
    risk_tier: str  # LOW / MEDIUM / HIGH / CRITICAL — from src/models/thresholds.py, deterministic
    customer_proxy_id: str
    customer_proxy_confidence: str
    payment_instrument_proxy_id: str
    graph_lookup_keys: dict[str, str | None]  # device/ip/bank_account synthetic IDs — for Phase 3's graph join


def build_case_record(transaction_row: pd.Series, risk_score: float, risk_tier: str) -> CaseRecord:
    """transaction_row: one row of the full feature-pipeline output
    (src/features/pipeline.py's artifact.df) — has the synthetic entity
    columns available for lookup purposes even though they were never
    part of the model's feature matrix.
    """
    return CaseRecord(
        transaction_id=int(transaction_row["TransactionID"]),
        risk_score=float(risk_score),
        risk_tier=risk_tier,
        customer_proxy_id=str(transaction_row["customer_proxy_id"]),
        customer_proxy_confidence=str(transaction_row["customer_proxy_confidence"]),
        payment_instrument_proxy_id=str(transaction_row["payment_instrument_proxy_id"]),
        graph_lookup_keys={
            "device_synthetic_id": transaction_row.get("device_synthetic_id"),
            "ip_synthetic_id": transaction_row.get("ip_synthetic_id"),
            "bank_account_synthetic_id": transaction_row.get("bank_account_synthetic_id"),
        },
    )


def build_case_records(
    df: pd.DataFrame, risk_scores: pd.Series, risk_tiers: pd.Series
) -> list[CaseRecord]:
    """Batch version — df is the feature-pipeline output (or a slice of
    it) aligned index-for-index with risk_scores/risk_tiers.
    """
    return [
        build_case_record(row, risk_scores.loc[idx], risk_tiers.loc[idx])
        for idx, row in df.iterrows()
    ]
