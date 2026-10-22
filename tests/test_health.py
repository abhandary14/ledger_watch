import pytest


# JWTTenantMiddleware looks up the public tenant on every request, so even
# /health touches the database.
@pytest.mark.django_db
def test_health_endpoint(api_client):
    """GET /health should return HTTP 200 with status ok."""
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
