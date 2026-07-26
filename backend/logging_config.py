"""
logging_config.py — single source of truth for backend logging.

Call setup_logging() once at process start (done in main.py). Everywhere else:

    from logging_config import get_logger
    log = get_logger("indexer")        # -> logger named "localfind.indexer"
    log.info("indexing %s", path)

Why this exists:
  - Consistent, greppable format across every module (timestamp | level | name).
  - Logs go to BOTH stdout and a rotating file (backend/logs/backend.log), so you
    can `tail -f backend/logs/backend.log` while testing and nothing scrolls away.
  - One place to set the level: LOG_LEVEL=DEBUG in .env to see every step,
    INFO (default) for normal use.
  - Noisy third-party libraries are capped at WARNING so our signal stays readable.
"""
import logging
import logging.handlers
import os
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent / "logs"
LOG_FILE = LOG_DIR / "backend.log"

# Third-party loggers we don't want drowning out our own logs.
_NOISY_LIBRARIES = [
    "httpx", "httpcore", "openai", "chromadb", "chromadb.telemetry",
    "watchfiles", "urllib3", "PIL", "uvicorn.access", "asyncio",
]

_configured = False


def setup_logging(level: str | None = None) -> None:
    """Configure root logging. Idempotent — safe to call more than once."""
    global _configured
    if _configured:
        return

    level_name = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    log_level = getattr(logging, level_name, logging.INFO)

    LOG_DIR.mkdir(exist_ok=True)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(log_level)
    # Drop any handlers already installed (uvicorn, a stray basicConfig, etc.)
    # so we don't emit every line two or three times.
    root.handlers.clear()

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(fmt)
    root.addHandler(stream_handler)

    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    for name in _NOISY_LIBRARIES:
        logging.getLogger(name).setLevel(logging.WARNING)

    _configured = True
    logging.getLogger("localfind").info(
        "Logging ready — level=%s, file=%s", level_name, LOG_FILE
    )


def get_logger(name: str) -> logging.Logger:
    """Namespaced logger: get_logger('indexer') -> logging.getLogger('localfind.indexer')."""
    if name == "localfind" or name.startswith("localfind."):
        return logging.getLogger(name)
    return logging.getLogger(f"localfind.{name}")
