"""Phase 5A.7 — deterministic investigation cache.

An in-process cache, not a distributed one — Phase 5A.6 explicitly says
"do not introduce distributed infrastructure, keep it simple," and this
serves the same "keep it simple" goal. Its only job is to avoid calling
a real LLM twice for an identical investigation within one running
process.

**Cache key** = (case_id, investigation_mode, llm_backend, MODEL_VERSION,
GRAPH_CONFIG_VERSION). Including the backend name and both frozen
artifact versions means a result computed under one configuration is
never served back under a different one — e.g. a stub-backend result
is never returned for a request that asked (server-side) to run under
the Claude backend, and a cached result would be invalidated (a fresh
key) if the underlying model/graph version labels ever change.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class InvestigationCacheKey:
    case_id: str
    investigation_mode: str
    llm_backend: str
    model_version: str
    graph_config_version: str

    def as_tuple(self) -> tuple:
        return (
            self.case_id,
            self.investigation_mode,
            self.llm_backend,
            self.model_version,
            self.graph_config_version,
        )


class InvestigationCache:
    """Thread-safe (uvicorn may serve requests from a threadpool for the
    sync-blocking investigation path, Phase 5A.6) in-memory cache."""

    def __init__(self) -> None:
        self._store: dict[tuple, dict] = {}
        self._lock = Lock()

    def get(self, key: InvestigationCacheKey) -> dict | None:
        with self._lock:
            return self._store.get(key.as_tuple())

    def set(self, key: InvestigationCacheKey, report: dict) -> None:
        with self._lock:
            self._store[key.as_tuple()] = report

    def has_case(self, case_id: str) -> bool:
        """Used by case listing's investigation_status filter — true if
        ANY (mode, backend, version) combination has a cached report for
        this case_id."""
        with self._lock:
            return any(k[0] == case_id for k in self._store)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
