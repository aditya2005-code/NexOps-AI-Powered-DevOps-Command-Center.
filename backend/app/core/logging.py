import logging
import sys
from typing import Optional
from app.core.config import settings


def setup_logging(log_level: Optional[str] = None) -> None:
    """Configure centralized structured logging for NexOps."""
    level_str = log_level or settings.LOG_LEVEL
    numeric_level = getattr(logging, level_str.upper(), logging.INFO)

    log_format = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    logging.basicConfig(
        stream=sys.stdout,
        level=numeric_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )

    # Set specific third-party logger levels to prevent noisy token/key leakages
    logging.getLogger("uvicorn.access").setLevel(numeric_level)
    logging.getLogger("uvicorn.error").setLevel(numeric_level)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance with the standard configuration."""
    return logging.getLogger(name)
