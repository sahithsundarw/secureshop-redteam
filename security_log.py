"""Security event log (V8 fix): authentication, access denials and admin actions go to a file."""
import logging
from pathlib import Path

from flask import request, session

LOGGER = logging.getLogger("secureshop.security")


def init_logging(app):
    """Attach one file handler per log path (safe to call for every app instance)."""
    path = Path(app.config["LOG_PATH"]).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    LOGGER.setLevel(logging.INFO)
    if any(getattr(h, "baseFilename", None) == str(path) for h in LOGGER.handlers):
        return
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)


def log_event(event, detail, level=logging.INFO):
    """Write one line. Callers pass user-controlled text through repr() to block log forging."""
    LOGGER.log(level, "event=%s user=%s ip=%s %s", event, session.get("user_id"), request.remote_addr, detail)
