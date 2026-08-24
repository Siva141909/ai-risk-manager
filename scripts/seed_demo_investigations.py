"""Phase 5A.13 — seed real investigations for the demo dataset.

Runs the actual pipeline (`InvestigationService.investigate`, the exact
same call `POST /api/v1/cases/investigate` makes) for every case in
`src/api/demo_data.py::DEMO_CASES` and writes the resulting reports to
`data/processed/api_demo_investigations.json` — never hand-authored.

Uses `RISK_MANAGER_LLM_BACKEND` (default `stub`) exactly like the API
server does, so running this with the default produces STUB TEST
reports (safe for CI/offline use), and running it with
`RISK_MANAGER_LLM_BACKEND=claude_agent_sdk` produces real CLAUDE
DEVELOPMENT RUN reports for an actual live demo — never presented as
one when it is the other (see the "backend" field on every report).
"""

from __future__ import annotations

import json
from pathlib import Path

from src.api.config import Settings
from src.api.demo_data import DEMO_CASES
from src.api.dependencies import build_app_state
from src.api.services import CaseService, InvestigationService

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = PROJECT_ROOT / "data" / "processed" / "api_demo_investigations.json"


def main() -> None:
    settings = Settings.from_env(project_root=PROJECT_ROOT)
    state = build_app_state(settings)
    case_service = CaseService(state.repository, state.ctx, state.cache, state.llm_client.backend_name)
    investigation_service = InvestigationService(state.ctx, state.corpus, state.llm_client, state.cache)

    results = []
    for demo in DEMO_CASES:
        case_id = f"CASE-{demo.transaction_id}"
        print(f"=== {demo.label} ({case_id}) — backend={settings.llm_backend} ===")
        case = case_service.get_case(case_id)
        outcome = investigation_service.investigate(case, "real_time")
        print(f"    recommendation={outcome.report['recommendation']} "
              f"validation_status={outcome.report['validation_status']} "
              f"agent_duration_ms={outcome.agent_duration_ms}")
        results.append({"label": demo.label, "case_id": case_id, "report": outcome.report})

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nWritten to {OUT_PATH}")


if __name__ == "__main__":
    main()
