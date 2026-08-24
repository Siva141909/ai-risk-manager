# Frontend UX Architecture — Phase 5B.1

**Figma note:** no Figma MCP/plugin tool is available in this Claude
Code environment (verified, not assumed). Per the technical lead's
explicit direction, the "design in Figma first" step is replaced with:
`DESIGN SPECIFICATION → HIGH-FIDELITY FRONTEND IMPLEMENTATION →
VISUAL VALIDATION → REAL BACKEND INTEGRATION`. This document and
`docs/DESIGN_SYSTEM.md` are the design source of truth that a Figma
file would otherwise have been; `docs/FRONTEND_ARCHITECTURE.md` and
`docs/DEMO_FLOW.md` complete the set (Phase 5B.18).

## 0. Ground truth: what the API can actually serve

Every field named anywhere in this document exists today in
`docs/API.md` / `src/api/schemas.py`. Nothing below is invented. Fields
explicitly **not** available, and how each screen handles that gap
honestly, are called out inline as **API GAP** notes rather than
silently faked.

Available: `CaseSummaryResponse` (case_id, transaction_id,
transaction_dt, ml_risk_score, ml_risk_tier, graph_flagged,
has_investigation), `CaseDetailResponse` (+ customer_proxy_id,
customer_proxy_confidence, graph_lookup_keys, graph_evidence),
`GraphEvidenceResponse` (community_id, community_size,
n_shared_devices, n_shared_ips, n_shared_bank_accounts,
multi_attribute_overlap, relationship_rarity_score,
temporal_concentration_hours, detected_relationship_types, narrative),
`CaseGraphResponse` (nodes, edges), `InvestigationResponse` /
`InvestigationReportSchema` (summary, trigger, risk_tier,
graph_findings, behavioral_findings, legitimate_explanations,
conflicting_evidence, conflict_description, policy_findings,
recommendation, requires_human_review,
human_approval_required_for_action, confidence, evidence[],
retrospective_evidence_used, investigation_complete,
validation_status), `ProcessingMetadata`.

**Not available anywhere in the API, by design (Phase 4/5A frozen
boundaries):** `CaseGroundTruth` fields (original_isFraud,
synthetic_ring_id/abuse_type/ring_role, legitimate_cluster_id/type,
synthetic_entity_label), a time-series/trend/history endpoint, a
server-side "coordination type" categorical field on the list endpoint,
a server-side sort-order parameter, and a per-tier/per-status aggregate
endpoint (counts are derived client-side from `total` on filtered list
calls — see §3).

## 1. Navigation structure

```
App shell
├── Risk Overview        /                    (operational summary)
├── Case Queue            /cases                (primary work list)
│   └── Case Investigation  /cases/:caseId          (HERO screen)
│       ├── Transaction Detail (in-page section, §Screen 4 scope folded in)
│       ├── Graph Explorer       /cases/:caseId/graph  (focused, full-screen graph view)
│       └── Investigation Report /cases/:caseId/report (report-style read view)
└── Demo (dev tooling only, not a product nav item — see docs/DEMO_FLOW.md)
```

Top nav: **Overview**, **Case Queue** — two items, not more. Case
Investigation/Graph Explorer/Investigation Report are reached by
drilling into a case, never top-level nav destinations (the product
story is "triage → investigate," not a flat set of unrelated pages).
"Transaction Detail" (Screen 4 in the original spec) is **not a
separate route** — its content (amount, product code, behavioral
signals, related entities) is a section within Case Investigation,
since every field it would show is already part of the same
`CaseDetailResponse`/`InvestigationReport` fetch; a separate page would
just be a second view of the same data behind an extra click, adding
navigation cost with no new information. This is a deliberate scope
consolidation, stated here rather than silently dropped.

## 2. Primary user workflow

```
Risk Overview (orientation: what needs attention right now)
   → Case Queue (scan, filter, pick a case)
      → Case Investigation (understand WHY it was flagged)
         → [optional] start/view AI investigation (WHY does it deserve attention)
         → [optional] Graph Explorer (explore the subgraph directly)
         → [optional] Investigation Report (read/share view)
      → back to Case Queue (next case)
```

Every screen answers exactly one of the four product-story questions
(from the authorization message): ML ("does this look risky?"), Graph
("is this coordinated?"), Agent ("why, with what evidence, what
legitimate explanation?"), Human ("do I approve?"). Case Investigation
is the only screen that must answer all four in one view — that's why
it's the hero screen and gets built first.

## 3. Information hierarchy per screen

### Risk Overview
1. Four tier tiles (LOW/MEDIUM/HIGH/CRITICAL counts) — each from one
   `GET /api/v1/cases?risk_tier=X&limit=1` call read for its `total`
   field (limit=1 keeps the payload trivial; `total` is exact
   regardless of limit).
2. Graph-flagged count tile — one `GET ?graph_flagged=true&limit=1` call.
3. Investigated / not-investigated counts — one
   `GET ?investigation_status=investigated&limit=1` call
   (`investigation_status=not_investigated` count = grand total − this).
4. **API GAP — "cases awaiting human review":** no server-side filter
   exists for `requires_human_review` (that field lives inside an
   `InvestigationReport`, not `CaseSummaryResponse`). Computed as a
   *bounded* enrichment: fetch the (small, demo-scale) set of already-
   investigated case reports via `GET /cases/{id}/investigation`
   (cache-only, never triggers a new agent run) and count
   `requires_human_review=true` among them. Documented in
   `docs/FRONTEND_ARCHITECTURE.md` as a pattern that needs a real
   backend aggregate before this scales past demo size.
5. Recent high-priority cases: one bounded `GET
   ?risk_tier=CRITICAL&limit=50` (or HIGH if CRITICAL is empty),
   sorted **client-side** by `transaction_dt` descending, top 5 shown.
   Labeled "Recent Critical Cases," not "recent" unqualified — the API
   has no sort-order parameter, so this is "most recent within the
   highest-priority tier already fetched," stated exactly as that.
6. **API GAP — trend information:** no time-series/history endpoint
   exists (this is a stateless read over a frozen dataset, not a live
   monitoring feed). Omitted entirely rather than fabricated — the spec
   itself says "where supported by backend data," and it isn't.
7. **API GAP — "coordination/ring summary" breakdown by ring type:**
   `CaseSummaryResponse` has no `detected_relationship_types` field, so
   only a single graph-flagged count is shown (§3.2 above), not a
   per-relationship-type breakdown. That detail exists only per-case
   (`GraphEvidenceResponse.detected_relationship_types`), shown on Case
   Investigation.

### Case Queue
Table columns, all backed by real `CaseSummaryResponse` fields:
Case ID, Time (transaction_dt), ML Risk (score + tier badge), Graph
Flag (yes/no badge), Investigation Status (has_investigation → Not
investigated / Investigated badge). Filters: risk tier, graph flagged,
investigation status, TransactionDT range (labeled honestly as
"transaction time range," not calendar dates — this dataset has no
wall-clock dates, `docs/API.md`).

**API GAP — "coordination type" column:** not shown as a queue column;
`CaseSummaryResponse` has no relationship-type field, and fetching it
per-row for every page would be an N+1 pattern this document explicitly
avoids (Phase 5B.17 performance guidance). The Graph Flag badge is the
queue-level coordination signal; the specific type is one click away on
Case Investigation.

**Bounded recommendation enrichment:** for rows where
`has_investigation=true` (typically a handful, not the whole page), the
queue additionally fetches the cached report
(`GET /cases/{id}/investigation`, cache-only) to show a compact
recommendation badge inline. This is bounded by how many rows on the
current page are already investigated — never proportional to the full
page size, never triggers a new agent run.

**API GAP — "confidence" and "recommended action" as list columns for
un-investigated cases:** both fields only exist post-investigation;
shown as "—" until then, exactly as available.

### Case Investigation (hero screen)
Section order, top to bottom (matches the authorization message
exactly): Header (case_id, status pill, transaction time) → Risk
Summary (ML score, ML tier, graph-coordination indicator, investigation
confidence if investigated) → Why This Case Was Flagged (ML signals
column + graph signals column, explicitly separated and labeled
"deterministic") → Network/Graph (embedded subgraph preview, "Open
Graph Explorer" for the full view) → Investigation Timeline (the
case's own known transaction history, once investigated — see §API
GAP below) → AI Investigation (labeled "AI INVESTIGATION," never
implies it set the risk tier — the risk tier shown in Risk Summary
always comes from `ml_risk_tier`, never from `investigation_report.risk_tier`,
even though the two are guaranteed equal by the frozen agent's own
validation) → Evidence (every `EvidenceItem`: id, source_tool, summary,
is_retrospective) → Human Review (recommendation,
`human_approval_required` badge, UI-only action buttons — §4).

**API GAP — "Investigation Timeline":** there is no dedicated
timeline/activity-log endpoint. The timeline section is populated from
`InvestigationReport.evidence` items whose `source_tool` is
`get_transaction_history` or `get_temporal_activity`, ordered as
returned — i.e., it is a *view* of evidence already fetched for the
investigation, not a new data source. Before an investigation has run,
this section is empty with a message explaining why (see §4 empty
states), not a fabricated placeholder timeline.

### Graph Explorer
Full-screen version of the same `CaseGraphResponse` (nodes/edges) the
Case Investigation page shows inline, with the interactions listed in
§Screen 5 of the authorization message (zoom, pan, select, inspect,
reset). No new data — a focused view of what `GET
/cases/{id}/graph` already returns.

### Investigation Report
Read-only, report-styled rendering of the same
`InvestigationResponse`/`InvestigationReport` Case Investigation already
has — every section the authorization message lists (Executive
Summary=`summary`, Risk Context=ml score/tier + `trigger`, Graph
Findings=`graph_findings`, Behavioral Findings=`behavioral_findings`,
Legitimate Explanations, Conflicting Evidence, Policy Findings,
Recommendation, Confidence, Evidence, human approval requirement) maps
1:1 onto fields already fetched — no new API call beyond what Case
Investigation already made.

## 4. Interaction model

**Starting an investigation:** a single "Start Investigation" button on
Case Investigation, disabled while an investigation is already running
for that case (client-side in-flight guard, prevents a double-click
firing two `POST /investigate` calls for the same case — Phase
5B.17's "avoid repeated Claude investigations"). Once
`has_investigation=true` (from the initial case fetch or a prior run in
this session), the button reads "View Investigation" / "Re-run" is
**not** offered as a casual action — re-investigating a case that
already has a cached report is an explicit, secondary action
(small text link, not a primary button), since the backend itself
treats a repeat request as a free cache hit rather than a new LLM call,
but presenting "re-run" prominently would invite users to think that's
normal/cheap when a cache miss (different backend/version) would not be.

**Human review actions (§Screen 3 "Human Review"):** "Approve
recommendation," "Request further investigation," "Mark as legitimate,"
"Escalate" are **UI-only** — the Phase 5A API has no endpoint to
persist a human decision (no `PATCH /cases/{id}`, no case-status
write path exists). Per the authorization message's own instruction
("If the backend does not support an action, do not fake it"), these
are rendered as visibly **disabled** buttons with a tooltip/label
stating "Not yet supported by the backend — Phase 5B UI-only" rather
than either hidden entirely (which would misrepresent the intended
product shape) or wired to a fake success state (which would misrepresent
what the system actually does). This is the literal, honest reading of
"UI actions ... should be UI-only unless the backend explicitly supports
them" combined with "do not invent backend capabilities."

## 5. Loading / empty / error / investigation states

| State | Where | Presentation |
|---|---|---|
| Loading (list/detail fetch) | Overview, Queue, Case Investigation | Skeleton rows/cards matching final layout shape, never a bare spinner-only screen for table content |
| Loading (investigation running) | Case Investigation | A distinct "Investigating…" panel state in the AI Investigation section — not a generic spinner; states it may take up to ~60s (matches measured real-Claude latency, `docs/AGENT_EVALUATION.md`), button disabled, no fake progress bar/streaming (Phase 5B.10: "do not fake streaming if the backend doesn't support it" — this backend returns one atomic result, no incremental events) |
| Empty (queue, no cases match filters) | Case Queue | "No cases match these filters" + a "Clear filters" action, never an empty table with no explanation |
| Empty (no graph evidence) | Case Investigation, Graph Explorer | "No shared infrastructure detected for this customer" — a real, valid state (most cases), not an error |
| Empty (no investigation yet) | Case Investigation, Investigation Report, Timeline | "This case has not been investigated yet" + the Start Investigation action, never a blank section |
| Error (case not found, 404) | Case Investigation | "Case not found" with a link back to the Queue |
| Error (malformed request, 400/422) | any form/filter | Inline field-level message from the API's `message`, never a raw stack trace (the API itself never returns one — `docs/API.md`) |
| Error (LLM unavailable, 503) | Case Investigation | "The investigation service is temporarily unavailable — try again shortly," distinct from a validation failure |
| Error (agent execution failed, 500) | Case Investigation | Generic "Investigation failed — try again," no internal exception text (the API never sends one) |
| Error (timeout, 504) | Case Investigation | "Investigation timed out" — distinct message, since this is a "still might work, took too long" case, not a hard failure |
| Fail-safe result (`validation_status="failed_human_review"`) | Case Investigation, AI Investigation section | **Not an error state at all** — rendered as a normal completed investigation whose recommendation is `escalate_to_human_analyst` and whose evidence list is empty; the UI must not special-case this into an error banner, since the backend itself treats it as a valid, if minimal, result (`docs/BACKEND_ARCHITECTURE.md` §6) |

## 6. What every screen must NOT do (Phase 5B.16 restated per-screen)

No screen ever renders `CaseGroundTruth` fields, a synthetic ring/
cluster ID, or any field not present in `docs/API.md`'s schemas. Where
the underlying dataset is synthetic (this entire benchmark is), that is
stated once, contextually, on Risk Overview and Case Investigation
("Data: synthetic benchmark transactions — see docs/CASE_MODEL.md"),
never per-field speculation about what's "real."
