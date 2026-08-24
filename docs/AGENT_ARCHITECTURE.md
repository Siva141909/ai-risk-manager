# Agent Architecture — Phase 4

## 1. Scope and non-negotiable boundaries

The investigation agent is a read-only analyst, not a decision-maker. It
consumes a `Case` (never `CaseGroundTruth` — see `docs/CASE_MODEL.md` §1),
calls a fixed set of controlled tools, retrieves policy via RAG, and
produces a structured `InvestigationReport`. It never:

- calculates or changes the ML risk score/tier (`risk_tier` in its output
  is always the value it was given, `src/agents/graph.py::node_validate_report`)
- creates synthetic ground truth or accesses `CaseGroundTruth`
  (structurally impossible — `AgentInput`'s only constructor takes a
  `Case`, `src/agents/case_contract.py`)
- modifies transaction data, freezes accounts, or takes any irreversible
  action (`human_approval_required_for_action` is hardcoded `True` and
  validated, `src/agents/safety.py`)
- invents evidence (every citation must trace to a real tool call,
  `src/agents/safety.py::validate_investigation_report`)
- treats future/retrospective information as if it justified the
  original real-time decision (`src/agents/temporal.py`)
- overrides deterministic policy (policy chunks are cited, never used to
  change the risk tier)

## 2. LangGraph state machine

```
START
  -> validate_case
  -> collect_core_evidence           (customer context, transaction history, temporal activity, risk signals, previous cases)
  -> investigate_graph_context        (graph context, related entities, graph neighbors — SKIPPED if no graph evidence exists)
  -> retrieve_policy                   (SKIPPED if no shared-infrastructure pattern found)
  -> generate_investigation_report      (LLM call)
  -> validate_report                     (deterministic, Phase 4N)
       -(failed, attempts < max)-> generate_investigation_report  (repair, with error feedback)
       -(failed, attempts >= max)-> fail_safe_human_review
       -(passed)-> finalize
  -> END
```

Implemented in `src/agents/graph.py`. State is a `TypedDict`
(`src/agents/state.py`); nodes are closures over `ToolRegistry`,
`PolicyCorpus`, and `LLMClient` instances (`InvestigationGraphDeps`) so
the graph itself has no global or hidden state.

**Design deviation from the original proposal, and why:** the design
doc's Section 16 proposed separate LLM-routed nodes for "Investigate
Transaction History" and "Investigate Related Entities." These are
folded into bounded evidence-collection nodes that always make the same
fixed set of tool calls, rather than letting the LLM choose which tool
to call first. At 10 tools total, giving the LLM a routing decision
between two near-identical evidence-gathering steps adds latency and
non-determinism without adding investigative value — the LLM's judgment
is reserved for report *synthesis*, where it actually matters.

**Bounded repair loop:** `MAX_VALIDATION_ATTEMPTS = 1` — one repair
retry (the LLM is shown its own validation errors and asked to fix
them), then unconditional fail-safe routing to human review. This is
proven bounded by test, not just by reading the code
(`tests/integration/test_agent_investigation_pipeline.py::test_repair_loop_is_bounded_not_infinite`
asserts `call_count["n"] <= 3` against a client that *always* fabricates
evidence).

**Early-stop nodes:** `investigate_graph_context` and `retrieve_policy`
both no-op when the case has no graph evidence at all — there's nothing
structural to investigate or find policy guidance for, and skipping
saves tool calls and latency without skipping anything that would have
produced a real answer.

## 3. LLM backend architecture

`src/agents/graph.py` depends only on the `LLMClient` Protocol
(`src/agents/llm_client.py`) — one method, `generate(system_prompt,
user_prompt, max_tokens) -> str`. No LangGraph node, tool, or business
logic imports a specific provider SDK. Three implementations exist:

| Backend | `backend_name` | Deterministic | Network | Credential |
|---|---|---|---|---|
| `StubLLMClient` | `stub` | Yes | No | None |
| `ClaudeAgentSDKClient` | `claude_agent_sdk` | No | Yes | Local Claude Code auth only |
| `AnthropicAPIClient` | `anthropic_api` | No | Yes | `ANTHROPIC_API_KEY` (deployment-time) |

**`StubLLMClient`** — deterministic, offline, zero-cost. It does not
reason; it extracts the structured evidence bundle embedded in the
prompt (between `<<EVIDENCE_JSON>>...<<END_EVIDENCE_JSON>>` markers) and
fills a fixed template (`_stub_synthesize_report`). This is the *only*
backend the automated pytest suite uses — tests must be fast, free,
reproducible, and independent of auth/network. Every stub-produced
report is labeled `"backend": "stub"` and every summary field is
prefixed `"STUB TEST:"` so a stub result can never be mistaken for real
model output downstream.

**`ClaudeAgentSDKClient`** — uses the `claude_agent_sdk` Python package
(v0.2.144) to invoke the real Claude model through this development
environment's already-authenticated `claude` CLI installation. No
`ANTHROPIC_API_KEY`, nothing written to `.env`/source/config/git. Per
the explicit instruction governing this phase, the SDK's actual
installed API was inspected and a minimal live call verified working
*before* anything was built on top of it. Implementation:

```python
options = ClaudeAgentOptions(
    tools=[],                       # no tool access for the raw model call —
                                     # the investigation tools are orchestrated
                                     # by LangGraph, never exposed to the model
                                     # directly (controlled routing, §4 below)
    permission_mode="bypassPermissions",
    max_turns=1,
    system_prompt=system_prompt,
    model=model,
)
async for message in query(prompt=user_prompt, options=options):
    ...  # collect TextBlock text from AssistantMessage
```

Used only for qualitative agent evaluation and demo-case generation
(`scripts/run_agent_evaluation.py`), never in the automated test suite.
Labeled `"backend": "claude_agent_sdk"` everywhere in output, and every
report produced with it is referred to as a **CLAUDE DEVELOPMENT RUN**,
distinct from a hypothetical production **REAL API RUN** against
`AnthropicAPIClient`.

**`AnthropicAPIClient`** — deployment-ready interface for a standalone
`ANTHROPIC_API_KEY`. Constructing this class or importing this module
never requires the key or the `anthropic` package (lazy import inside
`.generate()`); it raises only at call time if the key is genuinely
absent. Never exercised in this project — no `ANTHROPIC_API_KEY` is
present in this environment, and none was requested.

**Switching backends later requires no changes to LangGraph, tool, or
business logic** — only a new/selected `LLMClient` implementation passed
into `InvestigationGraphDeps.llm_client`. This is structural (the graph
module has no `import anthropic` or `import claude_agent_sdk` at all
outside `llm_client.py`), not just a design intention.

## 4. Controlled tool routing (no arbitrary access)

The LLM never sees `src/tools/implementations.py` or any data source
directly. All 10 tools are called by LangGraph nodes through
`ToolRegistry.call(name, raw_args)` (`src/tools/registry.py`), which:

1. Checks `name` against a fixed allowlist (`ALLOWED_TOOL_NAMES`) —
   nothing outside `TOOL_REGISTRY` is callable.
2. Validates `raw_args` against that tool's strict Pydantic input schema
   (`extra="forbid"`) — malformed or extra arguments are rejected before
   dispatch, not passed through.
3. Enforces a per-investigation call budget
   (`MAX_TOOL_CALLS_PER_INVESTIGATION = 12`) and refuses more than
   `MAX_REPEATED_IDENTICAL_CALLS = 2` identical `(tool, args)` calls.
4. Catches tool execution failures explicitly and returns
   `{"error": ...}` rather than propagating a raw exception into the
   agent's context.

There is no SQL, no arbitrary code path, no dynamic dispatch by string
outside this registry. Full tool contracts: `docs/TOOL_CONTRACTS.md`.

## 5. Evidence, safety, and temporal boundaries

See `docs/SAFETY_MODEL.md` for prompt-injection defense and the
deterministic hallucination/evidence validator, and `docs/CASE_MODEL.md`
§5 (Phase 4 addendum) for the real-time/retrospective boundary.

## 6. What each test file proves

| File | Backend | Proves |
|---|---|---|
| `tests/unit/test_agent_case_contract.py` | none | `AgentInput` cannot be constructed with ground truth |
| `tests/unit/test_tool_schemas_and_authorization.py` | none | tool allowlist, schema rejection, budget enforcement, no ground-truth columns in any schema |
| `tests/unit/test_agent_temporal_boundary.py` | none | real-time cutoff filtering is enforced, not just documented |
| `tests/unit/test_agent_safety.py` | none | injection wrapping/detection, evidence-ID validation, all fail-closed rules |
| `tests/unit/test_rag_retrieval.py` | none | the 5 required Phase 4L retrieval scenarios |
| `tests/integration/test_agent_investigation_pipeline.py` | `StubLLMClient` | full graph wiring, early-stop routing, exact tier pass-through, malformed/fabricated-output fail-safe, bounded repair loop, tool-call budget |

None of these prove LLM reasoning *quality* — only pipeline, safety,
tool, and evidence-validation correctness. Quality can only be assessed
with real Claude reasoning; see `docs/AGENT_EVALUATION.md`.
