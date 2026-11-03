from app.core.config import Settings
from app.integrations.switch.config import is_switch_configured, get_switch_ws_url, get_switch_ops_url


def test_switch_disabled_by_default() -> None:
    """Verify Switch integration defaults to disabled."""
    settings = Settings(SWITCH_ENABLED=False)
    assert settings.SWITCH_ENABLED is False
    assert settings.switch_ws_url is None
    assert settings.switch_ops_url is None


def test_switch_unconfigured_when_credentials_missing() -> None:
    """Verify integration reports unconfigured if URL or API key is absent."""
    settings = Settings(SWITCH_ENABLED=True, SWITCH_CORE_URL=None, SWITCH_API_KEY=None)
    assert settings.SWITCH_ENABLED is True
    assert not is_switch_configured()


def test_switch_url_translation_http() -> None:
    """Verify http URL generates ws WebSocket URL."""
    settings = Settings(
        SWITCH_ENABLED=True,
        SWITCH_CORE_URL="http://switch.internal:8080/",
        SWITCH_API_KEY="sk_test_key",
    )
    assert settings.switch_ws_url == "ws://switch.internal:8080/gateway/changes/ws"
    assert settings.switch_ops_url == "http://switch.internal:8080/ops"


def test_switch_url_translation_https() -> None:
    """Verify https URL generates wss WebSocket URL."""
    settings = Settings(
        SWITCH_ENABLED=True,
        SWITCH_CORE_URL="https://switch.company.com",
        SWITCH_API_KEY="sk_test_key",
    )
    assert settings.switch_ws_url == "wss://switch.company.com/gateway/changes/ws"
    assert settings.switch_ops_url == "https://switch.company.com/ops"


def test_switch_timeout_and_backoff_defaults() -> None:
    """Verify default backoff and timeout parameters."""
    settings = Settings()
    assert settings.SWITCH_RECONNECT_INITIAL_DELAY == 2.0
    assert settings.SWITCH_RECONNECT_MAX_DELAY == 60.0
    assert settings.SWITCH_CONNECTION_TIMEOUT == 15.0

