from fastapi.testclient import TestClient
from app.core.config import get_settings


def test_root_endpoint(client: TestClient) -> None:
    """1. Test GET / returns application information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "NexOps backend is operational"
    assert data["data"]["status"] == "healthy"
    assert data["data"]["application"] == "NexOps"


def test_health_endpoint(client: TestClient) -> None:
    """2. Test GET /health returns standard health check."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert "environment" in data["data"]


def test_api_v1_health_endpoint(client: TestClient) -> None:
    """3. Test GET /api/v1/health returns versioned health response."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert data["data"]["application"] == "NexOps"


def test_request_id_and_process_time_headers(client: TestClient) -> None:
    """4. Test Request ID and processing time middleware."""
    # Test auto-generated Request ID
    response = client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert len(response.headers["X-Request-ID"]) > 0
    assert "X-Process-Time" in response.headers

    # Test custom incoming Request ID is echoed
    custom_id = "test-custom-request-id-12345"
    response_with_custom = client.get("/health", headers={"X-Request-ID": custom_id})
    assert response_with_custom.headers["X-Request-ID"] == custom_id


def test_invalid_endpoint_handling(client: TestClient) -> None:
    """5. Test 404 handling with centralized error envelope and Request ID."""
    response = client.get("/api/v1/nonexistent-route")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "NOT_FOUND"
    assert "X-Request-ID" in response.headers


def test_validation_error_response(client: TestClient) -> None:
    """6. Test 422 validation error returns structured format."""
    # Query parameter 'echo' has max_length=50
    invalid_query = "x" * 60
    response = client.get(f"/api/v1/health?echo={invalid_query}")
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["message"] == "Validation failed"
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(data["error"]["details"], list)
    assert len(data["error"]["details"]) > 0
    assert "X-Request-ID" in response.headers


def test_application_configuration() -> None:
    """7. Test basic application configuration values."""
    settings = get_settings()
    assert settings.APP_NAME == "NexOps"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert isinstance(settings.cors_origins, list)
    assert len(settings.cors_origins) > 0
