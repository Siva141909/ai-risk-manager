# Agent Evaluation — Phase 4P/4Q/4U

## 1. The evaluation rule this document follows

Per the explicit instruction governing this phase: pipeline, safety,
tool, and evidence-validation correctness are proven by the automated
pytest suite (deterministic, `StubLLMClient`, already passing — see
`docs/AGENT_ARCHITECTURE.md` §6) and are **not** re-reported here as
agent quality. This document separates five categories and states
plainly which backend proved each one:

| Category | What it proves | Backend used |
|---|---|---|
| A. Pipeline correctness | Graph wiring, state transitions, early-stop routing | STUB TEST (pytest) |
| B. Safety correctness | Injection defense, evidence validation, fail-safe bounds | STUB TEST (pytest) |
| C. Tool correctness | Allowlisting, schema validation, budget/repeat limits, no ground-truth leakage | STUB TEST (pytest) |
| D. Evidence validation | Every citation traces to a real tool call; no invented IDs | STUB TEST (pytest) |
| E. Actual investigative reasoning quality | Whether the agent's findings/recommendations are *good* | **CLAUDE DEVELOPMENT RUN only** (via `ClaudeAgentSDKClient`) |

**Only category E required real Claude.** The stub cannot be used to
claim anything about reasoning quality — it is a template filler, not a
reasoner, and every stub output is prefixed `"STUB TEST:"` for exactly
this reason.

## 2. Fixed evaluation set (Phase 4P)

12 categories, curated by the technical lead's specification (not
selected by the model), against real `TransactionID`s identified from
`data/synthetic/full/` ground truth (`scripts/run_agent_evaluation.py::EVAL_CASES`):

1. Strong abuse ring
2. Weak ring / noise member
3. Legitimate household (shared infra, non-fraud)
4. Legitimate office (shared infra, non-fraud)
5. Legitimate campus (shared infra, non-fraud)
6. Legitimate business (shared infra, non-fraud)
7. ML-high AND graph-high — **no real example exists in this benchmark**
   (confirmed identical to Phase 3's quadrant-D-empty finding,
   `docs/ML_GRAPH_ABLATION.md` §6, via the actual `graph_flagged`
   signal, not just ground-truth membership). Constructed as an
   explicitly-labeled synthetic test (`force_graph_evidence=True`) to
   exercise agent behavior on this hypothetical combination — never
   presented as a real detected case.
8. ML-low, graph-high (the conflicting-signal quadrant)
9. ML-high, graph-low
10. ML-low, graph-low (routine close)
11. Conflicting evidence (same ring member as #1, scored as if ML saw
    nothing — an explicit test of whether the agent surfaces the
    conflict rather than silently picking one signal)
12. Missing/sparse data

Configurations run per case:
- **A** — deterministic graph evidence only, no synthesis
- **B** — graph evidence + `src/graph/explain.py` template narrative, no LLM
- **C-stub** — full investigation graph, `StubLLMClient`
- **C-claude** — full investigation graph, `ClaudeAgentSDKClient` (real
  Claude, CLAUDE DEVELOPMENT RUN)

## 3. Results (as run 2026-08-24 — CLOSURE run, session limit reset)

All 12/12 stub runs passed validation (proves the pipeline handles every
category structurally). **All 12/12 real-Claude (category E) runs are
now complete** — cases 1–7 from the original Phase 4 run, cases 8–12
from the closure run after the Claude Code session limit reset (error
text and timing of the original failure documented in the git history
of this file; not repeated here since it is now moot).

| Category | ML tier | Graph evidence | Stub recommendation | **Claude recommendation** | Status | Latency | Tool calls |
|---|---|---|---|---|---|---|---|
| 1 strong_abuse_ring | MEDIUM | Y | investigate_further | **escalate_to_human_analyst** | passed | 53.7s | 11 |
| 2 weak_ring_noise_member | LOW | N | close | **monitor** | passed | 19.1s | 5 |
| 3 legitimate_household | LOW | Y | investigate_further | **investigate_further** | passed | 44.5s | 9 |
| 4 legitimate_office | LOW | Y | investigate_further | **investigate_further** | passed | 58.7s | 9 |
| 5 legitimate_campus | LOW | Y | investigate_further | **investigate_further** | passed | 55.8s | 9 |
| 6 legitimate_business | LOW | Y | investigate_further | **investigate_further** | passed | 42.5s | 10 |
| 7 ml_high_graph_high (SYNTHETIC) | CRITICAL | Y | escalate_to_human_analyst | **escalate_to_human_analyst** | passed | 51.6s | 11 |
| 8 ml_low_graph_high | MEDIUM | Y | investigate_further | **investigate_further** | passed | 45.3s | 9 |
| 9 ml_high_graph_low | CRITICAL | N | escalate_to_human_analyst | **escalate_to_human_analyst** | passed | 38.2s | 5 |
| 10 ml_low_graph_low | LOW | N | close | **monitor** | passed | 35.6s | 5 |
| 11 conflicting_evidence | LOW | Y | investigate_further | **escalate_to_human_analyst** | passed | 49.9s | 11 |
| 12 missing_data | LOW | N | close | **close** | passed | 20.1s | 5 |

**12/12 real-Claude runs completed and passed deterministic validation**
(category A–D checks) on top of being real reasoning (category E).

**Average latency: approximately 42.9 seconds** (arithmetic mean of the
12 per-case latencies in the table above: 53.7, 19.1, 44.5, 58.7, 55.8,
42.5, 51.6, 45.3, 38.2, 35.6, 49.9, 20.1 — sums to 515.0s / 12).
**This is measured development-run latency from this evaluation batch,
not a production SLA** — no production deployment exists
(`docs/BACKEND_ARCHITECTURE.md` §10), and this figure reflects the
`claude_agent_sdk` development backend under the conditions this
evaluation ran (sequential calls, no concurrency, no caching warm-up).
It should not be read as a guaranteed or optimized response time for
any live system.

`requires_human_review=True` in 11 of 12 cases — only case 12
(genuinely empty evidence, no graph, no risk signals, no history beyond
the single flagged transaction) results in `close` /
`requires_human_review=False`. This pattern is discussed critically in
§5 (Agent value test) — it is not simply reported as a success metric.

**Demo-case impact:** the 5-case demo set (`DEMO_CASE_CATEGORIES`) is
now fully complete with real-Claude results: `1_strong_abuse_ring`,
`3_legitimate_household`, `8_ml_low_graph_high`,
`11_conflicting_evidence`, `12_missing_data` — all `validation_status=passed`.

## 4. Manual qualitative review — all 12 cases, full report text

Per-case assessment against the 9 required criteria: (1) evidence
correctness, (2) evidence completeness, (3) reasoning value beyond
template narrative, (4) legitimate explanations considered, (5)
conflicts recognized, (6) policy citation relevance, (7) unsupported
claims, (8) recommendation follows evidence, (9) uncertainty represented
appropriately. Based on reading the full `InvestigationReport` JSON for
every case (`data/processed/agent_evaluation/evaluation_results.json`),
not just the recommendation label.

**General findings across all 12 cases:**

- **(7) Unsupported claims: none found.** Every entity/transaction/policy
  reference in every report's free text resolves to an evidence item
  the deterministic validator also independently confirmed
  (`docs/SAFETY_MODEL.md` §3) — no hallucinated IDs in any of the 12
  reports, consistent with the 12/12 `validation_status=passed` result.
  Interpretive language ("consistent with card-testing," "atypical of
  normal purchasing behavior") is judgment, not fabricated fact, and is
  always tied back to a cited evidence item.
- **(2) Evidence completeness** is consistently strong: every case calls
  all 5 core-evidence tools, and every case with graph evidence also
  calls `get_related_entities`, `get_graph_neighbors` (once per detected
  relationship type — up to 3 calls), and `get_policy`. No case
  under-investigates relative to what was available to it.
- **(9) Uncertainty is represented well and consistently**: every report
  explicitly distinguishes "no data" from "confirmed normal" (e.g. case
  8: "This should be read as 'insufficient behavioral data' rather than
  'confirmed normal behavior'"; case 2's summary states the same
  distinction) rather than defaulting sparse evidence to a clean bill of
  health. `confidence` scores are also honest about this — no case
  claims confidence above 0.55, including the strongest-evidence case
  (case 1).
- **(3) Reasoning value beyond template narrative — the strongest
  positive finding.** Case 7 is the clearest evidence of this: the
  agent independently called `get_graph_context`/`get_graph_neighbors`
  and discovered they **contradicted** the pre-computed
  `graph_evidence` block it was handed (`found=false`, no neighbors,
  vs. a claimed 5-node multi-attribute community) — it did not simply
  restate the given narrative, it cross-checked it against live tool
  data and explicitly reported the discrepancy as a conflict
  (`GRAPH-CTX-75BFE00A`). It also correctly identified the embedded
  `"SYNTHETIC TEST CONSTRUCTION..."` annotation in that narrative as
  untrusted data content and stated plainly that it did not let it
  influence the conclusion — real evidence the injection-defense
  architecture (`docs/SAFETY_MODEL.md` §2) holds in practice, not just
  in the adversarial unit tests. Separately, both case 7 and case 9
  (same underlying transaction, `3400379`, framed once with and once
  without graph evidence) independently discovered the same real
  signal — 7 consecutive identical-$1331 transactions in a tight
  window — purely from `get_transaction_history`/`get_temporal_activity`,
  a genuine behavioral finding neither config A nor config B ever
  surfaces, since neither queries transaction history at all.
- **(4)/(5)/(6) Legitimate explanations, conflict recognition, and
  policy citation** are present and topically correct in every case
  with graph evidence (1, 3–8, 11) — household/office/campus/business/
  shared-account explanations are matched to the actual relationship
  type found (device vs. IP vs. bank account), and the same 3 policy
  chunks (`POLICY-205BCBFC` escalation criteria,
  `POLICY-7ED833BD` false-positive guidance,
  `POLICY-E3752D9E` conflict-handling) are retrieved and cited
  consistently, appropriately reused across cases since the corpus is
  small and these are the genuinely relevant sections for a
  shared-infrastructure query.

**A material negative finding — (8) recommendation-vs-evidence
inconsistency across structurally similar cases.** Cases 2 and 12 have
nearly identical evidence shapes: singleton customer, 1 known
transaction, `get_transaction_history` returns an *empty list* despite
`n_total_known=1` (the same latent data-inconsistency in both), no
graph evidence, no risk signals, no prior cases. Case 2 sets
`conflicting_evidence=true` ("this internal inconsistency suggests a
data resolution or pipeline issue... limits confidence") and recommends
`monitor`; case 12 sets `conflicting_evidence=false` ("no conflicting
evidence was identified... all evidence points toward a low-risk,
low-information case") over the *same underlying data pattern* and
recommends `close`. This is not a validation failure (both reports are
internally consistent and evidence-grounded) but it is a real
reasoning-quality gap: the same structural ambiguity is flagged in one
case and waved through in the other, with no evident case-specific
reason for the difference. A production deployment would need either a
deterministic rule for this specific data-inconsistency pattern (so it
isn't left to per-call LLM judgment) or to accept this as a source of
recommendation variance between otherwise-similar cases.

**A second, broader negative finding — over-triggering / low
specificity on "conflicting evidence."** 10 of 12 cases are marked
`conflicting_evidence=true`, including every case with *any* graph
evidence regardless of strength — cases 3, 4, and 5 each have only a
**single shared attribute** (`multi_attribute_overlap=false`), a LOW ML
tier, and no confirmed temporal concentration, which is exactly the
profile `docs/policy_documents/03_false_positive_guidance.md` describes
as a candidate for closing, not escalating. The agent retrieves and
cites that exact guidance in all three cases, then recommends
`investigate_further` anyway rather than `close`, with reasoning that
amounts to "a single-attribute overlap alone doesn't meet the escalation
bar, but I still won't close it" — the policy citation is topically
correct (criterion 6 above is satisfied) but the agent's own stated
escalation criteria (from `POLICY-205BCBFC`, which it correctly quotes
as *not* met) don't actually support the recommendation it reaches. A
reviewer using config A/B alone (`graph_flagged=true`, low ML score)
would likely reach the same "needs a look" conclusion in seconds, making
the ~9-tool, ~45–58s investigation's *marginal* recommendation-level
value small for cases 3–6 specifically, even though the underlying
report content (§ finding above) is genuinely richer. This is discussed
further in §5.

## 5. Agent value test (Phase 4Q) — A vs. B vs. C, not forced positive

Configuration A (raw graph evidence) and B (template narrative, no LLM)
give a reviewer the same underlying facts as configuration C but with
zero synthesis — no legitimate-explanation reasoning, no conflict
detection, no policy citation, no independently-gathered behavioral
evidence.

**Where C provides clear, material value over A/B:**
- **No-graph-evidence cases (2, 9, 10, 12):** A and B are contentless
  here (`graph_evidence_raw: null`, narrative "No graph evidence
  available") — a reviewer using only A/B has *nothing* case-specific
  to go on beyond the bare ML score. C independently investigates
  transaction/temporal history and, in cases 9 and 12, reaches a
  differentiated, evidence-grounded conclusion (escalate vs. close)
  that A/B cannot produce at all. This is the strongest case for the
  agent's value — it is doing real work A/B structurally cannot do.
- **Case 7:** C caught a live contradiction between the pre-computed
  graph narrative and direct tool verification that A/B would have
  silently passed through as fact (A/B only ever render the given
  `graph_evidence`, they never independently query the graph tools to
  check it). This is a genuine correctness improvement over the
  non-agent baseline, not just a richer narrative.

**Where C's value over A/B is marginal or unclear:**
- **Cases 3–6 (single-attribute, low-ML shared-infrastructure):** as
  detailed in §4, C reaches the same practical "needs a look"
  conclusion a reviewer would get from A/B's `graph_flagged=true` alone,
  at ~45–59s of latency and 9–10 tool calls per case, and the specific
  recommendation (`investigate_further`) doesn't cleanly follow from the
  escalation criteria it itself cites as unmet. The richer report text
  (legitimate explanations, named policy sections) is real added value
  *if a human reads the full report*, but adds little if only the
  recommendation label is consumed downstream.
- **Cases 2 vs. 12 inconsistency (§4):** undermines the case that C's
  judgment is more reliable than a simple deterministic rule would be
  for this specific "empty transaction history despite `n_total_known=1`"
  pattern — a fixed rule would at least be consistent.

**Cost side, stated plainly:** 19–59s latency per case for a real
Claude call vs. near-instant for A/B, and a real operational failure
mode surfaced during this evaluation (the original Phase 4 run hit a
Claude Code session limit on 5/12 cases, resolved only by waiting for
the limit to reset and re-running — documented for transparency even
though the closure run now shows 12/12 complete).

**Conclusion, not forced positive:** the agent provides clear,
demonstrable value on cases where config A/B has *no* case-specific
signal to offer (no graph evidence) or where a pre-computed input needs
independent verification (case 7). Its value is much thinner — arguably
not worth the latency — on cases where a human would reach the same
practical conclusion from the raw graph flag alone, and the cases-2-vs-12
inconsistency shows the agent's judgment is not yet perfectly reliable
even within its own stated reasoning. Recommend keeping the agent step
but not assuming its recommendation label alone is sufficient for
low-signal shared-infrastructure cases without a human reading the full
report — and treating the two negative findings above as concrete,
open items rather than resolving them by prompt-tuning within this
frozen-implementation closure task (see the covering report for why
the implementation was intentionally not touched here).

## 6. Observability (Phase 4R)

`langsmith` is present as a transitive dependency of `langgraph` but was
not wired up — it requires its own API key, which is out of scope for
the same reason `ANTHROPIC_API_KEY` was: not required to be requested
from the user for this phase. The practical fallback is structured
logging via the project's existing `src/logging_conf.py` pattern
(established in earlier phases) plus the `ToolRegistry.call_log` /
`InvestigationState` fields already captured on every run
(`tool_outputs`, `validation_errors`, `validation_attempts`,
`injection_signals_detected`, `llm_backend`), which together give full
per-investigation traceability without an external tracing service.

## 7. Status and known limitations (Phase 4 CLOSURE)

**12/12 real-Claude cases complete.** All 5 previously-incomplete cases
(8–12) were re-run against the unmodified `ClaudeAgentSDKClient`, using
the exact same `EVAL_CASES` specs, tool configuration, prompts, RAG
corpus, and validation rules as the original Phase 4 run — no
implementation change was made to obtain these results. No execution
bug was encountered; the original 5 failures were confirmed to be a
Claude Code session-limit condition that had genuinely cleared by the
time of the closure run (verified: cases 8–12 now complete with normal
19–58s latencies, consistent with the successful pattern from cases
1–7, not the ~2s immediate-rejection pattern seen in the original
failures).

**Known limitations, not fixed by this closure task (frozen
implementation, per the closure instructions):**
- The cases-2-vs-12 recommendation inconsistency (§4) — same evidence
  shape, different `conflicting_evidence` conclusion.
- Apparent over-triggering of `conflicting_evidence`/`investigate_further`
  on single-attribute, low-ML shared-infrastructure cases (3–6), where
  the agent's own cited escalation criteria don't support the
  recommendation it reaches (§4, §5).
- `AnthropicAPIClient` remains unexercised (no `ANTHROPIC_API_KEY`
  available in this environment) — noted in `docs/AGENT_ARCHITECTURE.md`,
  unchanged by this closure task.

These are documented as open findings for a future phase, not silently
resolved or hidden — per the explicit instruction governing this
closure task, no prompts, thresholds, or agent logic were changed in
response to any individual case result.
