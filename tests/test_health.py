def test_health_endpoint(api_client):
    """GET /health should return HTTP 200 with status ok."""
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
