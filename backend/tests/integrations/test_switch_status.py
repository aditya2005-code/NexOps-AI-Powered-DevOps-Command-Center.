from datetime import datetime, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient

from app.core.config import settings
from app.integrations.switch.listener import get_switch_listener
from app.integrations.switch.schemas import SwitchConnectionState


def test_switch_status_endpoint_disabled(client: TestClient) -> None:
    """Verify status response when Switch is disabled."""
    with patch.object(settings, "SWITCH_ENABLED", False):
        listener = get_switch_listener()
        listener.state = SwitchConnectionState.DISABLED
        listener.connected = False

        response = client.get("/api/v1/integrations/switch/status")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["enabled"] is False
        assert data["data"]["state"] == "disabled"
        assert data["data"]["connected"] is False
        assert "X-Request-ID" in response.headers


def test_switch_status_endpoint_unconfigured(client: TestClient) -> None:
    """Verify status response when Switch is enabled but missing credentials."""
    with patch.object(settings, "SWITCH_ENABLED", True), \
         patch.object(settings, "SWITCH_CORE_URL", None), \
         patch.object(settings, "SWITCH_API_KEY", None):
        listener = get_switch_listener()
        listener.state = SwitchConnectionState.UNCONFIGURED
        listener.connected = False

        response = client.get("/api/v1/integrations/switch/status")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["enabled"] is True
        assert data["data"]["configured"] is False
        assert data["data"]["state"] == "unconfigured"
        assert data["data"]["connected"] is False


def test_switch_status_endpoint_connected(client: TestClient) -> None:
    """Verify status response when actively connected."""
    listener = get_switch_listener()
    listener.state = SwitchConnectionState.CONNECTED
    listener.connected = True
    listener.last_connected_at = datetime.now(timezone.utc)

    with patch.object(settings, "SWITCH_ENABLED", True), \
         patch.object(settings, "SWITCH_CORE_URL", "http://switch.internal:8080"), \
         patch.object(settings, "SWITCH_API_KEY", "sk_real_secret_key_123"):
        response = client.get("/api/v1/integrations/switch/status")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["state"] == "connected"
        assert data["data"]["connected"] is True
        assert data["data"]["last_connected_at"] is not None

        # Verify no credentials leaked
        assert "sk_real_secret_key_123" not in str(data)


def test_switch_status_endpoint_error_state(client: TestClient) -> None:
    """Verify status response when an error occurs."""
    listener = get_switch_listener()
    listener.state = SwitchConnectionState.ERROR
    listener.connected = False
    listener.last_error_at = datetime.now(timezone.utc)
    listener.last_error = "ConnectionRefusedError: Port 8080 not reachable"

    response = client.get("/api/v1/integrations/switch/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["state"] == "error"
    assert data["data"]["connected"] is False
    assert "Port 8080 not reachable" in data["data"]["last_error"]

