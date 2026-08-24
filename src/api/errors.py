"""Phase 5A.5 — consistent API error handling.

Every exception here maps to a clean JSON error body and an appropriate
HTTP status — no stack trace, no internal exception text, ever reaches
the client (`_safe_detail` truncates/sanitizes free-text detail).

**Explicit design point on "agent failure" vs. "validation failure"**
(Phase 5A.5 asks for both to have consistent errors):

- The investigation agent's OWN deterministic evidence/report validation
  (`src/agents/safety.py`, Phase 4N) is not a system failure at all — a
  report that fails that validation is routed by the frozen LangGraph
  workflow to `fail_safe_human_review` and returned as a completely
  normal HTTP 200 `InvestigationResponse` with
  `validation_status="failed_human_review"` and
  `requires_human_review=true`. This IS the fail-safe behavior Phase
  5A.5 requires the API to preserve — it is a valid business outcome,
  not an error, and turning it into an HTTP error would be *removing*
  that behavior, not preserving it.
- `AgentExecutionError` below is for the OTHER case: the LLM
  client/transport itself raising (e.g. the Claude Agent SDK's own
  session-limit error observed during Phase 4 closure), or any other
  unexpected exception escaping `run_investigation`. That is a genuine
  system failure and does map to an HTTP error (503, see
  `LLMUnavailableError`, a subclass used when the failure is
  specifically LLM-backend-shaped).
- "Malformed request" / request-schema "validation failure" is handled
  automatically by FastAPI/Pydantic (422) and is a separate concept
  from the above.
"""

from __future__ import annotations

from src.logging_conf import get_logger

logger = get_logger("api.errors")


class ApiError(Exception):
    """Base class for every deliberate API-layer error. `status_code`
    and `error_code` are used by the FastAPI exception handler
    (`src/api/main.py`) to build a consistent JSON body."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class MalformedCaseIdError(ApiError):
    status_code = 400
    error_code = "malformed_case_id"


class CaseNotFoundError(ApiError):
    status_code = 404
    error_code = "case_not_found"


class InvestigationNotFoundError(ApiError):
    status_code = 404
    error_code = "investigation_not_found"


class UnsupportedInvestigationModeError(ApiError):
    """Raised when a request asks for an investigation_mode/cutoff_dt
    combination the frozen Phase 4 agent does not actually support —
    see docs/BACKEND_ARCHITECTURE.md's "investigation_mode" design note.
    Deliberately 400, not 501: this is a request the client made
    incorrectly, not a missing feature the server intends to add for
    this exact shape."""

    status_code = 400
    error_code = "unsupported_investigation_mode"


class ToolExecutionError(ApiError):
    status_code = 502
    error_code = "tool_execution_failed"


class LLMUnavailableError(ApiError):
    status_code = 503
    error_code = "llm_unavailable"


class AgentExecutionError(ApiError):
    """An unexpected exception escaped `run_investigation` itself (not
    the graph's own designed fail-safe path, which never raises).
    Covers `LLMUnavailableError` as a more specific case where the
    calling service can identify the failure as LLM-shaped."""

    status_code = 500
    error_code = "agent_execution_failed"


class InvestigationTimeoutError(ApiError):
    status_code = 504
    error_code = "investigation_timeout"


class RequestTooLargeError(ApiError):
    status_code = 413
    error_code = "request_too_large"
