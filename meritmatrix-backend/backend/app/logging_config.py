"""
Centralized logging configuration.

Ensures consistent, structured-ish log output and prevents accidental
leakage of sensitive information (passwords, tokens, secrets) into logs.
"""
import logging
import sys

from app.config import get_settings

SENSITIVE_KEYS = {"password", "secret", "token", "authorization", "jwt"}


class RedactSensitiveFilter(logging.Filter):
    """Best-effort filter that redacts obviously sensitive substrings in log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:  # noqa: BLE001
            return True
        lowered = msg.lower()
        if any(key in lowered for key in SENSITIVE_KEYS):
            record.msg = "[log message redacted: potentially sensitive content]"
            record.args = ()
        return True


def configure_logging() -> None:
    settings = get_settings()

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL.upper())

    # Avoid duplicate handlers on reload
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    handler.addFilter(RedactSensitiveFilter())
    root_logger.addHandler(handler)

    # Quiet down noisy third-party loggers unless DEBUG
    if not settings.DEBUG:
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
