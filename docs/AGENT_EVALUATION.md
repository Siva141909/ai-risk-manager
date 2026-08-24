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

## 3. Results (as run 2026-08-24)

All 12/12 stub runs passed validation (proves the pipeline handles every
category structurally). Real-Claude (category E) results:

| Category | ML tier | Graph evidence | Stub recommendation | **Claude recommendation** | Status | Latency | Tool calls |
|---|---|---|---|---|---|---|---|
| 1 strong_abuse_ring | MEDIUM | Y | investigate_further | **escalate_to_human_analyst** | passed | 53.7s | 11 |
| 2 weak_ring_noise_member | LOW | N | close | **monitor** | passed | 19.1s | 5 |
| 3 legitimate_household | LOW | Y | investigate_further | **investigate_further** | passed | 44.5s | 9 |
| 4 legitimate_office | LOW | Y | investigate_further | **investigate_further** | passed | 58.7s | 9 |
| 5 legitimate_campus | LOW | Y | investigate_further | **investigate_further** | passed | 55.8s | 9 |
| 6 legitimate_business | LOW | Y | investigate_further | **investigate_further** | passed | 42.5s | 10 |
| 7 ml_high_graph_high (SYNTHETIC) | CRITICAL | Y | escalate_to_human_analyst | **escalate_to_human_analyst** | passed | 51.6s | 11 |
| 8 ml_low_graph_high | MEDIUM | Y | investigate_further | — | **ERROR** | 2.5s | 9 (before error) |
| 9 ml_high_graph_low | CRITICAL | N | escalate_to_human_analyst | — | **ERROR** | 2.0s | 5 (before error) |
| 10 ml_low_graph_low | LOW | N | close | — | **ERROR** | 2.8s | 5 (before error) |
| 11 conflicting_evidence | LOW | Y | investigate_further | — | **ERROR** | 2.1s | 11 (before error) |
| 12 missing_data | LOW | N | close | — | **ERROR** | 2.2s | 5 (before error) |

**7/12 real-Claude runs completed and passed deterministic validation
(category A–D checks) on top of being real reasoning (category E).**
5/12 (cases 8–12) failed with:

```
ResultError: Claude Code returned an error result:
You've hit your session limit · resets 12:50am (Asia/Calcutta) (exit code: 1)
```

This is a genuine Claude Code session/usage limit on the development
account running these 12 sequential real-Claude investigations (each
involving multiple tool-call round trips reflected in the prompt), not
a pipeline or code defect — confirmed by the abnormally short latency
(~2–2.8s, consistent with an immediate session-limit rejection) versus
the 19–59s latency of the 7 successful runs, and by the exact error text
being a Claude Code session-limit message, not a validation or schema
error. Per the explicit instruction governing this phase, these 5 are
reported honestly as **incomplete**, not backfilled with stub output
relabeled as real, and not silently omitted from this table.

**Demo-case impact:** the 5-case demo set (Phase 4U,
`DEMO_CASE_CATEGORIES`) reuses 5 of these categories to avoid duplicate
real-API calls — `1_strong_abuse_ring`, `3_legitimate_household`,
`8_ml_low_graph_high`, `11_conflicting_evidence`, `12_missing_data`.
Categories 8, 11, and 12 are among the failed runs, so **3 of 5 demo
cases currently lack a real-Claude result** and need a re-run once the
session limit resets. Categories 1 and 3 have complete real-Claude
results.

## 4. Qualitative observations from the 7 completed real-Claude runs

- **Case 1 (strong abuse ring)**: stub recommended `investigate_further`
  (its fixed conflict-detection template treats any MEDIUM/LOW tier +
  graph evidence as conflicting); Claude recommended
  `escalate_to_human_analyst` — a stronger, better-justified conclusion
  given `graph_flagged=True` and multi-attribute overlap, showing the
  real model weighing the graph evidence more heavily than the
  template's blanket rule.
- **Case 2 (weak ring / noise member, no graph evidence)**: stub
  defaulted to `close` (its template: LOW tier + no graph evidence
  → close); Claude recommended `monitor` — a more conservative
  middle ground the fixed template has no path to produce, suggesting
  the real model is reasoning about behavioral signals the template
  ignores entirely.
- **Cases 3–6 (legitimate shared-infrastructure scenarios)**: stub and
  Claude agree on `investigate_further` in all four — expected, since
  the stub's conflict-detection rule (MEDIUM/LOW tier + graph evidence
  present) happens to match a reasonable actual recommendation here
  regardless of *why*. This is exactly the category where category-E
  quality differences would matter most (does the agent correctly cite
  the false-positive-guidance policy chunks and identify household/
  office/campus/business explanations, not just reach the same label as
  the template?) and is worth a closer manual read of the full report
  text (`data/processed/agent_evaluation/evaluation_results.json`)
  before final sign-off, not just the recommendation label.
- **Case 7 (synthetic ML-high + graph-high)**: both agree
  `escalate_to_human_analyst` — the case is constructed to be
  unambiguous by design, so agreement here is expected and not strong
  evidence of reasoning quality by itself.

## 5. Non-agent vs. agent comparison (Phase 4Q)

Configuration A (raw graph evidence) and B (template narrative, no LLM)
give a human reviewer the same underlying facts as configuration C but
with zero synthesis — no legitimate-explanation reasoning, no conflict
detection, no policy citation, no recommendation. The agent
configuration (C) adds: (1) an explicit `conflicting_evidence` flag
with a stated reason when ML and graph signals disagree, absent from A/B
entirely; (2) policy citations grounding a recommendation in
`docs/policy_documents/`, which A/B never reference; (3) a
`legitimate_explanations` list attempting to account for shared
infrastructure before recommending escalation, which A/B present as raw
signal only, undifferentiated from a genuine ring. The cost is latency
(19–59s per case for a real Claude call, vs. instant for A/B) and,
for 5/12 cases in this run, complete failure due to the external session
limit — a real operational tradeoff worth stating plainly, not glossed
over.

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

## 7. Remaining work before this document is final

- Re-run cases 8, 9, 10, 11, 12 against `ClaudeAgentSDKClient` once the
  Claude Code session limit resets, and update the results table and
  the demo-case set with genuine results.
- Do a manual qualitative read of the full report text (not just the
  recommendation label) for cases 3–6, where stub and Claude agreed on
  the label but the *reasoning* is what actually differentiates a real
  agent from the template.
