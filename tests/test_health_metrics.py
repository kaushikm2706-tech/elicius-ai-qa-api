def test_health_returns_healthy(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "healthy"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "ok"


def test_metrics_endpoint_exposes_prometheus_format(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    # Prometheus text format includes HELP/TYPE comment lines for each metric.
    assert b"chat_requests_total" in resp.content
