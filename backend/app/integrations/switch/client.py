import logging
from typing import Any, Dict, Optional
import httpx

from app.integrations.switch.exceptions import (
    SwitchAuthenticationError,
    SwitchConnectionError,
    SwitchOperationError,
)
from app.integrations.switch.schemas import (
    SwitchOperationResponse,
    SwitchSendMessageRequest,
)

logger = logging.getLogger("nexops.switch.client")


class SwitchClient:
    """Asynchronous HTTP client for communicating with Switch Core HTTP /ops."""

    def __init__(
        self,
        core_url: str,
        api_key: str,
        timeout: float = 15.0,
    ) -> None:
        self.core_url = core_url.rstrip("/")
        self._api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "User-Agent": "NexOps-Agent-Bridge/0.1.0",
        }

    async def get_http_client(self) -> httpx.AsyncClient:
        """Lazily initialize and return the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                headers=self._get_headers(),
            )
        return self._client

    async def verify_connection(self) -> bool:
        """Verify reachability and authentication against Switch Core."""
        client = await self.get_http_client()
        url = f"{self.core_url}/ops"
        try:
            response = await client.get(url)
            if response.status_code == 401 or response.status_code == 403:
                raise SwitchAuthenticationError("Switch authentication failed: invalid API key or insufficient permissions")
            if response.status_code >= 500:
                raise SwitchConnectionError(f"Switch core returned server error: {response.status_code}")
            return response.is_success or response.status_code in (200, 404, 405)
        except httpx.TimeoutException as exc:
            logger.warning("Switch core connection timed out during verification")
            raise SwitchConnectionError("Switch core connection timed out") from exc
        except httpx.RequestError as exc:
            logger.warning("Switch core request failed: %s", type(exc).__name__)
            raise SwitchConnectionError(f"Failed to reach Switch core at {self.core_url}") from exc

    async def send_message(
        self,
        room_id: str,
        content: str,
        thread_id: Optional[str] = None,
    ) -> SwitchOperationResponse:
        """Dispatch an outbound message into a Switch room via /ops."""
        payload = SwitchSendMessageRequest(
            room_id=room_id,
            content=content,
            thread_id=thread_id,
        )
        return await self.execute_operation(
            operation="send_message",
            payload=payload.model_dump(exclude_none=True),
        )

    async def execute_operation(
        self,
        operation: str,
        payload: Dict[str, Any],
    ) -> SwitchOperationResponse:
        """Execute a registered operation on Switch Core via /ops or path-routed fallback."""
        client = await self.get_http_client()
        # Official Switch protocol mounts /ops as the primary operation dispatch surface
        url = f"{self.core_url}/ops"
        body = {
            "operation": operation,
            "args": payload,
        }
        try:
            response = await client.post(url, json=body)
            # If the endpoint uses direct path-routing /ops/{operation} and /ops returned 404, fallback cleanly
            if response.status_code == 404:
                fallback_url = f"{self.core_url}/ops/{operation}"
                fallback_resp = await client.post(fallback_url, json=payload)
                if fallback_resp.is_success or fallback_resp.status_code in (401, 403):
                    response = fallback_resp

            if response.status_code in (401, 403):
                raise SwitchAuthenticationError(f"Unauthorized Switch operation '{operation}'")
            if not response.is_success:
                raise SwitchOperationError(
                    f"Switch operation '{operation}' failed with status {response.status_code}"
                )
            data = response.json() if response.content else {}
            return SwitchOperationResponse(
                success=True,
                operation=operation,
                data=data if isinstance(data, dict) else {"result": data},
            )
        except httpx.TimeoutException as exc:
            raise SwitchConnectionError(f"Timeout executing Switch operation '{operation}'") from exc
        except httpx.RequestError as exc:
            raise SwitchConnectionError(f"Network error executing Switch operation '{operation}'") from exc

    async def aclose(self) -> None:
        """Gracefully close the underlying HTTPX client session."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "SwitchClient":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.aclose()

    def __repr__(self) -> str:
        # Redact API key to avoid leakage in logs and tracebacks
        masked_key = self._api_key[:4] + "***" if len(self._api_key) > 4 else "***"
        return f"SwitchClient(core_url='{self.core_url}', api_key='{masked_key}')"

