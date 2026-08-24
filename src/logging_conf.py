"""Logging convention for the project.

Section 29 of the design doc requires structured JSON logging for the
non-agent parts of the pipeline. This sets that convention up now, at
minimum, so every later module logs consistently instead of each one
picking its own format.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


_STANDARD_LOGRECORD_ATTRS = frozenset(logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys())


class JsonFormatter(logging.Formatter):
    """Any field passed via `logger.info(msg, extra={...})` is merged
    into the JSON payload alongside the standard fields — added for
    Phase 5A's structured request/investigation logging
    (`src/api/logging_mw.py`), additive only: a call with no `extra`
    produces exactly the same output as before."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOGRECORD_ATTRS and key not in payload:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger configured with the project's JSON format."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
