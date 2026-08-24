"""Phase 4C/4G — the tool allowlist and controlled dispatch.

The LLM never gets direct access to `src/tools/implementations.py` or
any data source. It can only call `ToolRegistry.call(name, raw_args)`,
which: (1) checks `name` against a fixed allowlist, (2) validates
`raw_args` against that tool's strict Pydantic input schema — rejecting
anything else, (3) enforces a per-investigation call budget, (4) catches
and reports tool failures explicitly rather than propagating a raw
exception into the agent's context. There is no SQL, no arbitrary code
path, no way to call anything not in `TOOL_REGISTRY`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from pydantic import BaseModel, ValidationError

from src.tools import implementations as impl
from src.tools.context import ToolDataContext
from src.tools.schemas import (
    CustomerContextInput,
    GraphContextInput,
    GraphNeighborsInput,
    MerchantContextInput,
    PolicyQueryInput,
    PreviousCasesInput,
    RelatedEntitiesInput,
    RiskSignalsInput,
    TemporalActivityInput,
    TransactionHistoryInput,
)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    input_schema: type[BaseModel]
    fn: Callable[..., BaseModel]
    needs_corpus: bool = False


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "get_transaction_history": ToolSpec("get_transaction_history", TransactionHistoryInput, impl.get_transaction_history),
    "get_customer_context": ToolSpec("get_customer_context", CustomerContextInput, impl.get_customer_context),
    "get_related_entities": ToolSpec("get_related_entities", RelatedEntitiesInput, impl.get_related_entities),
    "get_graph_context": ToolSpec("get_graph_context", GraphContextInput, impl.get_graph_context),
    "get_graph_neighbors": ToolSpec("get_graph_neighbors", GraphNeighborsInput, impl.get_graph_neighbors),
    "get_temporal_activity": ToolSpec("get_temporal_activity", TemporalActivityInput, impl.get_temporal_activity),
    "get_merchant_context": ToolSpec("get_merchant_context", MerchantContextInput, impl.get_merchant_context),
    "get_previous_cases": ToolSpec("get_previous_cases", PreviousCasesInput, impl.get_previous_cases),
    "get_risk_signals": ToolSpec("get_risk_signals", RiskSignalsInput, impl.get_risk_signals),
    "get_policy": ToolSpec("get_policy", PolicyQueryInput, impl.get_policy, needs_corpus=True),
}

ALLOWED_TOOL_NAMES = frozenset(TOOL_REGISTRY.keys())

MAX_TOOL_CALLS_PER_INVESTIGATION = 12
MAX_REPEATED_IDENTICAL_CALLS = 2  # calling the exact same (tool, args) more than this is refused


class ToolAuthorizationError(ValueError):
    """Raised for a tool name outside the allowlist — never silently ignored."""


class ToolCallBudgetExceeded(RuntimeError):
    pass


@dataclass
class ToolCallLog:
    name: str
    args: dict
    ok: bool
    error: str | None = None


@dataclass
class ToolRegistry:
    """One instance per investigation — call budget and repeat-call
    tracking are per-case, not global, so one case's investigation can
    never starve another's budget."""

    ctx: ToolDataContext
    corpus: Any = None
    max_calls: int = MAX_TOOL_CALLS_PER_INVESTIGATION
    call_log: list[ToolCallLog] = field(default_factory=list)
    _call_counts: dict[tuple, int] = field(default_factory=dict)

    def call(self, name: str, raw_args: dict) -> dict:
        if len(self.call_log) >= self.max_calls:
            raise ToolCallBudgetExceeded(
                f"Tool call budget ({self.max_calls}) exceeded for this investigation."
            )
        if name not in ALLOWED_TOOL_NAMES:
            self.call_log.append(ToolCallLog(name=name, args=raw_args, ok=False, error="not in allowlist"))
            raise ToolAuthorizationError(f"Tool '{name}' is not in the allowlist: {sorted(ALLOWED_TOOL_NAMES)}")

        spec = TOOL_REGISTRY[name]
        call_key = (name, tuple(sorted(raw_args.items())))
        self._call_counts[call_key] = self._call_counts.get(call_key, 0) + 1
        if self._call_counts[call_key] > MAX_REPEATED_IDENTICAL_CALLS:
            error = f"identical call to '{name}' repeated more than {MAX_REPEATED_IDENTICAL_CALLS} times — refused"
            self.call_log.append(ToolCallLog(name=name, args=raw_args, ok=False, error=error))
            return {"error": error}

        try:
            validated_input = spec.input_schema(**raw_args)
        except ValidationError as e:
            error = f"schema validation failed: {e}"
            self.call_log.append(ToolCallLog(name=name, args=raw_args, ok=False, error=error))
            return {"error": error}

        try:
            if spec.needs_corpus:
                result = spec.fn(self.ctx, validated_input, self.corpus)
            else:
                result = spec.fn(self.ctx, validated_input)
        except Exception as e:  # noqa: BLE001 — tool failures must be represented explicitly, never crash the investigation
            error = f"tool execution failed: {type(e).__name__}: {e}"
            self.call_log.append(ToolCallLog(name=name, args=raw_args, ok=False, error=error))
            return {"error": error}

        self.call_log.append(ToolCallLog(name=name, args=raw_args, ok=True))
        return result.model_dump()

    def calls_remaining(self) -> int:
        return self.max_calls - len(self.call_log)
