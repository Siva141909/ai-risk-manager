# Tool Contracts — Phase 4C/4D/4G

10 read-only tools, each: (a) takes a validated Pydantic input, (b)
returns a validated Pydantic output, (c) is a pure function of
`ToolDataContext` + input — deterministic, same input always produces
the same output, (d) never touches ground-truth columns (not present in
the context at all — see authorization boundary below), (e) never
writes anything. All schemas: `src/tools/schemas.py`. All
implementations: `src/tools/implementations.py`. Dispatch: `src/tools/registry.py`.

## Authorization boundary (defense in depth)

`ToolDataContext.transactions_graph` is built by *selecting only safe
columns* from the synthetic-graph transaction table
(`SAFE_GRAPH_COLUMNS`, `src/tools/context.py`). Ground-truth columns —
`original_isFraud`, `synthetic_ring_id`, `synthetic_abuse_type`,
`synthetic_ring_role`, `legitimate_cluster_id`, `legitimate_cluster_type`,
`synthetic_entity_label` — are never loaded into this object at all, so
no tool built on top of it can leak them, however it's written. This is
on top of each tool's own output schema never having a field for them
(`extra="forbid"` on every schema, checked directly by
`tests/unit/test_tool_schemas_and_authorization.py`).

## Evidence IDs

Every tool output includes one or more `evidence_id` fields, generated
deterministically: `evidence_id(prefix, *parts) = f"{prefix}-{sha256(':'.join(parts))[:8].upper()}"`
(`src/tools/context.py`). Same underlying fact always produces the same
ID. The agent can only ever *cite* an ID that was actually returned by a
tool call in its own investigation — it cannot invent one (enforced
deterministically, `docs/SAFETY_MODEL.md`).

## Real-time vs. retrospective (Phase 4E)

Tools that accept `cutoff_dt` filter strictly to `TransactionDT <
cutoff_dt` when it is set (real-time mode) — enforced in the filtering
logic itself (`src/tools/implementations.py::_customer_rows` and
equivalent per-tool filters), not just documented. When `cutoff_dt` is
`None`, the tool runs in retrospective mode and tags its output
`mode="retrospective"`, so a caller — or the LLM reading the evidence
bundle — can never confuse "known at decision time" with "known now."
See `docs/CASE_MODEL.md` §5 for the full boundary model.

## The 10 tools

| Tool | Input | Cutoff-aware | Purpose |
|---|---|---|---|
| `get_transaction_history` | `customer_proxy_id`, `cutoff_dt?`, `max_results` | Yes | Up to N prior transactions for this customer proxy |
| `get_customer_context` | `customer_proxy_id` | No | Proxy confidence level, total known transaction count |
| `get_related_entities` | `customer_proxy_id` | No | Devices/IPs/bank accounts this customer shares with ≥1 other customer |
| `get_graph_context` | `customer_proxy_id` | No | The full Phase 3 deterministic graph signal set + narrative for this customer's community |
| `get_graph_neighbors` | `customer_proxy_id`, `relationship_type`, `max_results` | No | Other customers sharing a specific entity (device/IP/bank account) |
| `get_temporal_activity` | `customer_proxy_id`, `cutoff_dt?` | Yes | Transaction-count and recency features from Phase 2's frozen feature table |
| `get_merchant_context` | `product_cd` | No | Category-level context only — `ProductCD` is a 5-value product code, not a merchant identity (`docs/FEATURE_AUDIT.md`) |
| `get_previous_cases` | `customer_proxy_id`, `cutoff_dt?` | Yes | Prior HIGH/CRITICAL-tier transactions for this customer, as a documented proxy for case history (no persisted case DB exists yet — Phase 4 is the first agent phase) |
| `get_risk_signals` | `case_id` | No | Rule-flag signals attached to this case, if any |
| `get_policy` | `query`, `applies_to_pattern?`, `max_results` | No | RAG retrieval over the demo policy corpus — see `docs/RAG_POLICY.md` |

Each is a thin, pure function; none does I/O beyond reading the
in-memory `ToolDataContext` (and, for `get_policy`, the `PolicyCorpus`
passed in separately since it's an independently testable subsystem).

## Dispatch and enforcement (`ToolRegistry`)

`ToolRegistry` is instantiated once per investigation — its call budget
and repeated-call tracking are per-instance, so one case's investigation
can never starve another's budget:

- **Allowlist**: `name not in ALLOWED_TOOL_NAMES` raises
  `ToolAuthorizationError` immediately, logged before raising.
- **Schema validation**: `spec.input_schema(**raw_args)` — a
  `ValidationError` is caught and returned as `{"error": ...}`, never
  propagated as a crash.
- **Call budget**: `MAX_TOOL_CALLS_PER_INVESTIGATION = 12` — the
  `(12+1)`th call raises `ToolCallBudgetExceeded`.
- **Repeat-call throttling**: `MAX_REPEATED_IDENTICAL_CALLS = 2` — a
  third identical `(tool, args)` call is refused with an explicit error
  rather than silently executed again (guards against an LLM stuck
  re-issuing the same call).
- **Execution failure isolation**: any exception raised by the
  underlying tool function is caught, logged in the call log
  (`ok=False`, `error=...`), and returned as `{"error": ...}` — the
  investigation continues rather than crashing.

Proven by `tests/unit/test_tool_schemas_and_authorization.py` (11 tests)
and exercised end-to-end by
`tests/integration/test_agent_investigation_pipeline.py::test_tool_call_budget_never_exceeded_for_a_single_investigation`.
