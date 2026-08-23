# AI Risk Manager — Razorpay AI Buildathon 2026, Track 2

Implementation of the system described in
[`ai_risk_manager_system_design.md`](ai_risk_manager_system_design.md),
which is the authoritative source of truth for this project's architecture.
If code and design doc ever disagree, the design doc wins unless a
documented, reported deviation says otherwise (see `docs/` for any such
deviations).

## Status: Phase 0 — project initialization + feasibility audit

Phase 0 is scaffolding and feasibility-checking only. **No ML model, graph,
agent, RAG, API, or UI code exists yet** — see the design doc's Section 32
build order for what each later phase adds.

**Current blocker:** the IEEE-CIS Fraud Detection dataset is not present
locally. See [`docs/DATASET_ACQUISITION.md`](docs/DATASET_ACQUISITION.md)
for the official acquisition route and exact steps. No implementation
beyond Phase 0 scaffolding can proceed until this is resolved.

## Repository layout

```
data/{raw,synthetic,processed}/   # raw IEEE-CIS (gitignored), generator output, feature tables
configs/                          # seed.yaml, paths.yaml
src/{ingestion,generator,features,models,graph,agents,tools,rag,evaluation,api}/
tests/{unit,integration,adversarial}/
notebooks/                        # EDA, not shipped code
scripts/                          # pipeline/evaluation entrypoints (not yet populated)
frontend/                         # Streamlit/React UI (not yet populated)
docs/                             # acquisition, audit, and feasibility docs
```

## Environment

- Python 3.14.3, dependencies in `requirements.txt` (kept minimal by
  design — see the comment at the top of that file).
- No GPU/CUDA dependency in this project (Apple Silicon dev machine; models
  used — XGBoost — are CPU-trained per the design doc).

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -v
```

## Documents produced during Phase 0

- [`docs/DATASET_ACQUISITION.md`](docs/DATASET_ACQUISITION.md) — how to get
  IEEE-CIS legitimately; required because the dataset was not found locally.
- [`docs/GRAPH_FEASIBILITY.md`](docs/GRAPH_FEASIBILITY.md) — preliminary
  feasibility check of the graph/entity layer against IEEE-CIS's documented
  schema (pending re-verification once the raw files are actually read).
