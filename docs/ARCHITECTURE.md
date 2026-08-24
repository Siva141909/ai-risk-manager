# Architecture — Phase 5C, Requirement 16

One end-to-end diagram, labeled by data provenance and processing kind,
per the explicit instruction not to let a diagram imply something is
real, derived, or AI-generated when it isn't.

```
┌─────────────────────────────────────────────────────────────────┐
│ REAL IEEE-CIS TRANSACTION DATA                                    │  REAL
│ data/raw/train_transaction.csv — 590,540 real rows, never modified │
└───────────────────────────────┬───────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ Synthetic / Derived Entity Layer                                    │  SYNTHETIC / DERIVED
│ src/generator/ — customer_proxy, device/IP/bank/address proxies,    │
│ 100 legitimate shared-infra clusters, 8 coordinated-abuse rings     │
│ injected on top of the real rows (real TransactionDT/Amt untouched) │
└──────────┬──────────────────────────────────────┬───────────────────┘
           │                                       │
           ▼                                       ▼
┌───────────────────────────┐         ┌─────────────────────────────────┐
│ Transaction Feature          │       │ Graph Construction                │  DETERMINISTIC
│ Engineering                    │      │ src/graph/relationship_views.py     │
│ src/features/ — leak-safe,      │     │ device/IP/bank_account projections,  │
│ strictly-past-only features     │     │ multi-attribute combined view        │
└──────────────┬──────────────────┘     └──────────────┬────────────────────┘
               │                                        │
               ▼                                        ▼
┌───────────────────────────┐         ┌─────────────────────────────────┐
│ XGBoost Risk Model            │       │ Coordination Detection             │  DETERMINISTIC
│ src/models/ — calibrated,       │     │ src/graph/ring_recovery.py,          │
│ frozen since Phase 2             │    │ src/graph/signals.py — connected     │
│ ml_risk_score, ml_risk_tier      │    │ components, community_size>=3        │
│ (SUPPORTING CONTEXT — Req. 11)   │    │ (PRIMARY DETECTOR — Req. 2)          │
└──────────────┬────────────────────┘   └──────────────┬────────────────────┘
               │                                        │
               └───────────────────┬────────────────────┘
                                    ▼
                    ┌───────────────────────────────────┐
                    │ Coordinated-Abuse Case                │  DETERMINISTIC
                    │ src/graph/case_interface.py::Case       │  (no ground truth —
                    │ ml_risk_score/tier + graph_evidence,     │   structurally guaranteed,
                    │ NEVER CaseGroundTruth                     │  docs/CASE_MODEL.md §1)
                    └──────────────────┬────────────────────────┘
                                       ▼
                    ┌───────────────────────────────────┐
                    │ LangGraph Investigation                │  DETERMINISTIC WORKFLOW
                    │ src/agents/graph.py — tool routing,      │  (orchestration only —
                    │ evidence collection, validation,          │   no reasoning here)
                    │ bounded repair-then-fail-safe              │
                    └──────────────────┬────────────────────────┘
                                       ▼
                    ┌───────────────────────────────────┐
                    │ Claude Agent                            │  AI
                    │ src/agents/llm_client.py — reasons over   │
                    │ retrieved evidence + RAG policy chunks,    │
                    │ NEVER sets risk tier, NEVER acts           │
                    └──────────────────┬────────────────────────┘
                                       ▼
                    ┌───────────────────────────────────┐
                    │ Evidence-Backed Investigation           │  AI OUTPUT,
                    │ src/agents/schemas.py::InvestigationReport│  DETERMINISTICALLY
                    │ every claim traced to a real tool call,    │  VALIDATED
                    │ validated before being returned             │  (src/agents/safety.py)
                    └──────────────────┬────────────────────────┘
                                       ▼
                    ┌───────────────────────────────────┐
                    │ Human Review                             │  HUMAN
                    │ human_approval_required_for_action=True    │
                    │ always — system recommends, never acts      │
                    └───────────────────────────────────────────┘
```

## Legend

| Label | Meaning |
|---|---|
| **REAL** | Unmodified IEEE-CIS transaction data — every real column is byte-identical before and after this pipeline touches it (`tests/integration/test_reproducibility.py`) |
| **SYNTHETIC / DERIVED** | Injected by `src/generator/` on top of real rows — proxy entity IDs, legitimate-cluster/ring membership. Never conflated with real fraud labels (`docs/CASE_MODEL.md`, `docs/SYNTHETIC_DATA_GENERATION.md`) |
| **DETERMINISTIC** | Pure functions of their inputs — no LLM involved, same input always produces the same output |
| **AI** | Claude, via the LangGraph investigation workflow — reasons over already-deterministic evidence, never determines a risk tier or acts |
| **HUMAN** | The only layer that can turn a recommendation into a real-world action |

## What this diagram is not

Not a deployment diagram (no deployment exists, `docs/BACKEND_ARCHITECTURE.md`
§10) and not a claim that the LLM contributes to detection — the
XGBoost model and the graph detector both produce their outputs with
zero LLM involvement (Requirement 11); the LLM layer begins only after
a `Case` already exists.

## Where each stage is proven, not just diagrammed

| Stage | Evidence |
|---|---|
| Real data untouched | `tests/integration/test_reproducibility.py` |
| Synthetic layer never leaks into ML features | `src/features/leakage_guard.py`, `tests/unit/test_ground_truth_and_leakage.py` |
| XGBoost frozen, calibrated | `docs/ML_BASELINE.md`, `docs/RISK_THRESHOLD_POLICY.md` |
| Graph detection frozen, held-out tested | `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3-6 |
| `Case` never carries ground truth | `docs/CASE_MODEL.md` §1, `tests/unit/test_case_interface_leakage.py` |
| LangGraph never sets risk tier | `docs/SAFETY_MODEL.md` §1, `tests/integration/test_agent_investigation_pipeline.py::test_risk_tier_in_final_report_matches_frozen_ml_tier_exactly` |
| Every AI claim evidence-validated | `docs/SAFETY_MODEL.md` §3, `tests/unit/test_agent_safety.py` |
| Human approval structurally required | `docs/DEFENSE_ONLY_AUDIT.md` §6 |
