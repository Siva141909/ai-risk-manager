"""Phase 5A.11 — API test fixtures.

Every fixture here forces `llm_backend="stub"` explicitly, regardless of
any `RISK_MANAGER_LLM_BACKEND` set in the environment running pytest —
automated tests must never depend on live Claude (Phase 5A.11's
explicit instruction).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.api.config import Settings
from src.api.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def app_settings() -> Settings:
    return Settings(project_root=PROJECT_ROOT, environment="test", llm_backend="stub", investigation_timeout_seconds=30)


@pytest.fixture(scope="session")
def client(app_settings: Settings):
    # Session-scoped: building the app loads the full synthetic transaction
    # table and computes graph signals once (a few seconds) rather than once
    # per test module — the underlying data is read-only, so sharing it
    # across tests is safe (tests only assert on it, never mutate it, except
    # the investigation cache, which different case_ids/backends keep separate).
    app = create_app(app_settings)
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="session")
def first_servable_case(client: TestClient) -> dict:
    resp = client.get("/api/v1/cases", params={"limit": 1})
    assert resp.status_code == 200
    return resp.json()["items"][0]
