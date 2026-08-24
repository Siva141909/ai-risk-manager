"""Phase 5A.8 — basic API protections implemented as middleware.

Request body size limiting only — the rest of Phase 5A.8's list (allowed
enum values, no client-controlled risk tier, no arbitrary SQL/tool/
filesystem access) is satisfied structurally elsewhere: `extra="forbid"`
+ `Literal` types on every request schema (`src/api/schemas.py`), the
existing tool allowlist (`src/tools/registry.py`, untouched), and the
fact that no route or service ever builds a SQL string or accepts a
filesystem path from client input. See docs/API.md's security section
for the full list mapped to its enforcement point.

This is a Content-Length pre-check, not a streaming byte-counter — a
client that omits Content-Length and streams a large chunked body past
this check is a known simplification, acceptable at demo scale and
documented rather than silently assumed away.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int) -> None:
        super().__init__(app)
        self._max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                length = 0
            if length > self._max_bytes:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error_code": "request_too_large",
                        "message": f"request body exceeds the {self._max_bytes}-byte limit",
                        "request_id": getattr(request.state, "request_id", ""),
                    },
                )
        return await call_next(request)
