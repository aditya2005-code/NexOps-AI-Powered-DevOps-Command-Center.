import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.integrations.switch.client import SwitchClient
from app.integrations.switch.exceptions import (
    SwitchAuthenticationError,
    SwitchConnectionError,
    SwitchOperationError,
)


@pytest.mark.anyio
async def test_switch_client_verify_connection_success() -> None:
    """Verify verify_connection succeeds when Switch returns 200."""
    client = SwitchClient(core_url="http://mock-switch:8080", api_key="sk_valid_key")
    mock_resp = httpx.Response(status_code=200, request=httpx.Request("GET", "http://mock-switch:8080/ops"))

    with patch.object(httpx.AsyncClient, "get", AsyncMock(return_value=mock_resp)):
        result = await client.verify_connection()
        assert result is True
    await client.aclose()


@pytest.mark.anyio
async def test_switch_client_authentication_failure() -> None:
    """Verify 401 raises SwitchAuthenticationError."""
    client = SwitchClient(core_url="http://mock-switch:8080", api_key="sk_invalid_key")
    mock_resp = httpx.Response(status_code=401, request=httpx.Request("GET", "http://mock-switch:8080/ops"))

    with patch.object(httpx.AsyncClient, "get", AsyncMock(return_value=mock_resp)):
        with pytest.raises(SwitchAuthenticationError):
            await client.verify_connection()
    await client.aclose()


@pytest.mark.anyio
async def test_switch_client_timeout_handling() -> None:
    """Verify timeout triggers SwitchConnectionError."""
    client = SwitchClient(core_url="http://mock-switch:8080", api_key="sk_key")

    with patch.object(httpx.AsyncClient, "get", AsyncMock(side_effect=httpx.TimeoutException("Read timed out"))):
        with pytest.raises(SwitchConnectionError, match="timed out"):
            await client.verify_connection()
    await client.aclose()


@pytest.mark.anyio
async def test_switch_client_connection_refused() -> None:
    """Verify network error triggers SwitchConnectionError."""
    client = SwitchClient(core_url="http://mock-switch:8080", api_key="sk_key")

    with patch.object(httpx.AsyncClient, "get", AsyncMock(side_effect=httpx.ConnectError("Connection refused"))):
        with pytest.raises(SwitchConnectionError, match="Failed to reach Switch core"):
            await client.verify_connection()
    await client.aclose()


@pytest.mark.anyio
async def test_switch_client_send_message_via_ops_dispatcher() -> None:
    """Verify send_message dispatches to official /ops with operation and args."""
    client = SwitchClient(core_url="http://mock-switch:8080", api_key="sk_key")
    mock_resp = httpx.Response(
        status_code=200,
        json={"message_id": "msg-12345", "status": "delivered"},
        request=httpx.Request("POST", "http://mock-switch:8080/ops"),
    )

    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=mock_resp)) as mock_post:
        response = await client.send_message(
            room_id="room-ops-general",
            content="Incident #INC-101 opened",
            thread_id="thread-root-99",
        )
        assert response.success is True
        assert response.operation == "send_message"
        assert response.data["message_id"] == "msg-12345"

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["operation"] == "send_message"
        assert call_kwargs["json"]["args"]["room_id"] == "room-ops-general"
        assert call_kwargs["json"]["args"]["content"] == "Incident #INC-101 opened"
        assert call_kwargs["json"]["args"]["thread_id"] == "thread-root-99"
    await client.aclose()


@pytest.mark.anyio
async def test_switch_client_send_message_fallback_routing() -> None:
    """Verify send_message falls back to /ops/{operation} if /ops returns 404."""
    client = SwitchClient(core_url="http://mock-switch:8080", api_key="sk_key")
    resp_404 = httpx.Response(
        status_code=404,
        request=httpx.Request("POST", "http://mock-switch:8080/ops"),
    )
    resp_200 = httpx.Response(
        status_code=200,
        json={"message_id": "msg-fallback", "status": "delivered"},
        request=httpx.Request("POST", "http://mock-switch:8080/ops/send_message"),
    )

    with patch.object(httpx.AsyncClient, "post", AsyncMock(side_effect=[resp_404, resp_200])) as mock_post:
        response = await client.send_message(
            room_id="room-ops-general",
            content="Fallback content",
        )
        assert response.success is True
        assert response.operation == "send_message"
        assert response.data["message_id"] == "msg-fallback"
        assert mock_post.call_count == 2
    await client.aclose()


@pytest.mark.anyio
async def test_switch_client_operation_failure() -> None:
    """Verify non-200 operation response raises SwitchOperationError."""
    client = SwitchClient(core_url="http://mock-switch:8080", api_key="sk_key")
    mock_resp = httpx.Response(
        status_code=500,
        request=httpx.Request("POST", "http://mock-switch:8080/ops"),
    )

    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(SwitchOperationError):
            await client.send_message(room_id="room-1", content="test")
    await client.aclose()


@pytest.mark.anyio
async def test_switch_client_operation_unauthorized() -> None:
    """Verify 403 on operation raises SwitchAuthenticationError."""
    client = SwitchClient(core_url="http://mock-switch:8080", api_key="sk_key")
    mock_resp = httpx.Response(
        status_code=403,
        request=httpx.Request("POST", "http://mock-switch:8080/ops"),
    )

    with patch.object(httpx.AsyncClient, "post", AsyncMock(return_value=mock_resp)):
        with pytest.raises(SwitchAuthenticationError, match="Unauthorized Switch operation"):
            await client.send_message(room_id="room-1", content="test")
    await client.aclose()


def test_switch_client_secret_redaction() -> None:
    """Verify representation masks secret API key."""
    client = SwitchClient(core_url="http://mock-switch:8080", api_key="sk_super_secret_token_12345")
    representation = repr(client)
    assert "sk_super_secret_token_12345" not in representation
    assert "sk_s***" in representation or "***" in representation
