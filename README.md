# AI Risk Manager — Razorpay AI Buildathon 2026, Track 2

Implementation of the system described in
[`ai_risk_manager_system_design.md`](ai_risk_manager_system_design.md),
which is the authoritative source of truth for this project's architecture.
If code and design doc ever disagree, the design doc wins unless a
documented, reported deviation says otherwise (see `docs/` for any such
deviations, e.g. TF-IDF instead of FAISS for RAG retrieval — `docs/RAG_POLICY.md`).

**Razorpay AI Buildathon Track 02 — one class of loss claimed:
coordinated payment fraud / abuse-ring detection.** Not returns, not
chargebacks, not generic fraud — see
[`docs/RAZORPAY_TRACK_02_COMPLIANCE.md`](docs/RAZORPAY_TRACK_02_COMPLIANCE.md)
for the full requirement-by-requirement compliance evidence, including
held-out-test precision/recall/F1/false-positive cost.

**One sentence:** fraud models score one transaction at a time; this
system also finds the accounts secretly working together, and produces
a cited, human-checkable investigation — not just a score — behind a
clean REST API, before any consequence occurs.

## Status: Phase 5C — Razorpay Track 02 compliance locked

| Phase | What it built | Status |
|---|---|---|
| 0 | Repo scaffold, dataset acquisition, feasibility audit | done |
| 1 | Temporal split, entity model, synthetic ring/legitimate-cluster generator, graph benchmark | done |
| 2 | ML baseline (rules, logistic regression, XGBoost), calibration, cost-driven risk thresholds | done |
| 3 | Graph signals, ML+graph ablation at full benchmark scale | done |
| 4 | Investigation agent: LangGraph + 10 tools + RAG policy retrieval + safety/evidence validation, evaluated with real Claude | done ([`docs/AGENT_EVALUATION.md`](docs/AGENT_EVALUATION.md)) |
| 5A | FastAPI backend around the frozen Phase 2-4 pipeline | done ([`docs/BACKEND_ARCHITECTURE.md`](docs/BACKEND_ARCHITECTURE.md)) |
| 5B | React frontend, real-Claude end-to-end demo | done ([`docs/DEMO_FLOW.md`](docs/DEMO_FLOW.md)) |
| 5C | Track 02 compliance: genuinely held-out graph-detector evaluation, defense-only audit, repo safety check | done ([`docs/RAZORPAY_TRACK_02_COMPLIANCE.md`](docs/RAZORPAY_TRACK_02_COMPLIANCE.md)) |
| 5D+ | GitHub push, pitch video, submission | not started |

No ML/graph/agent/RAG/evaluation behavior was changed to build the
Phase 5A/5B layers — the API is a thin, tested layer around what Phase
2-4 already built and proved (`docs/BACKEND_ARCHITECTURE.md` §1), and
the frontend talks to that API only — no domain logic, no CSV access,
no ground-truth exposure (`docs/FRONTEND_ARCHITECTURE.md` §4).

## Architecture

```
FastAPI routes (src/api/routers/)
   ↓  validate request, call one service, shape response — no business logic
Application services (src/api/services.py)
   ↓  orchestrate, time, cache, translate exceptions — no ML/graph/agent logic
Existing deterministic pipeline
   Case generation (src/graph/case_interface.py, Phase 2J/3F)
   → Investigation agent (src/agents/graph.py, LangGraph, Phase 4F — FROZEN)
   → Structured response (src/api/schemas.py, reuses src.agents.schemas.InvestigationReport)
```

Full detail: [`docs/BACKEND_ARCHITECTURE.md`](docs/BACKEND_ARCHITECTURE.md).
API reference: [`docs/API.md`](docs/API.md). Agent internals:
[`docs/AGENT_ARCHITECTURE.md`](docs/AGENT_ARCHITECTURE.md).

## Repository layout

```
data/{raw,synthetic,processed}/   # raw IEEE-CIS (gitignored), generator output, feature tables, frozen ML scores
configs/                          # seed.yaml, paths.yaml, generator.yaml
src/
  ingestion/ generator/ features/ models/ graph/   # Phases 1-3: data, ML, graph
  agents/ tools/ rag/                                # Phase 4: LangGraph investigation agent, tools, RAG
  api/                                                 # Phase 5A: FastAPI backend (this phase)
  evaluation/                                           # ablation runner, cost model
tests/{unit,integration,api}/       # 223 Phase 1-5A tests, all deterministic
notebooks/                        # EDA, not shipped code
scripts/                          # pipeline/evaluation/demo-seeding entrypoints
frontend/                         # Phase 5B: Vite + React + TypeScript, src/{app,pages,components,hooks,services,types}/
docs/                             # architecture, audit, evaluation, and design-deviation docs
```

## Environment

- Python 3.14.3, dependencies in `requirements.txt`.
- No GPU/CUDA dependency (XGBoost is CPU-trained).
- **No `ANTHROPIC_API_KEY` is required for the default development
  workflow at any phase of this project** — see "LLM backend options"
  below.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
```

## Running the API

```bash
uvicorn src.api.main:app --reload
# then: http://127.0.0.1:8000/docs (interactive OpenAPI)
```

Defaults to the deterministic stub LLM backend — safe, free, no
credential. See [`docs/DEVELOPMENT_RUNBOOK.md`](docs/DEVELOPMENT_RUNBOOK.md)
for the full setup/run/demo-seeding guide.

## LLM backend options

Provider-agnostic (`src/agents/llm_client.py::LLMClient`), selected via
`RISK_MANAGER_LLM_BACKEND`:

| Backend | Use for | Credential |
|---|---|---|
| `stub` (default) | Automated tests, CI, exercising the API without cost/latency | none |
| `claude_agent_sdk` | Real investigations — live demo, real evaluation | none (local Claude Code auth) |
| `anthropic_api` | Future standalone deployment | `ANTHROPIC_API_KEY` (never required for development) |

```bash
# real Claude, no separate API key
RISK_MANAGER_LLM_BACKEND=claude_agent_sdk uvicorn src.api.main:app --reload
```

Every report is labeled with its `llm_backend` and, in the stub case,
every field is prefixed `"STUB TEST:"` — a stub result is never
presented as a real-reasoning result. See
[`docs/AGENT_ARCHITECTURE.md`](docs/AGENT_ARCHITECTURE.md) §3.

## Running the frontend

```bash
cd frontend
npm install
npm run dev
# then: http://localhost:5173 (proxies /api and /health to the backend on :8000)
```

Requires the backend running separately (`uvicorn src.api.main:app`,
above) — the frontend never reads data any other way. Visit `/demo`
for a dev-tooling page linking directly to the 5 backend demo cases
(`docs/DEMO_FLOW.md`); the two real product nav items are Risk Overview
and Case Queue.

## Running tests

```bash
pytest -q                 # backend — 223 Phase 1-5A tests
pytest tests/api -q        # just the API layer

cd frontend && npm test    # frontend — 36 component/page tests (Vitest + RTL)
cd frontend && npm run build   # typecheck + production build
```

100% deterministic on both sides — `StubLLMClient` (or a fake raising
client for error-path tests) on the backend, `apiClient` mocked at the
module boundary on the frontend — zero live network calls, zero cost,
zero live-Claude dependency in either automated suite.

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | service status, model/graph version labels |
| GET | `/api/v1/cases` | list cases (filter by risk tier, graph flag, investigation status, TransactionDT range) |
| GET | `/api/v1/cases/{case_id}` | case detail (ML score/tier, graph evidence, no ground truth) |
| GET | `/api/v1/cases/{case_id}/graph` | graph evidence shaped for visualization |
| GET | `/api/v1/cases/{case_id}/investigation` | existing investigation report, if any |
| POST | `/api/v1/cases/investigate` | run (or return cached) agent investigation |

Full request/response contracts, error codes, and demo curl examples:
[`docs/API.md`](docs/API.md).

## Key documents

- [`docs/RAZORPAY_TRACK_02_COMPLIANCE.md`](docs/RAZORPAY_TRACK_02_COMPLIANCE.md) — requirement-by-requirement Track 02 compliance, held-out precision/recall/F1/FP-cost
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — one labeled REAL/SYNTHETIC/DETERMINISTIC/AI/HUMAN pipeline diagram
- [`docs/DEFENSE_ONLY_AUDIT.md`](docs/DEFENSE_ONLY_AUDIT.md) — proof the system cannot take an offensive/irreversible action
- [`docs/BACKEND_ARCHITECTURE.md`](docs/BACKEND_ARCHITECTURE.md) — Phase 5A layering, caching, security, design decisions
- [`docs/API.md`](docs/API.md) — full API reference
- [`docs/DEVELOPMENT_RUNBOOK.md`](docs/DEVELOPMENT_RUNBOOK.md) — setup, run, demo-seeding
- [`docs/FRONTEND_UX.md`](docs/FRONTEND_UX.md) — information architecture, states, API-grounding notes
- [`docs/DESIGN_SYSTEM.md`](docs/DESIGN_SYSTEM.md) — tokens, components, evidence/graph visual language
- [`docs/FRONTEND_ARCHITECTURE.md`](docs/FRONTEND_ARCHITECTURE.md) — stack choices, typed API client, testing strategy
- [`docs/DEMO_FLOW.md`](docs/DEMO_FLOW.md) — demo script, visual-validation findings, real-Claude end-to-end proof
- [`docs/AGENT_ARCHITECTURE.md`](docs/AGENT_ARCHITECTURE.md) / [`docs/TOOL_CONTRACTS.md`](docs/TOOL_CONTRACTS.md) / [`docs/RAG_POLICY.md`](docs/RAG_POLICY.md) / [`docs/SAFETY_MODEL.md`](docs/SAFETY_MODEL.md) — Phase 4 agent internals
- [`docs/AGENT_EVALUATION.md`](docs/AGENT_EVALUATION.md) — 12/12 real-Claude evaluation results and honest limitations
- [`docs/CASE_MODEL.md`](docs/CASE_MODEL.md) — the `Case`/`CaseGroundTruth` separation every later phase relies on
- [`docs/ML_GRAPH_ABLATION.md`](docs/ML_GRAPH_ABLATION.md) — what the graph layer adds over ML alone
