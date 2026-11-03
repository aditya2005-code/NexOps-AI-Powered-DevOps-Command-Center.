class SwitchIntegrationError(Exception):
    """Base exception for Switch integration failures."""
    pass


class SwitchConnectionError(SwitchIntegrationError):
    """Raised when transport connection to Switch Agent Bridge fails or drops."""
    pass


class SwitchAuthenticationError(SwitchIntegrationError):
    """Raised when credentials or token verification fails against Switch."""
    pass


class SwitchProtocolError(SwitchIntegrationError):
    """Raised when an unexpected or malformed protocol frame is encountered."""
    pass


class SwitchOperationError(SwitchIntegrationError):
    """Raised when an outgoing Switch operation (e.g. send_message) fails."""
    pass

