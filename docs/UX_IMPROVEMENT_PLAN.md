# UX Improvement Plan — Phase 6, Part 10

Findings from a fresh-install, zero-pre-seeded-investigations audit
(`/tmp/phase6_fresh_overview.png`, `/tmp/phase6_fresh_queue.png` —
real Playwright screenshots of a genuinely fresh backend process, not
Phase 5B's screenshots which had 5 cases pre-investigated). Per Part 15's
change policy, only P0/P1 items are implemented; P2/P3 are documented
and left alone.

---

## Issue 1 (P1): The product's core differentiator is invisible on the first screen a judge sees

**Severity:** P1 (materially hurts demo quality — arguably borders P0,
since a judge who only skims Overview could reasonably conclude "this
is a plain ML risk scorer" and miss the graph/coordination capability
entirely).

**Current behavior:** On a fresh install (0 investigated cases, exactly
what a judge cloning the repo would see), Risk Overview's "Recent
Critical Cases" table shows 5 rows — **every single one has "No Graph
Evidence."** This is because graph-flagged cases are rare by design
(182 of 177,162 servable cases, ≈0.1% — coordinated abuse should be
rare) and the table is populated from the CRITICAL ML tier, which has
no correlation with graph flagging (`docs/ML_GRAPH_ABLATION.md` §4/§6 —
quadrant D, ML-high AND graph-high, is empirically empty in this
benchmark). The Case Queue's default (unfiltered) view has the same
property — the first 25 rows by transaction order are, again, ~100%
"No Graph Evidence," for the same prevalence reason.

**Why it hurts the judge experience:** Per the judge-question set (Q90:
"Can a judge see why ML missed something?"), the honest answer right
now is "not from the two primary nav screens in their default state" —
a judge would need to already know to apply the "Graph flagged" filter,
or click through to `/demo`, before ever seeing the feature that is
this project's actual claimed differentiator (`docs/RAZORPAY_TRACK_02_COMPLIANCE.md`
§2: "coordinated payment fraud / abuse-ring detection," not generic ML
scoring).

**Proposed change:** Add a second table to Risk Overview, **"Recent
Coordination-Flagged Cases,"** sourced from the graph-flagged query the
page already makes for the "Coordination detection" tile count (today
that query only reads `.total` and discards the rows — bump its
`limit` and reuse the `items` it already fetches, no new API call
shape, no backend change). Placed directly below "Cases by risk tier,"
above "Recent Critical Cases," so it's the second thing a judge sees,
not something they have to filter for.

**Expected benefit:** The very first screen now visibly answers "does
the graph feature actually find anything," instead of silently
depending on the judge already knowing to look for it.

**Risk:** Low. Additive UI only — no change to what data means, no
change to any filter default, no change to the Case Queue's honest
(sparse) default view (which correctly reflects real coordination
prevalence and should not be artificially reordered to look busier than
it is).

**Files affected:** `frontend/src/hooks/useOverviewStats.ts` (fetch
rows, not just count, for the graph-flagged query), `frontend/src/pages/RiskOverviewPage.tsx`
(render the new table).

---

## Issue 2 (P1): Large numbers are unformatted, reading as unpolished

**Severity:** P1 (Q98: "Does the product look like a real
risk-operations system?" — a real ops console formats `117,411`, not
`117411`).

**Current behavior:** `StatTile` renders raw numbers with no thousands
separator (`55648`, `117411`, `2018`, `2085`, `177162`).

**Proposed change:** Add `toLocaleString()` formatting at the point
these values are passed to `StatTile`/table cells.

**Expected benefit:** Small, immediate polish improvement with zero
behavioral risk.

**Risk:** None — pure display formatting, no value changes.

**Files affected:** `frontend/src/pages/RiskOverviewPage.tsx`,
`frontend/src/pages/CaseQueuePage.tsx` (the "Showing X–Y of Z" line).

---

## Issues found and deliberately NOT changed this phase

| Issue | Severity | Why left alone |
|---|---|---|
| `prefers-reduced-motion` not respected by the skeleton-pulse and investigating-spinner CSS animations | P2 | Accessibility nicety, doesn't block understanding or cause confusion; a real fix (media-query override) is safe but not urgent enough to justify touching CSS beyond the two P1 items above in one pass — noted for a future pass |
| "Start Investigation" button appears in both the Risk Summary rail and the AI Investigation panel's empty state | P3 | Each instance is contextually justified (one is always visible in the rail, one appears only in the empty state a judge is already looking at) — not confusing, arguably reinforces the action |
| Case Queue's default view has no graph/investigated signal (same root cause as Issue 1) | P2 (secondary to Issue 1) | Deliberately NOT fixed by reordering the Queue's default sort — a real analyst's queue should show cases in a neutral, honest order, not be gamed to look more "interesting" for a demo; Issue 1's Overview fix addresses the judge-visibility problem without compromising the Queue's honesty |
| No `frontend/package.json` `engines` field | P3 | Documented instead (`docs/REPRODUCIBILITY_AUDIT.md` §5/§6) — safer than constraining `npm install` behavior |

---

## Implementation order

1. Issue 1 (Overview coordination table)
2. Issue 2 (number formatting)
3. Run frontend tests, run build, visually re-validate both affected
   screens, confirm backend integration still works end-to-end.

No backend, ML, graph, agent, threshold, or RAG code is touched by
either change.
