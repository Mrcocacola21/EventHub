import pytest


@pytest.mark.api
def test_openapi_schema_contains_core_paths(api_client):
    response = api_client.get("/api/schema/")

    assert response.status_code == 200
    paths = response.data["paths"]
    assert "/api/bookings/{id}/use/" in paths
    assert "/api/tournaments/{id}/start/" in paths
    assert "/api/matches/{id}/result/" in paths
    assert "/api/notifications/read-all/" in paths
