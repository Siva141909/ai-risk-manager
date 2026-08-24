"""Phase 5A — deterministic case repository (Phase 5A.2/5A.13).

A repository abstraction, not a database — per the explicit instruction
that a database is not warranted just because listing/detail endpoints
exist. Wraps two already-frozen artifacts:

- `ToolDataContext` (`src/tools/context.py`, Phase 4C) — the same
  safe-column-only synthetic transaction table and graph signals the
  investigation agent's tools already read from.
- `data/processed/val_test_ml_scores.parquet` — Phase 2's frozen,
  out-of-sample calibrated ML scores (`scripts/score_val_test_for_graph_fusion.py`).

Only VALIDATION and TEST transactions are servable: they are the only
rows with an honest score (never used to fit the model). TRAIN-split
transactions have no out-of-sample score and are deliberately excluded
rather than re-scored here — this repository never runs inference, it
only serves what Phase 2/3 already computed and froze.

Every `Case` returned is built by the same, unmodified
`src/graph/case_interface.py::build_case` Phase 3/4 already use and
test — no case data is synthesized in this module, and `CaseGroundTruth`
is never imported here at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.graph.case_interface import Case, build_case
from src.graph.explain import build_evidence_and_narrative
from src.tools.context import ToolDataContext


@dataclass(frozen=True)
class CaseSummary:
    case_id: str
    transaction_id: int
    transaction_dt: int
    ml_risk_score: float
    ml_risk_tier: str
    graph_flagged: bool


class CaseNotServableError(LookupError):
    """Raised when a case_id/transaction_id has no frozen val/test score
    — distinct from a malformed case_id, so the API layer can return a
    precise 404 message either way."""


def case_id_for_transaction(transaction_id: int) -> str:
    return f"CASE-{transaction_id}"


def transaction_id_from_case_id(case_id: str) -> int:
    if not case_id.startswith("CASE-"):
        raise ValueError(f"malformed case_id (expected 'CASE-<transaction_id>'): {case_id!r}")
    suffix = case_id[len("CASE-") :]
    if not suffix.isdigit():
        raise ValueError(f"malformed case_id (expected 'CASE-<transaction_id>'): {case_id!r}")
    return int(suffix)


class CaseRepository:
    def __init__(self, ctx: ToolDataContext, val_test_scores: pd.DataFrame) -> None:
        self._ctx = ctx
        self._transactions_by_id = ctx.transactions_graph.set_index("TransactionID", drop=False)
        self._signals_by_customer = ctx.graph_signals.set_index("customer_proxy_id", drop=False)

        scores = val_test_scores[["TransactionID", "ml_score_calibrated", "ml_risk_tier"]].copy()
        self._scores_by_id = scores.set_index("TransactionID", drop=False)

        index = ctx.transactions_graph.merge(scores, on="TransactionID", how="inner")
        index = index.merge(
            ctx.graph_signals[["customer_proxy_id", "graph_flagged"]],
            on="customer_proxy_id", how="left",
        )
        index["graph_flagged"] = index["graph_flagged"].fillna(False)
        self._index = index

    @classmethod
    def from_project_root(cls, ctx: ToolDataContext, project_root: Path) -> "CaseRepository":
        scores_path = project_root / "data" / "processed" / "val_test_ml_scores.parquet"
        scores = pd.read_parquet(scores_path, columns=["TransactionID", "ml_score_calibrated", "ml_risk_tier"])
        return cls(ctx, scores)

    def list_cases(
        self,
        risk_tier: str | None = None,
        graph_flagged: bool | None = None,
        start_dt: int | None = None,
        end_dt: int | None = None,
        limit: int = 50,
        offset: int = 0,
        investigation_status: str | None = None,
        investigated_transaction_ids: set[int] | None = None,
    ) -> tuple[list[CaseSummary], int]:
        """`investigation_status`/`investigated_transaction_ids` MUST be
        applied here, before `total`/pagination are computed — filtering
        after `.iloc[offset:offset+limit]` (as an earlier version of
        this method's caller did, in `CaseService`) silently produces a
        wrong `total` and can return an empty page even when many
        matching rows exist elsewhere in the dataset, since the filter
        would only ever see the page's own (unrelated) rows."""
        df = self._index
        if risk_tier is not None:
            df = df[df["ml_risk_tier"] == risk_tier]
        if graph_flagged is not None:
            df = df[df["graph_flagged"] == graph_flagged]
        if start_dt is not None:
            df = df[df["TransactionDT"] >= start_dt]
        if end_dt is not None:
            df = df[df["TransactionDT"] <= end_dt]
        if investigation_status is not None:
            investigated_transaction_ids = investigated_transaction_ids or set()
            is_investigated = df["TransactionID"].isin(investigated_transaction_ids)
            df = df[is_investigated] if investigation_status == "investigated" else df[~is_investigated]

        total = len(df)
        page = df.sort_values("TransactionDT", kind="mergesort").iloc[offset : offset + limit]
        summaries = [
            CaseSummary(
                case_id=case_id_for_transaction(int(r.TransactionID)),
                transaction_id=int(r.TransactionID),
                transaction_dt=int(r.TransactionDT),
                ml_risk_score=float(r.ml_score_calibrated),
                ml_risk_tier=str(r.ml_risk_tier),
                graph_flagged=bool(r.graph_flagged),
            )
            for r in page.itertuples()
        ]
        return summaries, total

    def get_case_by_transaction_id(self, transaction_id: int) -> Case | None:
        if transaction_id not in self._scores_by_id.index:
            return None
        if transaction_id not in self._transactions_by_id.index:
            return None
        row = self._transactions_by_id.loc[transaction_id]
        score_row = self._scores_by_id.loc[transaction_id]

        customer_id = row["customer_proxy_id"]
        evidence = None
        if customer_id in self._signals_by_customer.index:
            evidence = build_evidence_and_narrative(self._signals_by_customer.loc[customer_id])

        return build_case(
            row,
            ml_risk_score=float(score_row["ml_score_calibrated"]),
            ml_risk_tier=str(score_row["ml_risk_tier"]),
            graph_evidence=evidence,
        )

    def get_case(self, case_id: str) -> Case | None:
        transaction_id = transaction_id_from_case_id(case_id)
        return self.get_case_by_transaction_id(transaction_id)
