"""Phase 3K — deterministic graph evidence narratives.

No LLM. Every sentence is built from a fixed template filled with the
Phase 3G signals — same input always produces the same output
(tested). This is the source of truth the future investigation agent
will cite from, not paraphrase or embellish.
"""

from __future__ import annotations

import pandas as pd

from src.graph.case_interface import GraphEvidence


def _relationship_counts_phrase(evidence: GraphEvidence) -> str:
    parts = []
    if evidence.n_shared_devices > 0:
        parts.append(f"{evidence.n_shared_devices} shared device{'s' if evidence.n_shared_devices != 1 else ''}")
    if evidence.n_shared_ips > 0:
        parts.append(f"{evidence.n_shared_ips} shared IP{'s' if evidence.n_shared_ips != 1 else ''}")
    if evidence.n_shared_bank_accounts > 0:
        parts.append(
            f"{evidence.n_shared_bank_accounts} shared bank-account proxy"
            f"{'ies' if evidence.n_shared_bank_accounts != 1 else ''}".replace("proxyies", "proxies")
        )
    if not parts:
        return "no shared infrastructure"
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + f", and {parts[-1]}"


def build_narrative(evidence: GraphEvidence) -> str:
    """Deterministic template — no free-form generation."""
    sentence_1 = (
        f"{evidence.community_size} customer proxies are connected through: "
        f"{_relationship_counts_phrase(evidence)}."
    )

    if evidence.temporal_concentration_hours is not None:
        sentence_2 = (
            f" Transactions in this group span {evidence.temporal_concentration_hours:.1f} hours."
        )
    else:
        sentence_2 = " Insufficient repeat-transaction data to assess temporal concentration."

    sentence_3 = ""
    if evidence.multi_attribute_overlap:
        sentence_3 = " Multiple relationship types overlap for at least one member of this group."

    rarity_note = ""
    if evidence.relationship_rarity_score > 0:
        rarity_note = f" Relationship rarity score: {evidence.relationship_rarity_score:.3f} (higher = rarer, more suspicious)."

    return sentence_1 + sentence_2 + sentence_3 + rarity_note


def build_evidence_and_narrative(signals_row: pd.Series) -> GraphEvidence:
    """signals_row: one row from src/graph/signals.py's compute_customer_graph_signals output."""
    relationship_types = []
    if signals_row["n_shared_devices"] > 0:
        relationship_types.append("SHARED_DEVICE")
    if signals_row["n_shared_ips"] > 0:
        relationship_types.append("SHARED_IP")
    if signals_row["n_shared_bank_accounts"] > 0:
        relationship_types.append("SHARED_BANK_ACCOUNT")

    evidence = GraphEvidence(
        community_id=int(signals_row["community_id"]),
        community_size=int(signals_row["community_size"]),
        n_shared_devices=int(signals_row["n_shared_devices"]),
        n_shared_ips=int(signals_row["n_shared_ips"]),
        n_shared_bank_accounts=int(signals_row["n_shared_bank_accounts"]),
        multi_attribute_overlap=bool(signals_row["multi_attribute_overlap"]),
        relationship_rarity_score=float(signals_row["relationship_rarity_score"]),
        temporal_concentration_hours=(
            float(signals_row["temporal_concentration_hours"])
            if pd.notna(signals_row["temporal_concentration_hours"])
            else None
        ),
        detected_relationship_types=relationship_types,
        narrative="",
    )
    # dataclass is frozen -> build narrative after, then replace via a fresh instance
    return GraphEvidence(**{**evidence.__dict__, "narrative": build_narrative(evidence)})
