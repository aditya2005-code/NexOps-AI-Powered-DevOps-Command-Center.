from typing import Optional
from app.core.config import settings


def is_switch_configured() -> bool:
    """Check if all mandatory Switch credentials and endpoints are present."""
    return bool(
        settings.SWITCH_ENABLED
        and settings.SWITCH_CORE_URL
        and settings.SWITCH_API_KEY
    )


def get_switch_ws_url() -> Optional[str]:
    """Retrieve computed WebSocket URL for Switch Agent Bridge."""
    return settings.switch_ws_url


def get_switch_ops_url() -> Optional[str]:
    """Retrieve base HTTP URL for Switch operations."""
    return settings.switch_ops_url

