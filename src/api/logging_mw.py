"""Phase 5A.9 — structured request observability.

Every request gets a `request_id` (also returned as an `X-Request-Id`
response header and echoed in every error body, Phase 5A.5) and one
structured JSON log line at completion with duration, endpoint, and
status. Route/service code can log additional timing (agent duration,
case-lookup duration) tagged with the same `request_id` via
`request.state.request_id`.

No transaction-level field values (amounts, evidence text, report
content) are logged here — only IDs, durations, and outcomes, per the
explicit "do not log unnecessary transaction-level sensitive data"
instruction.
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.logging_conf import get_logger

logger = get_logger("api.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = uuid.uuid4().hex
        request.state.request_id = request_id
        start = time.monotonic()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
