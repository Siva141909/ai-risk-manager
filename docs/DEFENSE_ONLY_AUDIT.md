# Defense-Only Audit — Phase 5C, Requirement 10

Razorpay Track 02's bar states plainly: **"Strictly defense-only:
anything offense-capable is disqualified."** This document audits the
entire system against that bar, capability by capability, with
evidence — not an assertion.

## 1. What the system can do

| Capability | Where | Nature |
|---|---|---|
| Score a transaction's fraud risk | `src/models/` (frozen XGBoost + calibration) | Read-only computation over already-collected fields |
| Detect coordinated shared-infrastructure structure | `src/graph/` | Read-only computation over already-collected fields |
| Retrieve case/transaction/graph/policy evidence | `src/tools/implementations.py`, 10 tools | Read-only, see §2 |
| Investigate a case and produce a report | `src/agents/graph.py` (LangGraph) | Synthesizes retrieved evidence into a structured recommendation — never acts |
| Serve the above over HTTP | `src/api/` | One mutating route total, see §3 |

## 2. Every tool is read-only, by name and by construction

`src/tools/registry.py::TOOL_REGISTRY` has 10 entries; every one is
named `get_*` (`get_transaction_history`, `get_customer_context`,
`get_related_entities`, `get_graph_context`, `get_graph_neighbors`,
`get_temporal_activity`, `get_merchant_context`, `get_previous_cases`,
`get_risk_signals`, `get_policy`). None writes to any data source, none
calls an external payment/account API, none accepts a filesystem path
from the caller. Verified by an automated test that would fail if a
single non-`get_` tool were ever registered:
`tests/unit/test_defense_only_audit.py::test_every_registered_tool_is_read_only_by_name`.

## 3. Exactly one mutating API route exists, and it can only request an investigation

The entire FastAPI surface (`src/api/routers/`) has one non-GET route:
`POST /api/v1/cases/investigate`. There is no `PUT`, `PATCH`, or
`DELETE` route anywhere in the application — no code path exists to
freeze an account, reverse a payment, modify a case record, or write
anything at all. Verified by
`tests/unit/test_defense_only_audit.py::test_only_one_mutating_route_exists_and_it_is_investigate`,
which enumerates every registered route/method pair and asserts the
mutating set is exactly `{("/api/v1/cases/investigate", "POST")}`.

## 4. The agent cannot invoke a tool outside the allowlist

`src/tools/registry.py::ToolRegistry.call(name, raw_args)` checks `name`
against `ALLOWED_TOOL_NAMES` before doing anything else, and raises
`ToolAuthorizationError` for anything else — there is no dynamic
dispatch-by-string that could reach an unregistered function, and the
LLM is never given direct Python execution or a generic "call this
function" capability. See `docs/TOOL_CONTRACTS.md`.

## 5. No outbound write/attack capability exists anywhere in the codebase

A static scan of every file under `src/` (git-tracked source, not test
fixtures) finds zero occurrences of: `.charge(`, `.refund(`,
`.transfer(`, `.payout(`, account freeze/block/disable calls, raw
outbound `requests.post/put/delete` or `httpx.post/put/delete`,
`os.system`, unrestricted `subprocess.Popen`, or `eval`/`exec`. The one
`subprocess` call in the entire codebase
(`src/evaluation/track02_manifest.py`) is a fixed-argument, read-only
`git rev-parse HEAD` used only for evaluation provenance — no
shell=True, no user-controllable input, explicitly allowlisted in the
test rather than silently excluded. Verified by
`tests/unit/test_defense_only_audit.py::test_no_offensive_or_write_capable_code_anywhere_in_src`.

## 6. Human approval is structurally mandatory, not a UI convention

`InvestigationReport.human_approval_required_for_action` defaults to
`True` (`src/agents/schemas.py`) and the deterministic validation node
(`src/agents/safety.py::validate_investigation_report`) **rejects any
report that sets it to `False`** — this is enforced in code the LLM
does not control, not merely documented as a policy. Verified by
`tests/unit/test_defense_only_audit.py::test_human_approval_required_for_action_cannot_be_false`
and, at the schema level,
`tests/unit/test_defense_only_audit.py::test_investigation_report_schema_has_no_action_execution_field`
confirms the output schema has no field through which the agent could
even express "I executed/froze/blocked/transferred" anything — there is
no field to fill in for an action that was never possible to take.

## 7. The frontend cannot express an offensive action either

`frontend/src/services/apiClient.ts` exposes exactly the same one
mutating call (`investigate`) — its TypeScript request type
(`InvestigateRequest`) has no field for anything beyond
`transaction_id`/`case_id`/`investigation_mode`/`cutoff_dt`. The four
human-review action buttons in the UI (Approve/Request Further
Investigation/Mark Legitimate/Escalate) are rendered **visibly
disabled** because no backend endpoint exists for them
(`docs/FRONTEND_UX.md` §4, `docs/BACKEND_ARCHITECTURE.md` §10) — the
product deliberately does not fake a "this action succeeded" state for
a capability that doesn't exist.

## 8. Explicit non-negotiable boundaries carried from Phase 4, re-verified here

Restated from `docs/SAFETY_MODEL.md` §1, which this audit treats as
still-binding and re-checks rather than re-deriving:

- Never calculates/changes the ML risk score or risk tier — the agent
  reports `case.ml_risk_tier` verbatim, never `investigation_report.risk_tier`
  in isolation (`docs/DESIGN_SYSTEM.md` §7's rendering-source rule on
  the frontend side too).
- Never accesses `CaseGroundTruth` — structurally impossible
  (`docs/CASE_MODEL.md` §1).
- Never invents evidence — every citation traced to a real tool call
  (`docs/SAFETY_MODEL.md` §3).
- Never treats future data as real-time justification — the temporal
  boundary is enforced in tool-call filtering itself, not just
  documented (`docs/CASE_MODEL.md` §5/§7).

## 9. What "defense-only" means for this product, stated plainly

The system's only outputs are: a risk score, a structural coordination
signal, and a cited investigative report ending in a *recommendation*
that a human must act on through channels this system does not touch.
It cannot generate fraudulent transactions, execute an attack against a
merchant or payment system, bypass a payment control, exploit any
system, automate offensive activity, or provide attack instructions
(the agent's system prompt — `src/agents/graph.py::REPORT_SYSTEM_PROMPT`
— is scoped entirely to investigating a case it is given, with no
instruction-following surface for an unrelated request, and untrusted
input is wrapped and treated as data, never as instructions,
`docs/SAFETY_MODEL.md` §2).

## 10. Test coverage summary

| Check | Test |
|---|---|
| Only one mutating route exists (`POST /investigate`) | `test_only_one_mutating_route_exists_and_it_is_investigate` |
| Every tool is read-only by name | `test_every_registered_tool_is_read_only_by_name` |
| `human_approval_required_for_action=False` is rejected | `test_human_approval_required_for_action_cannot_be_false` |
| No offensive/write code pattern anywhere in `src/` | `test_no_offensive_or_write_capable_code_anywhere_in_src` |
| Output schema has no action-execution field | `test_investigation_report_schema_has_no_action_execution_field` |

All 5 pass (`tests/unit/test_defense_only_audit.py`), part of the
project's full automated suite.

**Conclusion: the system is investigate/evidence/explain/recommend/escalate
only, with human approval structurally required for anything
consequential. No offense-capable code path exists.**
