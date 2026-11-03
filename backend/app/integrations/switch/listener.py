import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional
import websockets
from websockets.exceptions import ConnectionClosed

from app.core.config import settings
from app.integrations.switch.config import is_switch_configured, get_switch_ws_url
from app.integrations.switch.schemas import (
    SwitchConnectionState,
    SwitchInboundEvent,
    SwitchStatusResponse,
)

logger = logging.getLogger("nexops.switch.listener")


class SwitchListener:
    """Asynchronous WebSocket connection manager for Switch Agent Bridge."""

    def __init__(self) -> None:
        self.state: SwitchConnectionState = SwitchConnectionState.DISABLED
        self.connected: bool = False
        self.last_connected_at: Optional[datetime] = None
        self.last_error_at: Optional[datetime] = None
        self.last_error: Optional[str] = None

        self._task: Optional[asyncio.Task] = None
        self._stop_event: asyncio.Event = asyncio.Event()
        self._current_ws: Optional[Any] = None

        self._refresh_initial_state()

    def _refresh_initial_state(self) -> None:
        """Update state based on current settings."""
        if not settings.SWITCH_ENABLED:
            self.state = SwitchConnectionState.DISABLED
        elif not is_switch_configured():
            self.state = SwitchConnectionState.UNCONFIGURED
        else:
            self.state = SwitchConnectionState.DISCONNECTED

    def get_status(self) -> SwitchStatusResponse:
        """Return the current connection status."""
        self._refresh_initial_state() if self.state in (
            SwitchConnectionState.DISABLED,
            SwitchConnectionState.UNCONFIGURED,
        ) else None

        return SwitchStatusResponse(
            enabled=settings.SWITCH_ENABLED,
            configured=is_switch_configured(),
            state=self.state,
            connected=self.connected,
            last_connected_at=self.last_connected_at,
            last_error_at=self.last_error_at,
            last_error=self.last_error,
        )

    async def start(self) -> Optional[asyncio.Task]:
        """Start the background WebSocket connection loop if enabled and configured."""
        if not settings.SWITCH_ENABLED:
            logger.info("Switch integration is disabled; skipping listener startup")
            self.state = SwitchConnectionState.DISABLED
            return None

        if not is_switch_configured():
            logger.warning("Switch integration is enabled but missing credentials; skipping listener startup")
            self.state = SwitchConnectionState.UNCONFIGURED
            return None

        if self._task is not None and not self._task.done():
            logger.info("Switch listener is already running")
            return self._task

        self._stop_event.clear()
        self._task = asyncio.create_task(self._run_loop(), name="nexops-switch-listener")
        logger.info("Started background Switch listener task")
        return self._task

    async def stop(self) -> None:
        """Gracefully stop the background connection loop and close WebSocket."""
        self._stop_event.set()

        if self._current_ws is not None:
            try:
                await self._current_ws.close()
            except Exception as exc:
                logger.debug("Error closing Switch websocket during stop: %s", exc)
            finally:
                self._current_ws = None

        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                logger.debug("Exception while waiting for Switch listener cancellation: %s", exc)
            finally:
                self._task = None

        self.connected = False
        self.state = (
            SwitchConnectionState.DISABLED
            if not settings.SWITCH_ENABLED
            else SwitchConnectionState.DISCONNECTED
        )
        logger.info("Switch listener stopped cleanly")

    async def _run_loop(self) -> None:
        """Main connection and reconnection loop with bounded exponential backoff."""
        ws_url = get_switch_ws_url()
        if not ws_url or not settings.SWITCH_API_KEY:
            self.state = SwitchConnectionState.UNCONFIGURED
            return

        reconnect_delay = settings.SWITCH_RECONNECT_INITIAL_DELAY

        while not self._stop_event.is_set():
            self.state = SwitchConnectionState.CONNECTING
            headers = {"Authorization": f"Bearer {settings.SWITCH_API_KEY}"}

            try:
                logger.info("Attempting WebSocket connection to Switch Agent Bridge")
                async with websockets.connect(
                    ws_url,
                    additional_headers=headers,
                    open_timeout=settings.SWITCH_CONNECTION_TIMEOUT,
                    ping_interval=30.0,
                    ping_timeout=10.0,
                    max_size=1_048_576,
                ) as ws:
                    self._current_ws = ws
                    self.connected = True
                    self.state = SwitchConnectionState.CONNECTED
                    self.last_connected_at = datetime.now(timezone.utc)
                    self.last_error = None
                    reconnect_delay = settings.SWITCH_RECONNECT_INITIAL_DELAY
                    logger.info("Successfully connected to Switch Agent Bridge")

                    while not self._stop_event.is_set():
                        try:
                            message = await ws.recv()
                            self._handle_raw_message(message)
                        except ConnectionClosed as exc:
                            logger.warning("Switch WebSocket closed: code=%s, reason=%s", exc.code, exc.reason)
                            break
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self.connected = False
                self.state = SwitchConnectionState.ERROR
                self.last_error_at = datetime.now(timezone.utc)
                self.last_error = f"{type(exc).__name__}: Connection attempt failed"
                logger.warning(
                    "Switch connection failure (%s). Reconnecting in %.1fs...",
                    type(exc).__name__,
                    reconnect_delay,
                )

            self.connected = False
            self._current_ws = None
            if not self._stop_event.is_set():
                self.state = SwitchConnectionState.DISCONNECTED
                try:
                    await asyncio.sleep(reconnect_delay)
                except asyncio.CancelledError:
                    break
                reconnect_delay = min(
                    reconnect_delay * 2,
                    settings.SWITCH_RECONNECT_MAX_DELAY,
                )

    def _handle_raw_message(self, raw_message: str | bytes) -> None:
        """Validate and log incoming protocol frames without logging sensitive content."""
        try:
            payload = json.loads(raw_message)
            event = SwitchInboundEvent(**payload)
            # Log only safe metadata
            logger.info(
                "Received Switch event: type=%s, room_id=%s, message_id=%s",
                event.event_type,
                event.room_id,
                event.message_id,
            )
        except json.JSONDecodeError:
            logger.warning("Received invalid non-JSON frame from Switch Agent Bridge")
        except Exception as exc:
            logger.warning("Failed to validate Switch inbound frame: %s", type(exc).__name__)


_global_listener: Optional[SwitchListener] = None


def get_switch_listener() -> SwitchListener:
    """Return the global singleton Switch listener instance."""
    global _global_listener
    if _global_listener is None:
        _global_listener = SwitchListener()
    return _global_listener

