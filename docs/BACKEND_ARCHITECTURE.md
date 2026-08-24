# Backend Architecture — Phase 5A

## 1. Layering

```
FastAPI routes (src/api/routers/)
   ↓  (validate request, call one service, shape response — no business logic)
Application services (src/api/services.py)
   ↓  (orchestrate, time, cache, translate exceptions — no ML/graph/agent logic)
Existing deterministic pipeline
   - src/graph/case_interface.py (Case, build_case)     — Phase 2J/3F
   - src/tools/ (ToolRegistry, 10 tools)                — Phase 4C/4D/4G
   - src/rag/ (PolicyCorpus)                              — Phase 4K
   - src/agents/graph.py (LangGraph investigation agent)   — Phase 4F, FROZEN
   ↓
Structured response (src/api/schemas.py — reuses src.agents.schemas.InvestigationReport)
```

No route handler imports `src.agents`, `src.tools`, `src.graph`, or
`src.models` directly — only `src/api/services.py` and
`src/api/repository.py` do (checked directly,
`tests/api/test_security.py`'s AST-based `CaseGroundTruth`-isolation
test uses the same scanning approach and could be extended to enforce
this import boundary too). No XGBoost, graph-algorithm, LangGraph node,
RAG, or tool logic is implemented inside `src/api/routers/` — every
handler is a thin validate → call-one-service → shape-response
translation.

## 2. Case data source (Phase 5A.2/5A.13)

`CaseRepository` (`src/api/repository.py`) serves **validation/test-split
transactions only** — the only rows with an honest, out-of-sample
calibrated ML score (`data/processed/val_test_ml_scores.parquet`,
produced by `scripts/score_val_test_for_graph_fusion.py`, Phase 3).
TRAIN-split transactions were used to fit the model and have no honest
score; they are deliberately excluded rather than re-scored live — this
repository never runs inference, it only serves what Phase 2/3 already
computed and froze. This is a repository abstraction, not a database
(explicit Phase 5A.2 instruction) — an in-memory `pandas` index built
once at process startup from the same `ToolDataContext` the
investigation tools already use (`src/tools/context.py`, unmodified).

Every `Case` returned is built by the unmodified
`src/graph/case_interface.py::build_case` — no case data is synthesized
in the API layer, and `CaseGroundTruth` is never imported anywhere
under `src/api/` (enforced by an AST-based test,
`tests/api/test_security.py::test_case_ground_truth_never_imported_anywhere_in_api_layer`).

## 3. `investigation_mode` / `cutoff_dt` — a deliberate design constraint

The frozen Phase 4 agent (`src/agents/graph.py::node_validate_case`)
always uses the case's own trigger-transaction timestamp as its
real-time tool-call boundary — there is no code path in the frozen
implementation for an independently chosen cutoff or a "retrospective"
investigation mode. Rather than extend that frozen logic to add one
(explicitly out of scope for Phase 5A — "do not modify the evaluated
ML/graph/agent behavior"), the API's `investigation_mode` field accepts
only `"real_time"` today, and an optional `cutoff_dt` is accepted only
if it exactly matches the case's own trigger timestamp — anything else
returns `400 unsupported_investigation_mode`. This is a documented,
honest constraint, not a silent limitation: the field exists in the
contract (satisfying "optional cutoff timestamp where appropriate") but
is validated rather than pretended to do something the frozen agent
doesn't support. A real retrospective mode is a Phase 5B candidate that
would require touching `src/agents/graph.py` itself.

## 4. Async / long-running agent (Phase 5A.6) — decision

`POST /api/v1/cases/investigate` is **synchronous** — it runs the full
investigation and returns the complete result in one request. No
`/investigations` job-polling abstraction was built.

**Why:** Phase 4's evaluation measured real-Claude investigation
latency consistently at 19–59 seconds across 12/12 cases, and the
runtime already reliably completes within that window (no case ever
hung or needed cancellation across two full Phase 4 evaluation runs).
A synchronous request comfortably fits within normal HTTP client/server
timeout defaults when the client is configured with a modest read
timeout by the demo/frontend integrating with this API. Building a job
queue, polling storage, and a second endpoint would be real
infrastructure for a workload that doesn't need it yet at this scale
(Phase 5A.6's own "do not introduce distributed infrastructure, keep it
simple").

**How the API still respects the fact that this isn't instant:**
- The route is `async def` and runs the blocking investigation via
  `starlette.concurrency.run_in_threadpool`, so one slow investigation
  never blocks the event loop from serving other requests concurrently.
- A configurable timeout (`RISK_MANAGER_INVESTIGATION_TIMEOUT_SECONDS`,
  default 90s) wraps the call (`asyncio.wait_for`) and maps a timeout to
  `504 investigation_timeout`, not a hang.
- The response's `processing.total_duration_ms`/`agent_duration_ms`
  fields report real elapsed time, never fabricated as instantaneous.
- The result is cached (§5) so a client re-requesting the same
  investigation gets an instant cache hit, not another 20-60s wait.

**When this would need to change:** if concurrent demo usage grows
past what a handful of threadpool workers can hold open at once, or if
a UI needs to show live progress rather than "please wait," a
`POST /investigations` + `GET /investigations/{id}` job abstraction is
the natural Phase 5B extension — deliberately not built now.

## 5. Caching (Phase 5A.7)

`InvestigationCache` (`src/api/cache.py`) is a simple in-process,
thread-safe dict — not distributed, per Phase 5A.6/5A.7's "keep it
simple." Cache key = `(case_id, investigation_mode, llm_backend,
MODEL_VERSION, GRAPH_CONFIG_VERSION)` — a result computed under one
LLM backend or frozen-artifact version is never served back for a
different one. Since `investigation_mode` currently has exactly one
valid value and the version labels are process-wide constants, this
reduces in practice to "one cached report per (case_id, backend)" —
correct today, and already shaped so that a future second mode or a
version bump invalidates old entries automatically rather than
silently mixing them.

## 6. Error handling (Phase 5A.5)

See `src/api/errors.py` for the full exception hierarchy and status-code
mapping. The one design point worth restating: **the frozen agent's own
deterministic evidence/report validation failure
(`validation_status="failed_human_review"`, Phase 4N) is NOT an HTTP
error** — it is the fail-safe behavior itself, returned as a normal
`200 InvestigationResponse` with `requires_human_review=true` and
`recommendation="escalate_to_human_analyst"`. Converting that into an
HTTP error would remove the fail-safe behavior Phase 5A.5 explicitly
requires the API to preserve, not add safety.
`AgentExecutionError`/`LLMUnavailableError` are for the different case
where the LLM transport itself raises (session limits, connectivity) —
tested with a fake raising client, never live Claude
(`tests/api/test_errors.py`).

## 7. Security controls (Phase 5A.8) — mapped to enforcement point

| Control | Enforcement |
|---|---|
| No client-controlled risk tier / graph score | Every request schema has `extra="forbid"` (`src/api/schemas.py`) — an unrecognized field like `ml_risk_tier` in a request body is rejected with 422 before any handler runs, tested directly |
| Allowed enum values only | `Literal`/regex-pattern `Query` params (risk_tier, investigation_status) |
| No arbitrary SQL | No SQL exists anywhere in this project — pandas only (grep-tested) |
| No arbitrary tool invocation | Tool calls only ever originate inside `run_investigation`'s frozen LangGraph nodes; no route exposes "call tool X with args Y" |
| No arbitrary filesystem access | No route or service accepts a file path from client input |
| Request size limits | `BodySizeLimitMiddleware` (`src/api/security_mw.py`), Content-Length pre-check, 413 over the configured limit |
| `CaseGroundTruth` isolation | Never imported under `src/api/` at all (AST-checked test) |

## 8. Observability (Phase 5A.9)

`RequestLoggingMiddleware` (`src/api/logging_mw.py`) logs one structured
JSON line per request (`request_id`, method, path, status, duration).
The investigation route additionally logs `case_id`, `llm_backend`,
`cache_hit`, `agent_duration_ms`, and `validation_status` — never
transaction amounts, evidence text, or report content. Uses the
project's existing `src/logging_conf.py` convention, extended
additively (a new optional `extra=` merge in `JsonFormatter`) rather
than replaced.

## 9. Configuration (Phase 5A.10)

`src/api/config.py::Settings`, built from environment variables, never
inline in route code. `RISK_MANAGER_LLM_BACKEND` (`stub` default,
`claude_agent_sdk`, or `anthropic_api`) selects the backend exactly the
way `docs/AGENT_ARCHITECTURE.md`'s three `LLMClient` implementations
already work — no code changed to add this, the API layer just chooses
which one to construct. **No `ANTHROPIC_API_KEY` is required for the
default development workflow** — `stub` needs nothing, and
`claude_agent_sdk` needs only the local Claude Code authentication this
whole project has used since Phase 4.

## 10. What Phase 5A deliberately did not build

- A database (Postgres/etc.) — a repository abstraction over the
  existing frozen parquet files is sufficient at this scale (explicit
  instruction).
- A job queue for long-running investigations (§4).
- A retrospective investigation mode (§3) — would require touching the
  frozen agent.
- Authentication/authorization on the API itself — out of scope for
  this phase's instructions; noted as a Phase 5B/production gap in the
  Phase 5A report, not silently assumed away.
