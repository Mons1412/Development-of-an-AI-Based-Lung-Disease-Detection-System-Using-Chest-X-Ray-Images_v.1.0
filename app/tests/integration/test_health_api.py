def test_health_live_returns_ok(test_client):
    response = test_client.get("/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_ready_returns_model_version(test_client):
    response = test_client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["model_ready"] is True
    assert response.json()["model_version"] == "1.1.0"
