from __future__ import annotations


def test_health_returns_ok_and_no_secrets(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["llm_backend"] == "stub"
    assert "app_version" in body
    assert "model_version" in body
    assert "graph_config_version" in body
    forbidden_substrings = ["key", "secret", "token", "credential", "password"]
    body_text = str(body).lower()
    for token in forbidden_substrings:
        assert token not in body_text
