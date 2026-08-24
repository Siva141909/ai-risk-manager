from __future__ import annotations


def test_list_cases_default_pagination(client):
    resp = client.get("/api/v1/cases")
    assert resp.status_code == 200
    body = resp.json()
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert len(body["items"]) == 50
    assert body["total"] > 50


def test_list_cases_filter_by_risk_tier(client):
    resp = client.get("/api/v1/cases", params={"risk_tier": "CRITICAL", "limit": 20})
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["ml_risk_tier"] == "CRITICAL" for item in body["items"])


def test_list_cases_filter_by_graph_flagged(client):
    resp = client.get("/api/v1/cases", params={"graph_flagged": True, "limit": 20})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) > 0
    assert all(item["graph_flagged"] is True for item in body["items"])


def test_list_cases_filter_by_dt_range(client):
    resp = client.get("/api/v1/cases", params={"start_dt": 10_000_000, "end_dt": 10_100_000, "limit": 50})
    assert resp.status_code == 200
    body = resp.json()
    for item in body["items"]:
        assert 10_000_000 <= item["transaction_dt"] <= 10_100_000


def test_list_cases_invalid_risk_tier_rejected(client):
    resp = client.get("/api/v1/cases", params={"risk_tier": "SUPER_DUPER_CRITICAL"})
    assert resp.status_code == 422


def test_list_cases_pagination_offset(client):
    page1 = client.get("/api/v1/cases", params={"limit": 5, "offset": 0}).json()
    page2 = client.get("/api/v1/cases", params={"limit": 5, "offset": 5}).json()
    ids_1 = {item["case_id"] for item in page1["items"]}
    ids_2 = {item["case_id"] for item in page2["items"]}
    assert ids_1.isdisjoint(ids_2)


def test_list_cases_filter_by_investigation_status_not_investigated(client, first_servable_case):
    resp = client.get("/api/v1/cases", params={"investigation_status": "not_investigated", "limit": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert all(item["has_investigation"] is False for item in body["items"])


def test_investigation_status_filter_is_correct_before_pagination(client):
    """Regression test (Phase 5B): investigation_status must filter the
    FULL dataset before limit/offset and `total` is recomputed, not
    just check the current page's rows — a fixed page of un-investigated
    rows must never make `investigation_status=investigated` silently
    report the whole dataset's total or miss a real investigated case
    that happens to sit outside a small page."""
    listing = client.get("/api/v1/cases", params={"limit": 1}).json()
    full_total = listing["total"]

    target_case_id = client.get("/api/v1/cases", params={"limit": 1, "offset": 200}).json()["items"][0]["case_id"]
    investigate_resp = client.post("/api/v1/cases/investigate", json={"case_id": target_case_id})
    assert investigate_resp.status_code == 200

    resp = client.get("/api/v1/cases", params={"investigation_status": "investigated", "limit": 200})
    assert resp.status_code == 200
    body = resp.json()

    assert body["total"] < full_total  # never the unfiltered dataset size
    assert all(item["has_investigation"] is True for item in body["items"])
    assert any(item["case_id"] == target_case_id for item in body["items"])
