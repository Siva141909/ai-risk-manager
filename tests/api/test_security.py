"""Phase 5A.8/5A.11 — security controls."""

from __future__ import annotations

import ast
from pathlib import Path

from src.api.demo_data import DEMO_CASES

API_SRC_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "api"

GROUND_TRUTH_FIELD_NAMES = [
    "original_isFraud", "synthetic_ring_id", "synthetic_abuse_type", "synthetic_ring_role",
    "legitimate_cluster_id", "legitimate_cluster_type", "synthetic_entity_label",
]


def test_client_cannot_override_risk_tier_via_extra_field(client, first_servable_case):
    resp = client.post(
        "/api/v1/cases/investigate",
        json={"case_id": first_servable_case["case_id"], "ml_risk_tier": "CRITICAL"},
    )
    assert resp.status_code == 422  # extra="forbid" rejects the field outright


def test_client_cannot_override_graph_score_via_extra_field(client, first_servable_case):
    resp = client.post(
        "/api/v1/cases/investigate",
        json={"case_id": first_servable_case["case_id"], "relationship_rarity_score": 999.0},
    )
    assert resp.status_code == 422


def test_actual_response_risk_tier_always_matches_frozen_dataset(client, first_servable_case):
    """Even setting aside the 422 rejection above: confirm the response
    the server WOULD have returned matches the frozen dataset value,
    never anything derived from client input."""
    resp = client.get(f"/api/v1/cases/{first_servable_case['case_id']}")
    assert resp.json()["ml_risk_tier"] == first_servable_case["ml_risk_tier"]


def test_request_body_over_size_limit_rejected(app_settings):
    from fastapi.testclient import TestClient

    from src.api.main import create_app

    tiny_limit_settings = app_settings.__class__(
        project_root=app_settings.project_root, environment="test", llm_backend="stub",
        investigation_timeout_seconds=30, max_request_body_bytes=64,
    )
    app = create_app(tiny_limit_settings)
    with TestClient(app) as test_client:
        oversized_case_id = "CASE-" + ("1" * 200)
        resp = test_client.post("/api/v1/cases/investigate", json={"case_id": oversized_case_id})
        assert resp.status_code == 413
        assert resp.json()["error_code"] == "request_too_large"


def test_case_ground_truth_never_imported_anywhere_in_api_layer():
    """Structural check (mirrors Phase 4's CaseGroundTruth-isolation
    tests): scans every src/api/*.py file's AST for an import of
    CaseGroundTruth — not just a runtime response check, since a field
    that's simply never populated could still be one refactor away from
    a leak. An import site is the earliest place this could go wrong."""
    for path in API_SRC_DIR.rglob("*.py"):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    assert alias.name != "CaseGroundTruth", f"{path} imports CaseGroundTruth"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "CaseGroundTruth" not in alias.name


def test_no_ground_truth_field_names_in_any_demo_investigation_response(client):
    for demo in DEMO_CASES:
        case_id = f"CASE-{demo.transaction_id}"
        resp = client.post("/api/v1/cases/investigate", json={"case_id": case_id})
        assert resp.status_code == 200
        for field in GROUND_TRUTH_FIELD_NAMES:
            assert field not in resp.text, f"{field} leaked in response for {case_id}"


def test_no_sql_string_construction_anywhere_in_api_layer():
    """Cheap grep-equivalent: the API layer must never build a SQL
    string from request input (Phase 5A.8's "no arbitrary SQL"). This
    project has no SQL at all — pandas only — so this simply confirms
    that stays true."""
    forbidden_tokens = ["execute(", "cursor(", " SELECT ", "sqlite3", "psycopg"]
    for path in API_SRC_DIR.rglob("*.py"):
        text = path.read_text()
        for token in forbidden_tokens:
            assert token not in text, f"{path} contains {token!r}"
