import enum
import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class SwitchConnectionState(str, enum.Enum):
    """Lifecycle states of the Switch integration connection."""
    DISABLED = "disabled"
    UNCONFIGURED = "unconfigured"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class SwitchStatusResponse(BaseModel):
    """Sanitized status model exposed to health and status endpoints."""
    enabled: bool
    configured: bool
    state: SwitchConnectionState
    connected: bool
    agent_id: Optional[str] = None
    last_connected_at: Optional[datetime] = None
    last_error_at: Optional[datetime] = None
    last_error: Optional[str] = None


class SwitchInboundEvent(BaseModel):
    """Pydantic schema representing verified incoming Switch Agent Bridge event frames."""
    event_type: str = Field(..., max_length=100)
    room_id: Optional[str] = Field(None, max_length=255)
    message_id: Optional[str] = Field(None, max_length=255)
    sender_id: Optional[str] = Field(None, max_length=255)
    sender_name: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = Field(None, max_length=10000)
    thread_id: Optional[str] = Field(None, max_length=255)
    timestamp: Optional[datetime] = None


class SwitchSendMessageRequest(BaseModel):
    """Payload for outbound message delivery via HTTP /ops/send_message."""
    room_id: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1, max_length=10000)
    thread_id: Optional[str] = Field(None, max_length=255)


class SwitchOperationResponse(BaseModel):
    """Standard response from Switch HTTP operations endpoint."""
    success: bool
    operation: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class SwitchIntakeResult(BaseModel):
    """Result of processing an inbound Switch room message for incident intake."""
    status: str = Field(..., description="Intake outcome: created, duplicate, rejected_unmapped_room, persistence_failure, invalid_event")
    incident_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    room_id: Optional[str] = None
    message_id: Optional[str] = None
    acknowledgement_sent: bool = False
    detail: Optional[str] = None

