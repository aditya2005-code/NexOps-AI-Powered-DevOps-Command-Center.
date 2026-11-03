import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch
from websockets.exceptions import ConnectionClosed

from app.core.config import settings
from app.integrations.switch.listener import SwitchListener
from app.integrations.switch.schemas import SwitchConnectionState


@pytest.mark.anyio
async def test_switch_listener_disabled_by_default() -> None:
    """Verify listener remains in DISABLED state when SWITCH_ENABLED=False."""
    with patch.object(settings, "SWITCH_ENABLED", False):
        listener = SwitchListener()
        status = listener.get_status()
        assert status.enabled is False
        assert status.state == SwitchConnectionState.DISABLED
        assert status.connected is False

        task = await listener.start()
        assert task is None


@pytest.mark.anyio
async def test_switch_listener_unconfigured_when_missing_credentials() -> None:
    """Verify listener enters UNCONFIGURED state when credentials are absent."""
    with patch.object(settings, "SWITCH_ENABLED", True), \
         patch.object(settings, "SWITCH_CORE_URL", None), \
         patch.object(settings, "SWITCH_API_KEY", None):
        listener = SwitchListener()
        status = listener.get_status()
        assert status.enabled is True
        assert status.configured is False
        assert status.state == SwitchConnectionState.UNCONFIGURED

        task = await listener.start()
        assert task is None


@pytest.mark.anyio
async def test_switch_listener_successful_connection_and_stop() -> None:
    """Verify listener transitions to CONNECTED upon successful WebSocket handshake and stops cleanly."""
    mock_ws = AsyncMock()
    mock_ws.recv = AsyncMock(side_effect=asyncio.CancelledError)
    mock_ws.close = AsyncMock()

    class MockConnectContext:
        async def __aenter__(self):
            return mock_ws
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    with patch.object(settings, "SWITCH_ENABLED", True), \
         patch.object(settings, "SWITCH_CORE_URL", "http://switch.mock:8080"), \
         patch.object(settings, "SWITCH_API_KEY", "sk_test_12345"), \
         patch("websockets.connect", return_value=MockConnectContext()):

        listener = SwitchListener()
        task = await listener.start()
        assert task is not None

        await asyncio.sleep(0.05)

        assert listener.connected is True
        assert listener.state == SwitchConnectionState.CONNECTED
        assert listener.last_connected_at is not None

        # Stop listener cleanly while connected
        await listener.stop()
        assert listener.connected is False
        assert listener.state == SwitchConnectionState.DISCONNECTED


@pytest.mark.anyio
async def test_switch_listener_reconnection_after_connection_lost() -> None:
    """Verify listener reconnects when connection is unexpectedly closed by server."""
    connection_attempts = 0

    mock_ws = AsyncMock()
    # First connection closes unexpectedly; second connection waits
    async def mock_recv():
        nonlocal connection_attempts
        if connection_attempts == 1:
            raise ConnectionClosed(None, None)
        await asyncio.sleep(1.0)
        return "{}"

    mock_ws.recv = AsyncMock(side_effect=mock_recv)
    mock_ws.close = AsyncMock()

    class MockConnectContext:
        async def __aenter__(self):
            nonlocal connection_attempts
            connection_attempts += 1
            return mock_ws
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    with patch.object(settings, "SWITCH_ENABLED", True), \
         patch.object(settings, "SWITCH_CORE_URL", "http://switch.mock:8080"), \
         patch.object(settings, "SWITCH_API_KEY", "sk_test_12345"), \
         patch.object(settings, "SWITCH_RECONNECT_INITIAL_DELAY", 0.05), \
         patch("websockets.connect", return_value=MockConnectContext()):

        listener = SwitchListener()
        task = await listener.start()
        assert task is not None

        # Wait enough time for initial disconnect and subsequent reconnect
        await asyncio.sleep(0.2)

        assert connection_attempts >= 2
        await listener.stop()


@pytest.mark.anyio
async def test_switch_listener_shutdown_while_connecting() -> None:
    """Verify listener handles cancellation and stops cleanly while in connecting state."""
    class SlowConnectContext:
        async def __aenter__(self):
            await asyncio.sleep(10.0)
            raise ConnectionRefusedError()
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    with patch.object(settings, "SWITCH_ENABLED", True), \
         patch.object(settings, "SWITCH_CORE_URL", "http://switch.mock:8080"), \
         patch.object(settings, "SWITCH_API_KEY", "sk_test_12345"), \
         patch("websockets.connect", return_value=SlowConnectContext()):

        listener = SwitchListener()
        task = await listener.start()
        assert task is not None

        await asyncio.sleep(0.05)
        assert listener.state == SwitchConnectionState.CONNECTING

        # Cancel while connecting
        await listener.stop()
        assert listener.state == SwitchConnectionState.DISCONNECTED
        assert listener.connected is False


@pytest.mark.anyio
async def test_switch_listener_repeated_startup_and_shutdown() -> None:
    """Verify listener handles repeated start and stop cycles safely without leaking tasks."""
    mock_ws = AsyncMock()
    async def mock_recv():
        await asyncio.sleep(100.0)
        return "{}"

    mock_ws.recv = AsyncMock(side_effect=mock_recv)
    mock_ws.close = AsyncMock()

    class MockConnectContext:
        async def __aenter__(self):
            return mock_ws
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    with patch.object(settings, "SWITCH_ENABLED", True), \
         patch.object(settings, "SWITCH_CORE_URL", "http://switch.mock:8080"), \
         patch.object(settings, "SWITCH_API_KEY", "sk_test_12345"), \
         patch("websockets.connect", return_value=MockConnectContext()):

        listener = SwitchListener()

        # Cycle 1
        t1 = await listener.start()
        assert t1 is not None
        await asyncio.sleep(0.02)
        # Duplicate start returns same running task
        assert await listener.start() == t1
        await listener.stop()
        assert listener.connected is False

        # Cycle 2
        t2 = await listener.start()
        assert t2 is not None
        await asyncio.sleep(0.02)
        await listener.stop()
        assert listener.connected is False


@pytest.mark.anyio
async def test_switch_listener_connection_failure_updates_state() -> None:
    """Verify failed connection records ERROR state without exposing raw secrets."""
    with patch.object(settings, "SWITCH_ENABLED", True), \
         patch.object(settings, "SWITCH_CORE_URL", "http://switch.mock:8080"), \
         patch.object(settings, "SWITCH_API_KEY", "sk_test_secret_key"), \
         patch.object(settings, "SWITCH_RECONNECT_INITIAL_DELAY", 0.05), \
         patch("websockets.connect", side_effect=ConnectionRefusedError("Connection refused")):

        listener = SwitchListener()
        task = await listener.start()
        assert task is not None

        await asyncio.sleep(0.05)

        assert listener.connected is False
        assert listener.state in (SwitchConnectionState.ERROR, SwitchConnectionState.DISCONNECTED)
        assert listener.last_error_at is not None
        assert "sk_test_secret_key" not in str(listener.last_error)

        await listener.stop()


def test_switch_listener_handle_raw_message() -> None:
    """Verify _handle_raw_message parses valid JSON and handles malformed frames safely."""
    listener = SwitchListener()
    valid_raw = json.dumps({
        "event_type": "room_message",
        "room_id": "ops-room",
        "message_id": "msg-001",
        "content": "Alert: high CPU",
    })
    listener._handle_raw_message(valid_raw)

    # Malformed non-JSON frame
    listener._handle_raw_message("not-a-valid-json-string")

    # Empty frame
    listener._handle_raw_message("")

    # Binary frame bytes
    listener._handle_raw_message(b'{"event_type": "ping"}')
