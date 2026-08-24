"""Phase 5A.13 — deterministic demo dataset.

Five real transaction IDs, verified servable through `CaseRepository`
(i.e. each has a frozen validation/test-split ML score,
`data/processed/val_test_ml_scores.parquet`) and confirmed by direct
query to have the shape its label claims (see the confirmation query in
the Phase 5A commit history) — chosen from the actual repository, not
invented. No `InvestigationReport` is hand-authored here: this module
only names which cases to demo. Producing an actual report for one of
these always means calling the real pipeline — either
`POST /api/v1/cases/investigate`, or, for local seeding,
`scripts/seed_demo_investigations.py`, which calls the exact same
`InvestigationService.investigate` the API route calls.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoCase:
    label: str
    transaction_id: int
    description: str


DEMO_CASES: list[DemoCase] = [
    DemoCase(
        label="strong_coordinated_ring",
        transaction_id=3410549,
        description=(
            "11-member community sharing both a device and an IP (multi-attribute overlap), "
            "MEDIUM ML tier — the clearest coordinated-abuse shape in the demo set."
        ),
    ),
    DemoCase(
        label="legitimate_household",
        transaction_id=3452855,
        description=(
            "5-member community linked by a single shared IP only, LOW ML tier — the shape "
            "docs/policy_documents/03_false_positive_guidance.md describes as a household/office "
            "false-positive candidate, not a ring."
        ),
    ),
    DemoCase(
        label="ml_low_graph_high",
        transaction_id=3457202,
        description=(
            "4-member community sharing a bank account, MEDIUM ML tier but a low individual score "
            "— the quadrant ML scoring alone would miss (docs/ML_GRAPH_ABLATION.md)."
        ),
    ),
    DemoCase(
        label="conflicting_evidence",
        transaction_id=3416834,
        description=(
            "3-member community sharing a device, MEDIUM ML tier — structural and behavioral "
            "signals in tension, the shape Phase 4's evaluation found the agent should surface "
            "explicitly rather than silently resolve."
        ),
    ),
    DemoCase(
        label="missing_data",
        transaction_id=3400406,
        description=(
            "Singleton customer proxy, 1 known transaction, no graph evidence, LOW ML tier — "
            "the sparse-data case with almost nothing to investigate."
        ),
    ),
]
