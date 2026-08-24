# Demo Flow — Phase 5B.19

**Status placeholder:** this document is written before implementation
(per the Phase 5B.18 doc-first requirement) and updated at the end of
Phase 5B with actual visual-validation results and the real-Claude
end-to-end confirmation — see §4/§5, filled in after implementation.

## 1. Running the demo

```bash
# terminal 1 — backend, real Claude
RISK_MANAGER_LLM_BACKEND=claude_agent_sdk uvicorn src.api.main:app --reload

# terminal 2 — frontend
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173`. For a fast/offline rehearsal, omit
`RISK_MANAGER_LLM_BACKEND` (defaults to `stub`) — every stub-generated
investigation is prefixed `"STUB TEST:"` in its text fields, so a
rehearsal run is never confusable with a real one.

## 2. The 5 demo cases

From `src/api/demo_data.py` — real, repository-verified transactions,
not fabricated:

| Label | Case ID | Shape |
|---|---|---|
| Strong coordinated ring | `CASE-3410549` | 11-member community, shared device + IP |
| Legitimate household | `CASE-3452855` | 5-member community, shared IP only, LOW tier |
| ML-low / graph-high | `CASE-3457202` | 4-member community, shared bank account, MEDIUM tier |
| Conflicting evidence | `CASE-3416834` | 3-member community, shared device, MEDIUM tier |
| Missing data | `CASE-3400406` | singleton, no graph evidence, LOW tier |

## 3. The primary demo script (15 steps, per the authorization message)

1. **Open Risk Overview** (`/`) — orient on tier counts, graph-flagged
   count, investigated/pending counts, recent critical cases.
2. **Navigate to Case Queue** (`/cases`) — scan the list, point out the
   ML Risk and Graph Flag columns as two independent signals.
3. **Select the ML-low / graph-high case** (`CASE-3457202`) — search or
   filter to find it, click through to Case Investigation.
4. **Show ML score vs. graph coordination** — Risk Summary shows
   `ml_risk_score≈0.011` (LOW-looking on its own) next to a graph-
   flagged indicator; narrate: "the model alone would not have raised
   this."
5. **Explain why graph caught something ML did not** — "Why This Case
   Was Flagged" section, graph column: 4-member community sharing one
   bank account, rarity score near 1.0.
6. **Open the graph** — inline subgraph preview → "Open Graph Explorer."
7. **Explore shared device / IP / bank account** — this case's graph
   has one relationship type (SHARED_BANK_ACCOUNT); use the Strong
   Ring case (`CASE-3410549`) as the multi-relationship-type example
   if the narration wants to show more than one edge color.
8. **Start investigation** — "Start Investigation" button, real Claude
   backend, ~20-60s (per §5's measured latency).
9. **Show the agent investigation process** — the "Investigating…"
   panel state while it runs (no fake progress/streaming, per
   `docs/FRONTEND_UX.md` §5).
10. **Show evidence / legitimate explanations / conflicts / policy /
    recommendation** — AI Investigation section, each subsection
    labeled and visually distinct from deterministic evidence
    (`docs/DESIGN_SYSTEM.md` §7).
11. **Show policy evidence** — policy findings render with their
    `[POLICY:doc#section]` citations.
12. **Show recommendation** — Human Review panel.
13. **Show "HUMAN APPROVAL REQUIRED"** — the badge is always present
    (`human_approval_required_for_action` is hardcoded `True` by the
    frozen agent, `docs/SAFETY_MODEL.md` §1), and the UI-only action
    buttons are visibly disabled with their "not yet backend-supported"
    tooltip (`docs/FRONTEND_UX.md` §4) — narrate this as an honest
    product boundary, not a bug.
14. **Inspect evidence details** — expand an `EvidenceItem`, point out
    `source_tool`/`is_retrospective`.
15. **Return to Case Queue** — the case now shows an "Investigated"
    badge and (bounded enrichment) its recommendation inline.

## 4. Visual validation results

60 full-page screenshots captured via Playwright at 1440/1280/1024px
(`frontend/tests/visual_validation.py`) covering Risk Overview, Case
Queue (default and filtered), all 5 demo cases' Case Investigation /
Graph Explorer / Investigation Report pages, and a not-found error
state. Every screenshot was read and inspected directly, not just
generated. Issues found and fixed as a direct result:

1. **Backend defect — `investigation_status` filter reported the wrong
   total and could silently miss real rows.** The filter was applied
   *after* pagination truncation (`CaseService.list_cases`), so
   `GET /cases?investigation_status=investigated&limit=1` returned
   `total=177162` (the whole dataset) instead of the true count.
   Overview's "Investigated" tile visibly showed this wrong number.
   Fixed in `src/api/repository.py`/`src/api/cache.py`/`src/api/services.py`
   — filtering now happens on the full dataset before `total`/pagination
   are computed, with a regression test added
   (`tests/api/test_cases_listing.py::test_investigation_status_filter_is_correct_before_pagination`).
   This is an API-layer (Phase 5A) fix, not a change to ML/graph/agent
   behavior.
2. **Pagination display bug** — "Showing 0–25 of N" should read
   "Showing 1–25" (operator-precedence bug: `filters.offset ?? 0 + 1`
   parsed as `filters.offset ?? (0 + 1)`, not `(filters.offset ?? 0) + 1`).
   Fixed in `CaseQueuePage.tsx`.
3. **Overlapping graph edges hid a color** — when a neighbor shares more
   than one relationship type with the center (`multi_attribute_overlap`,
   the highest-signal case), two edges connect the exact same node pair;
   drawn as straight lines they perfectly overlapped and the
   later-drawn color completely hid the earlier one, defeating the
   point of typed edge colors on exactly the case that matters most.
   Fixed in `CaseGraph.tsx` by bowing same-pair edges with a small
   perpendicular offset so every relationship type stays visible;
   verified visually on the strong-ring demo case (`CASE-3410549`).
4. **Edge color distinctness** — `SHARED_IP` originally reused
   `--color-accent`, which read too close to `--color-graph-text`
   (`SHARED_DEVICE`) at thin edge-stroke widths. Replaced with a new
   token, `--color-graph-ip-text` (cyan), documented in
   `docs/DESIGN_SYSTEM.md` §1/§8.
5. **Duplicate empty-state copy** — the Investigation Timeline and AI
   Investigation sections both said "This case has not been
   investigated yet" verbatim (confusing when a page shows the same
   sentence twice); Timeline's copy was made section-specific
   ("Timeline not yet available…").
6. **Error-state latency** — `useCase`/`useCaseGraph` inherited a
   default retry that retried even a 404 once before settling into the
   error state, delaying "Case not found" by a retry round-trip.
   Fixed with a shared retry predicate (`shouldRetryQuery`,
   `apiClient.ts`) that never retries a 4xx.

No text clipping, overflow, or responsive breakage was found at
1440/1280/1024px after the above fixes; the 2-column Case Investigation
layout collapses to 1 column at ≤1280px as designed.

## 5. Real-Claude end-to-end confirmation

Ran against a backend started with `RISK_MANAGER_LLM_BACKEND=claude_agent_sdk`
(fresh process, empty cache). A Playwright script
(`frontend/tests/e2e_real_claude_demo.py`) navigated to
`/cases/CASE-3457202` (ML-low/graph-high) in an actual headless
browser, located the real "Start Investigation" button by its
accessible role, and clicked it — not a direct API call.

**Server-side proof** (`/tmp/backend_claude.log`, one structured log line):

```json
{"message": "investigation_completed", "case_id": "CASE-3457202",
 "llm_backend": "claude_agent_sdk", "cache_hit": false,
 "agent_duration_ms": 44304, "validation_status": "passed"}
```

44.3 seconds — consistent with Phase 4's measured 20-60s range for
real Claude investigations, confirming this was a genuine live call,
not a cache hit or stub.

**Browser-side proof:** three screenshots taken during the same run —
before the click ("Not investigated" badge, no report), during
("Investigating…" panel with the spinner and the honest "typically
take 20-60 seconds" copy, confirmed actually visible via
`wait_for_selector`), and after (full real report: multi-paragraph
reasoning in Summary/Graph Findings/Behavioral Findings, two real
`legitimate_explanations`, `conflicting_evidence=true` with a specific
`conflict_description`, three real `[POLICY:...]` citations, 8 real
`EvidenceItem`s each tied to a real `source_tool`,
`recommendation=investigate_further`, confidence 45%, and
"HUMAN APPROVAL REQUIRED" with all four human-review actions visibly
disabled). No `"STUB TEST"` string appears anywhere in the rendered
page — confirmed programmatically (`"STUB TEST" in body_text` = `False`).

This confirms the complete chain end-to-end, each link with direct
evidence rather than an assumption:
**Frontend (browser click)** → **FastAPI** (`POST /api/v1/cases/investigate`,
`src/api/routers/cases.py`) → **frozen case/pipeline**
(`CaseRepository`/`build_case`, unmodified since Phase 5A) →
**LangGraph** (`run_investigation`, unmodified since Phase 4) →
**Claude Agent SDK** (`ClaudeAgentSDKClient`, unmodified since Phase 4)
→ **InvestigationReport** (validated, `validation_status="passed"`) →
**Frontend** (rendered in `AiInvestigationPanel`/`HumanReviewPanel`,
correctly labeled, no stub markers).
