# Case Model — Phase 2J/3F/3G/3K

---

## 1. PRODUCTION CASE DATA vs. EVALUATION-ONLY GROUND TRUTH

Two separate dataclasses (`src/graph/case_interface.py`), never merged
into one object anywhere in the codebase:

```python
@dataclass(frozen=True)
class Case:                     # PRODUCTION — what the agent (Phase 4+) will see
    case_id: str
    trigger_transaction_ids: list[int]
    trigger_transaction_dt: int          # real TransactionDT, not wall-clock
    ml_risk_score: float
    ml_risk_tier: str
    customer_proxy_id: str
    customer_proxy_confidence: str
    graph_lookup_keys: dict[str, str | None]
    graph_evidence: GraphEvidence | None

@dataclass(frozen=True)
class CaseGroundTruth:           # EVALUATION-ONLY — never passed to the agent
    case_id: str
    original_isFraud: int
    synthetic_ring_id: str | None
    synthetic_abuse_type: str | None
    synthetic_ring_role: str | None
    legitimate_cluster_id: str | None
    legitimate_cluster_type: str | None
    synthetic_entity_label: str
```

**This is a structural guarantee, not a convention.** `Case` has no
field that could hold a ground-truth value — verified directly by field-
name inspection
(`tests/unit/test_case_interface_leakage.py::test_case_dataclass_has_no_ground_truth_field`).
`build_case()` and `build_case_ground_truth()` are separate functions;
no code path constructs both from the same call, and no function returns
both together.

---

## 2. `GraphEvidence` — the interpretable signals (Phase 3G)

| Signal | Precise definition |
|---|---|
| `community_size` | Number of customer_proxy entities (including this one) in the same detected community of the frozen multi-attribute graph (`docs/GRAPH_BENCHMARK_FULL.md` §6) — "number of connected suspicious customers" |
| `n_shared_devices` | Count of distinct `device_synthetic_id` values this customer shares with ≥1 other customer |
| `n_shared_ips` | Same, for `ip_synthetic_id` |
| `n_shared_bank_accounts` | Same, for `bank_account_synthetic_id` |
| `multi_attribute_overlap` | `True` if this customer shares more than one relationship TYPE (device AND/OR ip AND/OR bank_account) with at least one other customer — directly tests the design doc's Section 8 "multi-attribute sharing is a stronger signal" hypothesis at the per-case level |
| `relationship_rarity_score` | `1 / mean(n_sharing across this customer's shared entities)` — higher = the customer's shared attributes are rarer (shared with fewer people), which is more suspicious than an attribute shared by hundreds |
| `temporal_concentration_hours` | `(max - min TransactionDT) / 3600` across this customer's OWN transactions — `None` if they have only one transaction (undefined, not zero) |
| `graph_flagged` | Deterministic: `community_size >= 3` (`src/graph/signals.py::GRAPH_FLAG_MIN_COMMUNITY_SIZE`) — matches the generator's own minimum configured ring size |

Computed by `src/graph/signals.py::compute_customer_graph_signals` —
pure function of the full synthetic-graph transaction table (device/IP/
bank_account/TransactionDT/customer_proxy_id columns only; verified to
never read `isFraud` or any `synthetic_*` ground-truth column,
`tests/unit/test_graph_no_target_leakage.py`).

---

## 3. Deterministic evidence narrative (Phase 3K) — no LLM

`src/graph/explain.py::build_narrative` fills a fixed template from
`GraphEvidence` — same input always produces the same output
(`tests/unit/test_graph_signals_and_explain.py::test_narrative_deterministic_same_input_same_output`).
This is the literal text the future investigation agent will cite from,
not paraphrase.

Example, generated (not hand-written) from
`data/synthetic/full/transactions.parquet`:

> *"5 customer proxies are connected through: 1 shared bank-account
> proxy. Insufficient repeat-transaction data to assess temporal
> concentration. Relationship rarity score: 1.000 (higher = rarer, more
> suspicious)."*

---

## 4. Worked example: real-time score vs. retrospective evidence

Transaction `3457202` (validation/test split), generated end-to-end via
`build_case` + `build_case_ground_truth`:

**`Case` (production, agent-visible):**
```
case_id='CASE-3457202'
trigger_transaction_ids=[3457202]
trigger_transaction_dt=12144110
ml_risk_score=0.0114          # real-time: from src/features/, Phase 2's frozen model
ml_risk_tier='MEDIUM'
customer_proxy_id='customer_proxy-customer_proxy-unresolved-3457202'
customer_proxy_confidence='mega_unresolved'
graph_lookup_keys={'device_synthetic_id': 'DEV-24873951',
                    'ip_synthetic_id': '149.83.4.38',
                    'bank_account_synthetic_id': 'BANK-6438701038'}
graph_evidence=GraphEvidence(community_size=4, n_shared_bank_accounts=1,
                              multi_attribute_overlap=False,
                              narrative='4 customer proxies are connected
                              through: 1 shared bank-account proxy...')
```

**`CaseGroundTruth` (evaluation-only, never sent to any agent):**
```
case_id='CASE-3457202'
original_isFraud=0                                  # NOT real fraud
synthetic_ring_id='RING-SHARED_BANK_ACCOUNT-000'      # but IS an injected ring
synthetic_ring_role='core_member'
synthetic_entity_label='ring_member'
```

**This is the concrete demonstration of `docs/ML_GRAPH_ABLATION.md`'s
central finding:** the ML score alone (0.011) gives no reason to
investigate this transaction. The graph evidence, computed independently
and without any access to `isFraud`, correctly surfaces that this
customer shares a bank account with 3 others — a structural signal
transaction-level scoring cannot produce.

---

## 5. Real-time features vs. retrospective investigation evidence (Phase 3L)

| | Real-time (ML features) | Retrospective (graph evidence) |
|---|---|---|
| Computed from | `src/features/` — strictly-past data relative to the trigger transaction's own `TransactionDT` (`src/features/historical.py`, leak-tested) | `src/graph/signals.py` — the FULL graph, all transactions, all times |
| May include information from transactions AFTER the trigger transaction? | **Never** — enforced and tested (`tests/unit/test_historical_features_leakage.py`, `tests/integration/test_pipeline_leakage.py`) | **Yes, by design** — a relationship discovered here may have been formed by a later transaction |
| Valid as a Phase 2 ML feature? | Yes — this is exactly what it's for | **No — never.** `src/graph/signals.py`'s output columns are structurally disjoint from `src/features/schema.py`'s allowed feature columns (tested, `tests/unit/test_graph_no_target_leakage.py::test_graph_evidence_columns_are_denylisted_as_ml_features_if_ever_merged`) |
| Valid as case investigation evidence? | Yes | Yes — this is exactly what it's for |

**The rule, stated plainly:** a relationship observed after a trigger
transaction cannot justify the *original real-time risk decision*
(`ml_risk_score`/`ml_risk_tier`, which are frozen at scoring time and
never recomputed with graph information) — but it CAN be surfaced as
retrospective investigation evidence once a case is opened, exactly the
`Case.graph_evidence` field's role. The two are different fields on the
same object precisely so this distinction survives into the data model,
not just into a design doc.

---

## 6. Leakage guarantees (Phase 3L) — full list

See `docs/LEAKAGE_PREVENTION.md` for Phase 2's 7 guarantees (still
enforced, untouched by Phase 3). Phase 3 adds:

| Guarantee | Mechanism | Test |
|---|---|---|
| `original_isFraud` not used in graph detection | `compute_customer_graph_signals`'s signature has no isFraud parameter; source contains no reference to it | `test_graph_no_target_leakage.py` (3 tests) |
| Synthetic ring labels not used to construct detection scores | `graph_flagged` is derived purely from `community_size` (structural), never from `synthetic_ring_id` | Same file |
| Ground-truth ring IDs are evaluation-only | `CaseGroundTruth` structurally separate from `Case` | `test_case_interface_leakage.py` (5 tests) |
| Graph thresholds selected without test labels | `GRAPH_FLAG_MIN_COMMUNITY_SIZE=3` is a fixed structural constant (matches the generator's own `size_min`), not fit from any data split at all | Code inspection — no fitting function exists for it |
| ML test predictions remain frozen | `scripts/ml_graph_ablation.py` loads the already-saved Phase 2 model/calibrator/thresholds and only ever calls `.predict`/`.transform` — no `.fit` call anywhere in the script | Code inspection; Phase 2's own model files are read-only inputs |
| No future transactions enter graph features for a case's REAL-TIME score | Real-time (`ml_risk_score`) and retrospective (`graph_evidence`) are separate fields, never combined into one "score" — §5 | `Case` dataclass structure itself |

---

## 7. Phase 4 addendum — how the investigation agent consumes `Case`

`Case` is the only object the Phase 4 investigation agent ever receives.
`src/agents/case_contract.py::build_agent_input(case: Case) -> AgentInput`
is the sole constructor of the agent's input, and its signature takes a
`Case` and nothing else — there is no call site anywhere that could pass
a `CaseGroundTruth` through, even by mistake (structural, not
conventional; tested by `tests/unit/test_agent_case_contract.py`).

**Detection evidence vs. investigation evidence** (a second distinction
layered on top of §5's real-time/retrospective split):

- **Detection evidence** — `AgentInput.detection_evidence`
  (`ml_risk_score`, `ml_risk_tier`, `graph_evidence`) — is exactly
  `Case`'s own fields, copied verbatim. This is what got the case
  created in the first place. It is fixed before the agent runs and the
  agent can only ever *report* it, never change it
  (`docs/SAFETY_MODEL.md` §1).
- **Investigation evidence** — whatever the agent's tool calls retrieve
  *during* the investigation (transaction history, related entities,
  policy chunks, graph neighbors). It did not exist as "evidence" until
  the agent asked for it, even though the underlying data existed all
  along. Every item carries its own `is_retrospective` flag
  (`docs/CASE_MODEL.md` §5's real-time/retrospective boundary, now
  applied per tool call rather than per feature).

The agent's introduction of the real-time/retrospective boundary at
tool-call granularity, its evidence-ID provenance model, and its 10-tool
authorization surface are documented in full in
`docs/AGENT_ARCHITECTURE.md`, `docs/TOOL_CONTRACTS.md`, and
`docs/SAFETY_MODEL.md`.
