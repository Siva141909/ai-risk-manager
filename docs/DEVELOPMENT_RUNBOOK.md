# Development Runbook — Phase 5A

## Setup

```bash
python3.14 -m venv .venv   # or your Python 3.14 interpreter
source .venv/bin/activate
pip install -r requirements.txt
```

No `ANTHROPIC_API_KEY` is required for anything in this runbook.

## Reproducing from a fresh clone (Phase 6 addition)

`pytest -q` right after `pip install` gets you **146 of 228 backend
tests** (the ones built on in-memory fixtures) — the other 82 (all API
tests, several integration tests) read generated artifacts under
`data/synthetic/` and `data/processed/` that are correctly gitignored
(`docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §15) and therefore don't exist
on a fresh clone. To get all 228 passing and the API server running,
acquire the raw dataset first (`docs/DATASET_ACQUISITION.md`), then run
this exact sequence once:

```bash
python -m scripts.generate_full_benchmark          # data/synthetic/full/
python -m scripts.prepare_features                 # data/processed/features.parquet
python -m scripts.train_baseline                   # data/processed/model_*.json, calibrator_*.joblib
python -m scripts.calibrate_and_threshold           # data/processed/risk_thresholds.json
python -m scripts.score_val_test_for_graph_fusion   # data/processed/val_test_ml_scores.parquet
python -m scripts.graph_benchmark_full              # data/synthetic/full/graph_benchmark_full_report.json
python -m scripts.graph_health_full                 # data/synthetic/full/graph_health_full.json
python -m scripts.ml_graph_ablation                 # data/processed/ml_graph_ablation_report.json
pytest -q                                            # now all 228 pass
```

For the Track 02 held-out evaluation specifically (independent of the
above — a separate benchmark, `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3):

```bash
python -m scripts.generate_holdout_benchmark
python -m scripts.run_track02_evaluation
```

Full gap analysis and verified environment versions:
[`docs/REPRODUCIBILITY_AUDIT.md`](REPRODUCIBILITY_AUDIT.md).

## Running the test suite

```bash
pytest -q
```

Runs everything: Phase 1-4's 182 tests (dataset, ML, graph, agent,
safety, RAG) plus Phase 5A's ~40 API tests — all using deterministic
data and `StubLLMClient`/fake LLM clients, no network calls, no live
Claude. `tests/api/` alone:

```bash
pytest tests/api -q
```

## Running the API locally

**Default (stub backend — safe, deterministic, no credential):**

```bash
uvicorn src.api.main:app --reload
```

Then visit `http://127.0.0.1:8000/docs` for interactive OpenAPI docs, or:

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/api/v1/cases?limit=5"
curl -X POST http://127.0.0.1:8000/api/v1/cases/investigate \
  -H "Content-Type: application/json" \
  -d '{"case_id": "CASE-3457202"}'
```

Every investigation with the stub backend returns a report whose fields
are prefixed `"STUB TEST:"` — a deterministic template, not real
reasoning (see `docs/AGENT_ARCHITECTURE.md`). Fine for exercising the
API end-to-end; not a substitute for a real demo run.

**Claude development mode (real Claude, via the local Claude Code
environment — no separate API key):**

```bash
RISK_MANAGER_LLM_BACKEND=claude_agent_sdk uvicorn src.api.main:app --reload
```

Every investigation now calls the real Claude model through the same
`claude_agent_sdk` path verified in Phase 4
(`docs/AGENT_ARCHITECTURE.md` §3). Expect 20-60 seconds per
investigation (Phase 4's measured range) — the API is synchronous by
design (`docs/BACKEND_ARCHITECTURE.md` §4), so the request simply takes
that long to return; it is not stuck.

**Future standalone deployment mode** (not used in development):

```bash
RISK_MANAGER_LLM_BACKEND=anthropic_api ANTHROPIC_API_KEY=... uvicorn src.api.main:app
```

Only needed if running this API independently of a Claude Code
development environment. Never required for local development or CI.

## Seeding the demo dataset with real investigations

```bash
# stub (fast, safe, for smoke-testing the seeding script itself)
python -m scripts.seed_demo_investigations

# real Claude (for an actual live demo)
RISK_MANAGER_LLM_BACKEND=claude_agent_sdk python -m scripts.seed_demo_investigations
```

Runs the exact same `InvestigationService.investigate` call the API
route makes for each of the 5 cases in `src/api/demo_data.py`, writing
results to `data/processed/api_demo_investigations.json` (gitignored,
regenerate as needed — never hand-edit this file, it exists only to
prove the reports came from the real pipeline).

## Configuration reference

| Env var | Default | Meaning |
|---|---|---|
| `RISK_MANAGER_LLM_BACKEND` | `stub` | `stub` \| `claude_agent_sdk` \| `anthropic_api` |
| `RISK_MANAGER_ENV` | `development` | free-text label, shown on `/health` |
| `RISK_MANAGER_INVESTIGATION_TIMEOUT_SECONDS` | `90` | per-investigation timeout before `504` |

## Common tasks

**Add a new endpoint:** add a schema to `src/api/schemas.py`, a service
method to `src/api/services.py` (or a new service class if it's a new
concern), a route in `src/api/routers/`, and tests in `tests/api/`.
Never call `src.agents`/`src.tools`/`src.graph` from a router directly.

**Change what a route returns:** edit the Pydantic response schema in
`src/api/schemas.py` — OpenAPI docs regenerate automatically, nothing
to hand-sync.

**Investigate a slow test run:** `tests/api/conftest.py`'s `client`
fixture is session-scoped precisely so the ~590K-row synthetic
transaction table and graph-signal computation load once per test
session, not once per test file — if you add a new test module and see
it take 10+ seconds again, check you're depending on the shared
`client` fixture, not building a fresh `TestClient` per test.
