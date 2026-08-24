"""Phase 5A.11 — error-path tests.

Uses fake LLM clients (mirroring the pattern already established in
`tests/integration/test_agent_investigation_pipeline.py`'s
`AlwaysMalformedClient`/`FabricatingClient`) to exercise agent-failure
and LLM-unavailable paths without ever calling live Claude.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.config import Settings
from src.api.dependencies import get_investigation_service
from src.api.main import create_app
from src.api.services import InvestigationService


class _RaisingClient:
    """Simulates the LLM transport itself failing (e.g. a Claude Agent
    SDK session-limit error) — NOT a validation failure. Distinct from
    the frozen agent's own fail-safe path, which never raises."""

    backend_name = "broken_test_backend"

    def __init__(self, message: str) -> None:
        self._message = message

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        raise RuntimeError(self._message)


@pytest.fixture()
def app_with_broken_llm(app_settings: Settings):
    app = create_app(app_settings)
    with TestClient(app) as test_client:
        state = app.state.risk_manager
        broken_service = InvestigationService(
            state.ctx, state.corpus, _RaisingClient("You've hit your session limit · resets 12:50am"), state.cache
        )
        app.dependency_overrides[get_investigation_service] = lambda: broken_service
        yield test_client
        app.dependency_overrides.clear()


def test_llm_unavailable_maps_to_503(app_with_broken_llm, first_servable_case):
    resp = app_with_broken_llm.post("/api/v1/cases/investigate", json={"case_id": first_servable_case["case_id"]})
    assert resp.status_code == 503
    body = resp.json()
    assert body["error_code"] == "llm_unavailable"
    assert "request_id" in body
    # the exception TYPE name is a fine, useful diagnostic label; a stack
    # trace, file path, or line number is what must never leak
    assert "Traceback" not in body["message"]
    assert "services.py" not in body["message"]
    assert "line " not in body["message"]
    assert "You've hit your session limit" not in body["message"]  # raw exception text not echoed verbatim


@pytest.fixture()
def app_with_generic_broken_llm(app_settings: Settings):
    class _WeirdlyBrokenClient:
        backend_name = "weird_test_backend"

        def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
            raise ValueError("something structurally unexpected happened")

    app = create_app(app_settings)
    with TestClient(app) as test_client:
        state = app.state.risk_manager
        broken_service = InvestigationService(state.ctx, state.corpus, _WeirdlyBrokenClient(), state.cache)
        app.dependency_overrides[get_investigation_service] = lambda: broken_service
        yield test_client
        app.dependency_overrides.clear()


def test_generic_agent_execution_failure_maps_to_500(app_with_generic_broken_llm, first_servable_case):
    resp = app_with_generic_broken_llm.post("/api/v1/cases/investigate", json={"case_id": first_servable_case["case_id"]})
    assert resp.status_code == 500
    body = resp.json()
    assert body["error_code"] == "agent_execution_failed"
    assert "Traceback" not in body["message"]
    assert "something structurally unexpected happened" not in body["message"]  # raw exception text not echoed verbatim


def test_agent_fail_safe_human_review_is_not_an_http_error(client):
    """The frozen agent's OWN deterministic validation failure
    (fail_safe_human_review) must remain a normal 200 response — this
    is the fail-safe behavior Phase 5A.5 requires the API to preserve,
    not convert into an HTTP error."""

    class _AlwaysMalformedClient:
        backend_name = "always_malformed_test"

        def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
            return "this is not json at all {{{"

    from fastapi.testclient import TestClient as _TC  # local import to avoid confusion with module fixture client

    state = client.app.state.risk_manager
    broken_service = InvestigationService(state.ctx, state.corpus, _AlwaysMalformedClient(), state.cache)
    client.app.dependency_overrides[get_investigation_service] = lambda: broken_service
    try:
        resp = client.get("/api/v1/cases", params={"limit": 1})
        case_id = resp.json()["items"][0]["case_id"]
        resp = client.post("/api/v1/cases/investigate", json={"case_id": case_id})
        assert resp.status_code == 200
        body = resp.json()
        assert body["investigation_report"]["validation_status"] == "failed_human_review"
        assert body["human_approval_required"] is True
        assert body["recommendation"] == "escalate_to_human_analyst"
    finally:
        client.app.dependency_overrides.clear()


def test_malformed_json_body_returns_422(client):
    resp = client.post(
        "/api/v1/cases/investigate",
        content="{not valid json",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 422


def test_investigation_timeout_maps_to_504(app_settings):
    class _SlowClient:
        backend_name = "slow_test_backend"

        def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
            import time

            time.sleep(3)
            return "{}"

    fast_timeout_settings = Settings(
        project_root=app_settings.project_root, environment="test", llm_backend="stub", investigation_timeout_seconds=1
    )
    app = create_app(fast_timeout_settings)
    with TestClient(app) as test_client:
        state = app.state.risk_manager
        slow_service = InvestigationService(state.ctx, state.corpus, _SlowClient(), state.cache)
        app.dependency_overrides[get_investigation_service] = lambda: slow_service
        resp = test_client.get("/api/v1/cases", params={"limit": 1})
        case_id = resp.json()["items"][0]["case_id"]
        resp = test_client.post("/api/v1/cases/investigate", json={"case_id": case_id})
        assert resp.status_code == 504
        assert resp.json()["error_code"] == "investigation_timeout"
