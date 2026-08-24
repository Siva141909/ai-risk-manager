"""LLM client abstraction — Phase 4.

The LangGraph investigation workflow (src/agents/graph.py) depends ONLY
on the `LLMClient` protocol below, never on a specific provider SDK —
swapping providers requires a new implementation of this one method,
not touching graph/tool/business logic.

Three implementations, each with a different purpose — never confuse
their outputs:

- `StubLLMClient` — deterministic, offline, zero-cost, zero network
  calls. The ONLY backend the automated pytest suite uses (tests must be
  fast, free, reproducible, and independent of auth/network). It does
  NOT reason in natural language — it deterministically extracts the
  structured evidence bundle embedded in the prompt and fills a template
  report, citing only the evidence IDs it was given. This exercises the
  surrounding pipeline (tool routing, schema conformance, citation
  discipline) but produces no real investigative judgment. Every report
  built with it is labeled `"backend": "stub"` — never reported as a
  quality result.

- `ClaudeAgentSDKClient` — uses the `claude_agent_sdk` package (the
  Python SDK for Claude Code) to invoke the real Claude model this
  development environment is already authenticated for, via the local
  `claude` CLI installation — no separate API key, nothing written to
  any file or config. Verified working in this environment (see
  docs/AGENT_ARCHITECTURE.md). Used ONLY for qualitative agent
  evaluation and demo-case generation, never in the automated test
  suite (real network calls, real cost, non-deterministic). Labeled
  `"backend": "claude_agent_sdk"`.

- `AnthropicAPIClient` — deployment-ready interface for a standalone
  `ANTHROPIC_API_KEY` environment variable, for when this system runs
  independently of a Claude Code development environment. Implemented
  but only exercised if a key is present in the environment at call
  time — never required, never requested from the user, never written
  to any file. Labeled `"backend": "anthropic_api"`.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Every implementation must be synchronous and side-effect-free
    beyond the model call itself — no LangGraph node should need to know
    which backend it's talking to."""

    backend_name: str

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        """Return the model's raw text response."""
        ...


_EVIDENCE_BLOCK_RE = re.compile(r"<<EVIDENCE_JSON>>(.*?)<<END_EVIDENCE_JSON>>", re.DOTALL)


class StubLLMClient:
    """Deterministic, offline, zero-cost — see module docstring. Reads a
    structured evidence bundle the caller embeds in the prompt between
    `<<EVIDENCE_JSON>>`/`<<END_EVIDENCE_JSON>>` markers
    (src/agents/graph.py's report-generation node always does this) and
    deterministically synthesizes a schema-conformant response —
    template-filling, not reasoning.
    """

    backend_name = "stub"

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        match = _EVIDENCE_BLOCK_RE.search(user_prompt)
        if not match:
            return json.dumps(
                {
                    "summary": "STUB TEST: no evidence bundle found in prompt.",
                    "recommendation": "investigate_further",
                    "confidence": 0.0,
                    "evidence": [],
                }
            )
        bundle = json.loads(match.group(1))
        return json.dumps(_stub_synthesize_report(bundle))


def _stub_synthesize_report(bundle: dict) -> dict:
    """Deterministic template — same bundle always produces the same
    report. This is explicitly NOT investigative reasoning; it exists so
    the surrounding validation/safety/schema layers can be tested
    without a live model call."""
    evidence_items = [
        {
            "evidence_id": e["evidence_id"],
            "source_tool": e["source_tool"],
            "summary": f"STUB TEST: evidence returned by {e['source_tool']}.",
            "is_retrospective": e["source_tool"] in ("get_graph_context", "get_related_entities", "get_graph_neighbors", "get_policy"),
        }
        for e in bundle.get("evidence_items", [])
    ]
    has_graph_evidence = bundle.get("graph_evidence") is not None
    ml_tier = bundle.get("ml_risk_tier", "LOW")

    conflict_description = None
    conflicting = ml_tier in ("LOW", "MEDIUM") and has_graph_evidence
    if conflicting:
        recommendation = "investigate_further"
        summary = (
            "STUB TEST: ML risk tier is low/medium but graph evidence indicates shared "
            "infrastructure with other customer proxies — evidence is conflicting."
        )
        conflict_description = (
            "STUB TEST: structural graph evidence (shared infrastructure) suggests coordination risk, "
            "but the individual transaction's real-time ML risk score is low/medium — these two "
            "signals point in different directions and are not reconciled here."
        )
    elif ml_tier in ("HIGH", "CRITICAL") and has_graph_evidence:
        recommendation = "escalate_to_human_analyst"
        summary = "STUB TEST: elevated ML risk tier corroborated by graph evidence of shared infrastructure."
    elif ml_tier in ("HIGH", "CRITICAL"):
        recommendation = "escalate_to_human_analyst"
        summary = "STUB TEST: elevated ML risk tier with no graph-level corroboration available."
    else:
        recommendation = "close"
        summary = "STUB TEST: low ML risk tier and no graph evidence found."

    return {
        "summary": summary,
        "graph_findings": bundle.get("graph_evidence", {}).get("narrative", "No graph evidence available.")
        if has_graph_evidence else "No graph evidence available.",
        "behavioral_findings": "STUB TEST: behavioral synthesis not performed by the deterministic stub.",
        "legitimate_explanations": (
            ["Shared infrastructure may reflect a legitimate household, office, or business context."]
            if has_graph_evidence else []
        ),
        "conflicting_evidence": conflicting,
        "conflict_description": conflict_description,
        "policy_findings": [c["citation"] for c in bundle.get("policy_chunks", [])],
        "recommendation": recommendation,
        "confidence": 0.5,
        "evidence": evidence_items,
        "requires_human_review": ml_tier in ("HIGH", "CRITICAL") or conflicting or recommendation == "escalate_to_human_analyst",
    }


class ClaudeAgentSDKClient:
    """Uses claude_agent_sdk.query() — the local, already-authenticated
    Claude Code environment. No API key. See module docstring."""

    backend_name = "claude_agent_sdk"

    def __init__(self, model: str | None = None, max_turns: int = 1) -> None:
        self.model = model
        self.max_turns = max_turns

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        import asyncio

        return asyncio.run(self._agenerate(system_prompt, user_prompt))

    async def _agenerate(self, system_prompt: str, user_prompt: str) -> str:
        from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

        options = ClaudeAgentOptions(
            tools=[],  # no tool access for the LLM call itself — the investigation
                       # agent's tools (src/tools/) are orchestrated by LangGraph, not
                       # exposed to the raw model call here (Phase 4G: controlled routing)
            permission_mode="bypassPermissions",
            max_turns=self.max_turns,
            system_prompt=system_prompt,
            model=self.model,
        )
        chunks: list[str] = []
        async for message in query(prompt=user_prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        chunks.append(block.text)
        return "".join(chunks)


class AnthropicAPIClient:
    """Deployment-ready interface for ANTHROPIC_API_KEY. Never required,
    never requested from the user, never written anywhere. Raises only
    at call time if the key is genuinely absent — importing/constructing
    this class never requires the key or the `anthropic` package."""

    backend_name = "anthropic_api"

    def __init__(self, model: str = "claude-sonnet-5") -> None:
        self.model = model

    def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "AnthropicAPIClient requires ANTHROPIC_API_KEY in the environment. "
                "This is a deployment-time backend for running independently of a "
                "Claude Code development environment — not required for development "
                "or testing, which use StubLLMClient / ClaudeAgentSDKClient instead."
            )
        import anthropic  # lazy import — this package is not a hard dependency for development/testing

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return "".join(block.text for block in response.content if hasattr(block, "text"))


@dataclass(frozen=True)
class LLMBackendInfo:
    backend_name: str
    is_deterministic: bool
    requires_network: bool
    requires_credential: str | None


BACKEND_INFO = {
    "stub": LLMBackendInfo("stub", is_deterministic=True, requires_network=False, requires_credential=None),
    "claude_agent_sdk": LLMBackendInfo(
        "claude_agent_sdk", is_deterministic=False, requires_network=True,
        requires_credential="local Claude Code authentication (no separate API key)",
    ),
    "anthropic_api": LLMBackendInfo(
        "anthropic_api", is_deterministic=False, requires_network=True, requires_credential="ANTHROPIC_API_KEY"
    ),
}
