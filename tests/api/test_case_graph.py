from __future__ import annotations

from src.api.demo_data import DEMO_CASES


def _first_graph_flagged_case_id(client) -> str:
    resp = client.get("/api/v1/cases", params={"graph_flagged": True, "limit": 1})
    return resp.json()["items"][0]["case_id"]


def test_get_case_graph_with_graph_evidence(client):
    case_id = _first_graph_flagged_case_id(client)
    resp = client.get(f"/api/v1/cases/{case_id}/graph")
    assert resp.status_code == 200
    body = resp.json()
    assert body["case_id"] == case_id
    assert body["graph_evidence"] is not None
    assert len(body["nodes"]) >= 1
    center_nodes = [n for n in body["nodes"] if n["is_center"]]
    assert len(center_nodes) == 1


def test_get_case_graph_no_graph_evidence_returns_empty_viz(client):
    resp = client.get("/api/v1/cases", params={"graph_flagged": False, "limit": 1})
    case_id = resp.json()["items"][0]["case_id"]
    resp = client.get(f"/api/v1/cases/{case_id}/graph")
    assert resp.status_code == 200
    body = resp.json()
    assert body["graph_evidence"] is None
    assert body["nodes"] == []
    assert body["edges"] == []


def test_get_case_graph_nonexistent_case_404(client):
    resp = client.get("/api/v1/cases/CASE-999999999/graph")
    assert resp.status_code == 404


def test_demo_ring_case_graph_has_edges(client):
    ring = next(d for d in DEMO_CASES if d.label == "strong_coordinated_ring")
    resp = client.get(f"/api/v1/cases/CASE-{ring.transaction_id}/graph")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["edges"]) > 0
    for edge in body["edges"]:
        assert edge["source"] != edge["target"]
