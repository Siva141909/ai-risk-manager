from __future__ import annotations

from src.api.demo_data import DEMO_CASES

GROUND_TRUTH_FIELD_NAMES = [
    "original_isFraud", "synthetic_ring_id", "synthetic_abuse_type", "synthetic_ring_role",
    "legitimate_cluster_id", "legitimate_cluster_type", "synthetic_entity_label",
]


def test_get_case_detail_returns_expected_shape(client, first_servable_case):
    resp = client.get(f"/api/v1/cases/{first_servable_case['case_id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == first_servable_case["case_id"]
    assert body["ml_risk_tier"] == first_servable_case["ml_risk_tier"]
    assert "customer_proxy_id" in body
    assert "graph_lookup_keys" in body


def test_get_case_detail_never_leaks_ground_truth(client, first_servable_case):
    resp = client.get(f"/api/v1/cases/{first_servable_case['case_id']}")
    body_text = resp.text
    for field in GROUND_TRUTH_FIELD_NAMES:
        assert field not in body_text


def test_get_case_detail_nonexistent_case_returns_404(client):
    resp = client.get("/api/v1/cases/CASE-999999999")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error_code"] == "case_not_found"
    assert "request_id" in body


def test_get_case_detail_malformed_case_id_returns_400(client):
    resp = client.get("/api/v1/cases/not-a-real-case-id")
    assert resp.status_code == 400
    assert resp.json()["error_code"] == "malformed_case_id"


def test_demo_dataset_cases_are_all_servable(client):
    for demo in DEMO_CASES:
        resp = client.get(f"/api/v1/cases/CASE-{demo.transaction_id}")
        assert resp.status_code == 200, f"{demo.label} (txn {demo.transaction_id}) not servable"
