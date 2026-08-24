from __future__ import annotations

from src.api.demo_data import DEMO_CASES


def test_investigation_not_found_before_running(client, first_servable_case):
    resp = client.get(f"/api/v1/cases/{first_servable_case['case_id']}/investigation")
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "investigation_not_found"


def test_investigate_by_case_id_returns_full_response(client, first_servable_case):
    resp = client.post(
        "/api/v1/cases/investigate",
        json={"case_id": first_servable_case["case_id"], "investigation_mode": "real_time"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == first_servable_case["case_id"]
    assert body["ml_risk_tier"] == first_servable_case["ml_risk_tier"]
    assert "investigation_report" in body
    assert "recommendation" in body
    assert "confidence" in body
    assert body["human_approval_required"] is True
    assert body["processing"]["llm_backend"] == "stub"
    assert body["processing"]["cache_hit"] is False


def test_investigate_by_transaction_id_matches_case_id(client, first_servable_case):
    resp = client.post(
        "/api/v1/cases/investigate",
        json={"transaction_id": first_servable_case["transaction_id"]},
    )
    assert resp.status_code == 200
    assert resp.json()["case_id"] == first_servable_case["case_id"]


def test_investigate_is_cached_on_second_call(client, first_servable_case):
    resp1 = client.post("/api/v1/cases/investigate", json={"case_id": first_servable_case["case_id"]})
    resp2 = client.post("/api/v1/cases/investigate", json={"case_id": first_servable_case["case_id"]})
    assert resp1.status_code == 200 and resp2.status_code == 200
    assert resp2.json()["processing"]["cache_hit"] is True
    assert resp2.json()["investigation_report"] == resp1.json()["investigation_report"]


def test_investigation_found_after_running(client, first_servable_case):
    client.post("/api/v1/cases/investigate", json={"case_id": first_servable_case["case_id"]})
    resp = client.get(f"/api/v1/cases/{first_servable_case['case_id']}/investigation")
    assert resp.status_code == 200
    assert resp.json()["case_id"] == first_servable_case["case_id"]


def test_investigate_nonexistent_case_returns_404(client):
    resp = client.post("/api/v1/cases/investigate", json={"case_id": "CASE-999999999"})
    assert resp.status_code == 404


def test_investigate_missing_identifier_rejected(client):
    resp = client.post("/api/v1/cases/investigate", json={})
    assert resp.status_code == 422


def test_investigate_both_identifiers_rejected(client, first_servable_case):
    resp = client.post(
        "/api/v1/cases/investigate",
        json={"case_id": first_servable_case["case_id"], "transaction_id": first_servable_case["transaction_id"]},
    )
    assert resp.status_code == 422


def test_investigate_mismatched_cutoff_dt_rejected(client, first_servable_case):
    resp = client.post(
        "/api/v1/cases/investigate",
        json={"case_id": first_servable_case["case_id"], "cutoff_dt": first_servable_case["transaction_dt"] + 1},
    )
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "unsupported_investigation_mode"


def test_investigate_matching_cutoff_dt_accepted(client, first_servable_case):
    resp = client.post(
        "/api/v1/cases/investigate",
        json={"case_id": first_servable_case["case_id"], "cutoff_dt": first_servable_case["transaction_dt"]},
    )
    assert resp.status_code == 200


def test_all_demo_cases_investigate_successfully_via_stub(client):
    for demo in DEMO_CASES:
        case_id = f"CASE-{demo.transaction_id}"
        resp = client.post("/api/v1/cases/investigate", json={"case_id": case_id})
        assert resp.status_code == 200, f"{demo.label} failed: {resp.text}"
        body = resp.json()
        assert body["investigation_report"]["validation_status"] == "passed"
        assert body["processing"]["llm_backend"] == "stub"
