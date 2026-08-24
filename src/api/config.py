"""Phase 5A — application configuration.

Configuration lives here, never inline in route handlers (Phase 5A.10).
The LLM backend is a SERVER-side deployment choice, selected via an
environment variable — never a field the client can set on a request
(that would let a client influence which backend runs, which is a
different concern from Phase 5A.8's "no client-controlled risk tier,"
but the same principle: the backend decides how a case is investigated,
the client only asks for one).

No `ANTHROPIC_API_KEY` is required for the default development
workflow — the default backend is `stub`, and `claude_agent_sdk` (the
Claude Code development backend used for real evaluation, see
docs/AGENT_ARCHITECTURE.md) needs no separate key either. `anthropic_api`
is available for a future standalone deployment but is never the
default and is never required.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

VALID_LLM_BACKENDS = ("stub", "claude_agent_sdk", "anthropic_api")

# Static, descriptive labels for the frozen artifacts this API serves —
# not live introspection of a model registry (none exists yet). See
# docs/BACKEND_ARCHITECTURE.md for what each label refers to.
MODEL_VERSION = "phase2-xgboost-isotonic-calibrated-v1"
GRAPH_CONFIG_VERSION = "phase3-connected-components-min3-v1"
APP_VERSION = "0.5.0-phase5a"


@dataclass(frozen=True)
class Settings:
    project_root: Path
    environment: str = "development"
    llm_backend: str = "stub"
    investigation_timeout_seconds: int = 90
    max_request_body_bytes: int = 16_384
    default_page_limit: int = 50
    max_page_limit: int = 200

    @classmethod
    def from_env(cls, project_root: Path | None = None) -> "Settings":
        root = project_root or Path(__file__).resolve().parent.parent.parent
        backend = os.environ.get("RISK_MANAGER_LLM_BACKEND", "stub").strip().lower()
        if backend not in VALID_LLM_BACKENDS:
            raise ValueError(
                f"RISK_MANAGER_LLM_BACKEND={backend!r} is not one of {VALID_LLM_BACKENDS}"
            )
        return cls(
            project_root=root,
            environment=os.environ.get("RISK_MANAGER_ENV", "development"),
            llm_backend=backend,
            investigation_timeout_seconds=int(
                os.environ.get("RISK_MANAGER_INVESTIGATION_TIMEOUT_SECONDS", "90")
            ),
        )
