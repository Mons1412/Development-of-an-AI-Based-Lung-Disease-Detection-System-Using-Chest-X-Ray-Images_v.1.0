def test_model_info_returns_artifact_contract(test_client):
    response = test_client.get("/api/v1/model-info")

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "1.1.0"
    assert payload["classes"] == ["normal", "pneumonia", "tuberculosis"]
    assert payload["preprocessing"]["preprocessing_location"] == "embedded_in_model"
