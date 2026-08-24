"""Phase 4C/4D — the 10 read-only investigation tools.

Every tool: (a) takes a validated Pydantic input, (b) returns a
validated Pydantic output, (c) is a pure function of `ToolDataContext` +
input (deterministic — same input always produces the same output),
(d) never touches ground-truth columns (not present in the context at
all, src/tools/context.py), (e) never writes anything.

**Real-time vs. retrospective (Phase 4E):** tools that accept
`cutoff_dt` filter strictly to `TransactionDT < cutoff_dt` when it is
set (real-time mode) — this is enforced in the filtering logic itself,
not just documented. When `cutoff_dt` is `None`, the tool operates in
retrospective mode and its output is always tagged `mode="retrospective"`
so callers (and the agent's own report) can never confuse the two.
"""

from __future__ import annotations

import pandas as pd

from src.tools.context import ToolDataContext, evidence_id
from src.tools.schemas import (
    CustomerContextInput,
    CustomerContextOutput,
    GraphContextInput,
    GraphContextOutput,
    GraphNeighbor,
    GraphNeighborsInput,
    GraphNeighborsOutput,
    MerchantContextInput,
    MerchantContextOutput,
    PolicyChunk,
    PolicyQueryInput,
    PolicyQueryOutput,
    PreviousCase,
    PreviousCasesInput,
    PreviousCasesOutput,
    RelatedEntitiesInput,
    RelatedEntitiesOutput,
    RelatedEntity,
    RiskSignal,
    RiskSignalsInput,
    RiskSignalsOutput,
    TemporalActivityInput,
    TemporalActivityOutput,
    TransactionHistoryInput,
    TransactionHistoryOutput,
    TransactionRecord,
)

RELATIONSHIP_ENTITY_COLUMNS = {
    "SHARED_DEVICE": "device_synthetic_id",
    "SHARED_IP": "ip_synthetic_id",
    "SHARED_BANK_ACCOUNT": "bank_account_synthetic_id",
}


def _customer_rows(ctx: ToolDataContext, customer_proxy_id: str, cutoff_dt: int | None) -> pd.DataFrame:
    rows = ctx.transactions_graph[ctx.transactions_graph["customer_proxy_id"] == customer_proxy_id]
    if cutoff_dt is not None:
        rows = rows[rows["TransactionDT"] < cutoff_dt]
    return rows.sort_values("TransactionDT", kind="mergesort")


def get_transaction_history(ctx: ToolDataContext, inp: TransactionHistoryInput) -> TransactionHistoryOutput:
    all_known = _customer_rows(ctx, inp.customer_proxy_id, cutoff_dt=None)
    rows = _customer_rows(ctx, inp.customer_proxy_id, inp.cutoff_dt).head(inp.max_results)
    records = [
        TransactionRecord(
            evidence_id=evidence_id("TXN", str(r.TransactionID)),
            transaction_id=int(r.TransactionID),
            transaction_dt=int(r.TransactionDT),
            amount=float(r.TransactionAmt),
            product_cd=str(r.ProductCD),
        )
        for r in rows.itertuples()
    ]
    return TransactionHistoryOutput(
        customer_proxy_id=inp.customer_proxy_id,
        mode="real_time" if inp.cutoff_dt is not None else "retrospective",
        transactions=records,
        n_total_known=len(all_known),
    )


def get_customer_context(ctx: ToolDataContext, inp: CustomerContextInput) -> CustomerContextOutput:
    rows = ctx.transactions_graph[ctx.transactions_graph["customer_proxy_id"] == inp.customer_proxy_id]
    if len(rows) == 0:
        return CustomerContextOutput(
            evidence_id=evidence_id("CUST", inp.customer_proxy_id),
            customer_proxy_id=inp.customer_proxy_id,
            customer_proxy_confidence="unknown",
            total_known_transactions=0,
            found=False,
        )
    return CustomerContextOutput(
        evidence_id=evidence_id("CUST", inp.customer_proxy_id),
        customer_proxy_id=inp.customer_proxy_id,
        customer_proxy_confidence=str(rows.iloc[0]["customer_proxy_confidence"]),
        total_known_transactions=len(rows),
        found=True,
    )


def _shared_entities_for_customer(ctx: ToolDataContext, customer_proxy_id: str) -> list[tuple[str, str, int]]:
    """Returns (entity_type, entity_value, n_customers_sharing) for every
    entity this customer shares with at least one other customer."""
    rows = ctx.transactions_graph[ctx.transactions_graph["customer_proxy_id"] == customer_proxy_id]
    results = []
    for rel_type, col in RELATIONSHIP_ENTITY_COLUMNS.items():
        values = rows[col].dropna().unique()
        for value in values:
            sharing = ctx.transactions_graph[ctx.transactions_graph[col] == value]["customer_proxy_id"].nunique()
            if sharing > 1:
                results.append((rel_type.replace("SHARED_", "").lower(), str(value), int(sharing)))
    return results


def get_related_entities(ctx: ToolDataContext, inp: RelatedEntitiesInput) -> RelatedEntitiesOutput:
    shared = _shared_entities_for_customer(ctx, inp.customer_proxy_id)
    entities = [
        RelatedEntity(
            evidence_id=evidence_id("GRAPH-ENTITY", inp.customer_proxy_id, entity_type, entity_value),
            entity_type=entity_type,
            entity_value=entity_value,
            n_customers_sharing=n,
        )
        for entity_type, entity_value, n in shared
    ]
    return RelatedEntitiesOutput(customer_proxy_id=inp.customer_proxy_id, entities=entities)


def get_graph_context(ctx: ToolDataContext, inp: GraphContextInput) -> GraphContextOutput:
    rows = ctx.graph_signals[ctx.graph_signals["customer_proxy_id"] == inp.customer_proxy_id]
    if len(rows) == 0:
        return GraphContextOutput(evidence_id=evidence_id("GRAPH-CTX", inp.customer_proxy_id), found=False)
    r = rows.iloc[0]
    from src.graph.explain import build_evidence_and_narrative

    narrative_evidence = build_evidence_and_narrative(r)
    return GraphContextOutput(
        evidence_id=evidence_id("GRAPH-CTX", inp.customer_proxy_id),
        found=True,
        community_id=int(r["community_id"]),
        community_size=int(r["community_size"]),
        n_shared_devices=int(r["n_shared_devices"]),
        n_shared_ips=int(r["n_shared_ips"]),
        n_shared_bank_accounts=int(r["n_shared_bank_accounts"]),
        multi_attribute_overlap=bool(r["multi_attribute_overlap"]),
        relationship_rarity_score=float(r["relationship_rarity_score"]),
        temporal_concentration_hours=(
            float(r["temporal_concentration_hours"]) if pd.notna(r["temporal_concentration_hours"]) else None
        ),
        graph_flagged=bool(r["graph_flagged"]),
        narrative=narrative_evidence.narrative,
    )


def get_graph_neighbors(ctx: ToolDataContext, inp: GraphNeighborsInput) -> GraphNeighborsOutput:
    if inp.relationship_type not in RELATIONSHIP_ENTITY_COLUMNS:
        return GraphNeighborsOutput(
            customer_proxy_id=inp.customer_proxy_id, relationship_type=inp.relationship_type, neighbors=[]
        )
    col = RELATIONSHIP_ENTITY_COLUMNS[inp.relationship_type]
    own_rows = ctx.transactions_graph[ctx.transactions_graph["customer_proxy_id"] == inp.customer_proxy_id]
    own_values = own_rows[col].dropna().unique()

    neighbors = []
    for value in own_values:
        sharing_rows = ctx.transactions_graph[ctx.transactions_graph[col] == value]
        n_sharing = sharing_rows["customer_proxy_id"].nunique()
        others = sharing_rows[sharing_rows["customer_proxy_id"] != inp.customer_proxy_id]
        for r in others.itertuples():
            neighbors.append(
                GraphNeighbor(
                    evidence_id=evidence_id("GRAPH-NBR", inp.customer_proxy_id, str(r.TransactionID)),
                    neighbor_customer_proxy_id=str(r.customer_proxy_id),
                    relationship_type=inp.relationship_type,
                    shared_entity_value=str(value),
                    n_customers_sharing_this_entity=int(n_sharing),
                    neighbor_transaction_id=int(r.TransactionID),
                    neighbor_transaction_dt=int(r.TransactionDT),
                )
            )
    neighbors = neighbors[: inp.max_results]
    return GraphNeighborsOutput(
        customer_proxy_id=inp.customer_proxy_id, relationship_type=inp.relationship_type, neighbors=neighbors
    )


def get_temporal_activity(ctx: ToolDataContext, inp: TemporalActivityInput) -> TemporalActivityOutput:
    rows = ctx.transactions_ml[
        ctx.transactions_ml["TransactionID"].isin(
            ctx.transactions_graph.loc[
                ctx.transactions_graph["customer_proxy_id"] == inp.customer_proxy_id, "TransactionID"
            ]
        )
    ]
    if inp.cutoff_dt is not None:
        rows = rows[rows["TransactionDT"] < inp.cutoff_dt]
    if len(rows) == 0:
        return TemporalActivityOutput(
            evidence_id=evidence_id("TEMPORAL", inp.customer_proxy_id, str(inp.cutoff_dt)),
            customer_proxy_id=inp.customer_proxy_id,
            mode="real_time" if inp.cutoff_dt is not None else "retrospective",
            txn_count_so_far=None,
            txn_count_prior_24h=None,
            time_since_last_txn_seconds=None,
            found=False,
        )
    latest = rows.sort_values("TransactionDT", kind="mergesort").iloc[-1]
    return TemporalActivityOutput(
        evidence_id=evidence_id("TEMPORAL", inp.customer_proxy_id, str(inp.cutoff_dt)),
        customer_proxy_id=inp.customer_proxy_id,
        mode="real_time" if inp.cutoff_dt is not None else "retrospective",
        txn_count_so_far=int(latest["cust_txn_count_so_far"]) if pd.notna(latest["cust_txn_count_so_far"]) else None,
        txn_count_prior_24h=(
            float(latest["cust_txn_count_prior_24h"]) if pd.notna(latest["cust_txn_count_prior_24h"]) else None
        ),
        time_since_last_txn_seconds=(
            float(latest["cust_time_since_last_txn"]) if pd.notna(latest["cust_time_since_last_txn"]) else None
        ),
        found=True,
    )


def get_merchant_context(ctx: ToolDataContext, inp: MerchantContextInput) -> MerchantContextOutput:
    n = int((ctx.transactions_graph["ProductCD"] == inp.product_cd).sum())
    return MerchantContextOutput(
        evidence_id=evidence_id("MERCHANT", inp.product_cd),
        product_cd=inp.product_cd,
        n_transactions_observed=n,
        note=(
            "ProductCD is a 5-value product-category code, not a real merchant identity "
            "(docs/FEATURE_AUDIT.md) — this is category-level context only."
        ),
    )


def get_previous_cases(ctx: ToolDataContext, inp: PreviousCasesInput) -> PreviousCasesOutput:
    """No persisted case-tracking system exists yet (Phase 4 is the first
    agent phase) — this returns prior HIGH/CRITICAL-tier transactions for
    the same customer_proxy_id as a documented proxy for case history,
    not a claim that a real case database was queried."""
    rows = ctx.transactions_ml[
        ctx.transactions_ml["TransactionID"].isin(
            ctx.transactions_graph.loc[
                ctx.transactions_graph["customer_proxy_id"] == inp.customer_proxy_id, "TransactionID"
            ]
        )
    ]
    if inp.cutoff_dt is not None:
        rows = rows[rows["TransactionDT"] < inp.cutoff_dt]

    cases = []
    for r in rows.itertuples():
        risk_info = ctx.case_risk_signals.get(f"CASE-{r.TransactionID}")
        tier = risk_info["ml_risk_tier"] if risk_info else "UNKNOWN"
        if tier in ("HIGH", "CRITICAL"):
            cases.append(
                PreviousCase(
                    evidence_id=evidence_id("PREV-CASE", str(r.TransactionID)),
                    case_id=f"CASE-{r.TransactionID}",
                    transaction_id=int(r.TransactionID),
                    transaction_dt=int(r.TransactionDT),
                    risk_tier_at_time=tier,
                )
            )
    return PreviousCasesOutput(
        customer_proxy_id=inp.customer_proxy_id,
        mode="real_time" if inp.cutoff_dt is not None else "retrospective",
        previous_cases=cases,
        note="Proxy for case history (no persisted case database exists yet) — see docstring.",
    )


def get_risk_signals(ctx: ToolDataContext, inp: RiskSignalsInput) -> RiskSignalsOutput:
    info = ctx.case_risk_signals.get(inp.case_id)
    if not info:
        return RiskSignalsOutput(case_id=inp.case_id, signals=[])
    signals = [
        RiskSignal(
            evidence_id=evidence_id("RISK-SIGNAL", inp.case_id, key),
            signal_type=key,
            value=str(value),
        )
        for key, value in info.items()
    ]
    return RiskSignalsOutput(case_id=inp.case_id, signals=signals)


def get_policy(ctx: ToolDataContext, inp: PolicyQueryInput, corpus) -> PolicyQueryOutput:
    """corpus: src/rag/retrieval.py::PolicyCorpus — passed in rather than
    stored on ToolDataContext, since it's a separate, independently
    testable subsystem (Phase 4K)."""
    results = corpus.retrieve(inp.query, applies_to_pattern=inp.applies_to_pattern, top_k=inp.max_results)
    chunks = [
        PolicyChunk(
            evidence_id=evidence_id("POLICY", r.doc_id, r.section_id),
            citation=f"[POLICY:{r.doc_id}#{r.section_id}]",
            doc_id=r.doc_id,
            section_id=r.section_id,
            text=r.text,
            similarity_score=round(r.score, 4),
        )
        for r in results
    ]
    return PolicyQueryOutput(query=inp.query, chunks=chunks)
