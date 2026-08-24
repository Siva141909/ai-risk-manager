"""Phase 4C — the data context every tool reads from.

**Authorization boundary, enforced at construction, not per-tool:**
`ToolDataContext.transactions_graph` is built by SELECTING only safe
columns from the synthetic-graph transaction table — ground-truth
columns (`original_isFraud`, `synthetic_ring_id`, `synthetic_abuse_type`,
`synthetic_ring_role`, `legitimate_cluster_id`, `legitimate_cluster_type`,
`synthetic_entity_label`) are never loaded into this object at all, so
no tool built on top of it — however it's written — can leak them. This
is defense in depth on top of each tool's own output schema
(src/tools/schemas.py) never having a field for them.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

SAFE_GRAPH_COLUMNS = [
    "TransactionID", "TransactionDT", "TransactionAmt", "ProductCD",
    "customer_proxy_id", "customer_proxy_confidence",
    "device_synthetic_id", "ip_synthetic_id", "bank_account_synthetic_id",
]

SAFE_ML_COLUMNS = [
    "TransactionID", "TransactionDT", "TransactionAmt",
    "cust_txn_count_so_far", "cust_txn_count_prior_24h", "cust_time_since_last_txn",
]


def evidence_id(prefix: str, *parts: str) -> str:
    """Deterministic, short, stable evidence ID — same inputs always
    produce the same ID (Phase 4H: evidence IDs are never invented by
    the agent, only ever returned by a tool)."""
    material = ":".join(str(p) for p in parts)
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:8].upper()
    return f"{prefix}-{digest}"


@dataclass(frozen=True)
class ToolDataContext:
    transactions_graph: pd.DataFrame  # safe columns only — see SAFE_GRAPH_COLUMNS
    transactions_ml: pd.DataFrame      # safe columns only — see SAFE_ML_COLUMNS
    graph_signals: pd.DataFrame          # src/graph/signals.py output — no ground truth by construction
    case_risk_signals: dict[str, dict]     # {case_id: {"ml_risk_score":..., "ml_risk_tier":..., "rule_flags": {...}}}

    def transaction_by_id(self, transaction_id: int) -> pd.Series | None:
        rows = self.transactions_graph[self.transactions_graph["TransactionID"] == transaction_id]
        return rows.iloc[0] if len(rows) else None


def load_tool_data_context(
    project_root: Path,
    full_synthetic_parquet: Path | None = None,
    features_parquet: Path | None = None,
) -> ToolDataContext:
    full_synthetic_parquet = full_synthetic_parquet or project_root / "data" / "synthetic" / "full" / "transactions.parquet"
    features_parquet = features_parquet or project_root / "data" / "processed" / "features.parquet"

    synthetic = pd.read_parquet(full_synthetic_parquet, columns=SAFE_GRAPH_COLUMNS)
    features = pd.read_parquet(features_parquet, columns=SAFE_ML_COLUMNS)

    from src.graph.signals import compute_customer_graph_signals

    signals = compute_customer_graph_signals(synthetic)

    return ToolDataContext(
        transactions_graph=synthetic,
        transactions_ml=features,
        graph_signals=signals,
        case_risk_signals={},
    )
