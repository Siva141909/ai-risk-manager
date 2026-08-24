# Frontend Architecture — Phase 5B.5/5B.7

## 1. Stack, and why each piece is there

No frontend existed before this phase (`frontend/` held only a
`.gitkeep`), so this is a from-scratch, minimal choice — not a
migration of something pre-existing.

| Choice | Why | Why not something heavier |
|---|---|---|
| Vite + React + TypeScript | Fast dev server, typed API contracts (catches a field-name typo against `docs/API.md` at compile time, not in a demo) | Next.js/Remix add server-rendering/routing machinery this API-driven SPA doesn't need |
| `react-router-dom` | 5 real routes (§3), a case detail sub-route structure | none simpler that still handles nested case routes |
| `@tanstack/react-query` | Directly implements Phase 5B.17's performance requirements: automatic request de-duplication (two components requesting the same case can't fire two fetches), built-in loading/error/success states per query (matches the state model in `docs/FRONTEND_UX.md` §5 exactly), and caching that prevents an accidental duplicate `POST /investigate` from re-hitting a live LLM (on top of the backend's own cache) | Redux/MobX would add global-state machinery this app doesn't need — there is no client-only state of consequence besides filters and in-flight guards |
| Hand-built SVG graph renderer (`components/graph/`) | The relationship model (typed edges: SHARED_DEVICE/SHARED_IP/SHARED_BANK_ACCOUNT, a center node, bounded neighbor counts) is simple and star-shaped per case — a generic charting library (Chart.js/Recharts) cannot express typed relationship edges at all, and a full graph-layout library (Cytoscape/d3-force) is unbounded machinery for what is, per case, at most a few dozen nodes in a fixed radial arrangement. Matches the explicit instruction: "do not use a generic chart library if it cannot represent the relationship model clearly," read together with "do not introduce unnecessary frameworks" | Cytoscape.js, d3-force, react-flow — all real options, all more general-purpose than this bounded, typed, small-N use case needs |
| Vitest + React Testing Library | Vite-native test runner, no separate config toolchain; RTL tests user-visible behavior (what Phase 5B.15 asks for), not implementation details | Playwright is used separately for *visual* validation (§6 of this doc / `docs/DEMO_FLOW.md`), a different concern from component tests |
| Plain CSS with custom properties (`styles/tokens.css`) | Every token in `docs/DESIGN_SYSTEM.md` is a CSS custom property — no CSS-in-JS runtime, no Tailwind config to keep in sync with the design doc separately | A utility framework would let token values drift from the design doc into ad hoc class combinations; a single tokens file is the actual source of truth either way, so skipping the extra layer avoids a second place values could disagree |

No authentication library, no state-persistence library, no
deployment tooling — none needed per the phase's own stop conditions.

## 2. Directory structure

```
frontend/
├── index.html
├── vite.config.ts
├── package.json
├── src/
│   ├── main.tsx
│   ├── app/
│   │   └── App.tsx              # router + React Query provider + top nav shell
│   ├── types/
│   │   └── api.ts                 # 1:1 TypeScript mirror of src/api/schemas.py — see §4
│   ├── services/
│   │   └── apiClient.ts            # typed fetch wrapper, one function per endpoint
│   ├── hooks/
│   │   ├── useCases.ts              # React Query hooks: list/detail/graph/investigation/investigate
│   │   └── useInvestigationEnrichment.ts  # bounded per-row cache-only enrichment, docs/FRONTEND_UX.md §3
│   ├── pages/
│   │   ├── RiskOverviewPage.tsx
│   │   ├── CaseQueuePage.tsx
│   │   ├── CaseInvestigationPage.tsx
│   │   ├── GraphExplorerPage.tsx
│   │   └── InvestigationReportPage.tsx
│   ├── components/
│   │   ├── layout/     # TopNav, PageShell
│   │   ├── risk/         # RiskTierBadge, GraphFlagBadge, StatTile
│   │   ├── cases/          # CaseTable, FilterBar, CaseStatusBadge
│   │   ├── investigation/    # AiInvestigationPanel, HumanReviewPanel, RecommendationBadge
│   │   ├── graph/               # CaseGraph (SVG renderer), GraphLegend
│   │   ├── evidence/              # EvidenceItemCard, EvidenceList
│   │   └── common/                  # Button, Badge, Card, Table, EmptyState, ErrorState, Skeleton, Tooltip
│   ├── styles/
│   │   └── tokens.css                 # every token from docs/DESIGN_SYSTEM.md, nothing else defines a color/size
│   └── utils/
│       └── format.ts                    # shared formatting: score→%, dt→relative label, evidence grouping
└── tests/
    └── (co-located *.test.tsx next to each component/page)
```

## 3. Routes

| Path | Page | API calls on load |
|---|---|---|
| `/` | RiskOverviewPage | ~6 bounded `GET /api/v1/cases?...&limit=1` (docs/FRONTEND_UX.md §3) |
| `/cases` | CaseQueuePage | `GET /api/v1/cases?<filters>` + bounded per-investigated-row enrichment |
| `/cases/:caseId` | CaseInvestigationPage | `GET /cases/{id}`, `GET /cases/{id}/graph`, `GET /cases/{id}/investigation` (404-tolerant) |
| `/cases/:caseId/graph` | GraphExplorerPage | `GET /cases/{id}` (for header context) + `GET /cases/{id}/graph` |
| `/cases/:caseId/report` | InvestigationReportPage | `GET /cases/{id}`, `GET /cases/{id}/investigation` |

`POST /api/v1/cases/investigate` is only ever called from one place —
the "Start Investigation" action on `CaseInvestigationPage` — never on
page load, never speculatively, matching Phase 5B.17's "avoid repeated
Claude investigations."

## 4. Typed API client — the frontend/backend boundary

`src/types/api.ts` is a hand-written, field-for-field TypeScript mirror
of every Pydantic schema in `src/api/schemas.py` — **snake_case
preserved exactly** (no camelCase transform layer). This is a
deliberate choice: a transform layer is one more place a field could be
silently renamed or dropped without either side noticing; keeping the
wire shape identical to the documented contract means `docs/API.md` and
`src/types/api.ts` can be diffed against each other directly, and a
backend field addition/removal is a visible, single-file change here.

`src/services/apiClient.ts` exports one typed function per endpoint
(`listCases`, `getCase`, `getCaseGraph`, `getCaseInvestigation`,
`investigate`, `getHealth`) — no generic "call any endpoint" escape
hatch, so there is no code path by which the frontend could call
something outside the documented contract. Every function's return type
is one of the `src/types/api.ts` interfaces; there is no `any` in this
file.

**What the frontend structurally cannot do** (mirrors Phase 5A.8's
server-side guarantees with a client-side one): `apiClient.ts` has no
SQL, no filesystem access, no import from `src/` (the Python package) —
this is a fully separate Node/TypeScript project with its own
`package.json`, so there is no module resolution path into the Python
domain code even by accident. `investigate()`'s request type
(`InvestigateRequest`) has no `ml_risk_tier`/score-like field at all —
not just rejected server-side (`docs/BACKEND_ARCHITECTURE.md` §7), the
TypeScript type doesn't expose one to set in the first place.

## 5. Data flow / state

Server state (everything from the API) lives in React Query's cache,
keyed by `["case", caseId]`, `["cases", filters]`,
`["investigation", caseId]`, etc. — no server data is duplicated into
component-local `useState`. Client-only state (filter selections,
in-flight "investigation running" guard, graph pan/zoom transform) is
plain component state — there is no client state worth lifting into a
global store.

**In-flight guard for `POST /investigate`:** `useInvestigate` (in
`hooks/useCases.ts`) exposes `isRunning`, derived from React Query's
mutation status, and `CaseInvestigationPage` disables "Start
Investigation" whenever `isRunning` is true — the only place a double
request could originate (a second browser tab/window hitting the same
case concurrently) is still safe because the *backend's* own cache
(Phase 5A.7) makes a second concurrent request either wait, hit cache,
or run once more — the frontend guard is a UX affordance, not the
correctness boundary; the correctness boundary is already server-side.

## 6. Visual validation workflow (Phase 5B.4/5B.14, no-Figma path)

Since there is no Figma file to diff against, "Figma ↔ React visual
comparison" (Phase 5B.6) is replaced with:

1. Run backend (`RISK_MANAGER_LLM_BACKEND=stub`) + frontend dev server.
2. Use Playwright (via the project's `webapp-testing` skill) to open
   every route, including each of the 5 demo cases
   (`src/api/demo_data.py`), and capture a full-page screenshot.
3. Inspect each screenshot directly (this document's author reads every
   one, not just checks the app "builds") for: text clipping, spacing/
   alignment errors, overflow, unreadable graph layouts, missing loading/
   empty/error states, and responsive breakage at 1440/1280/1024px.
4. Fix what's found; re-screenshot; repeat until clean.

Results of this pass are recorded in `docs/DEMO_FLOW.md`, not silently
assumed — "the application builds" is never treated as equivalent to
"visually validated" (explicit instruction).

## 7. Performance guardrails (Phase 5B.17)

- Case Queue never fetches more than one page (`limit≤200`) at a time;
  no "load everything" mode.
- Graph rendering is bounded by what `GET /cases/{id}/graph` already
  returns (itself bounded server-side, `docs/TOOL_CONTRACTS.md`'s
  `max_results` on `get_graph_neighbors`) — the frontend never
  paginates or fetches additional neighbor pages beyond one call.
- No polling anywhere — investigation status is a single synchronous
  request/response (`docs/BACKEND_ARCHITECTURE.md` §4's documented
  sync-by-design decision), so there is nothing to poll.
- React Query's default `staleTime`/cache behavior prevents an
  accidental re-fetch storm from route re-renders; case/investigation
  queries are configured with a non-zero `staleTime` since the
  underlying dataset is frozen for the lifetime of the server process.

## 8. Testing strategy (Phase 5B.15)

Component/page tests (Vitest + RTL, `apiClient` mocked at the module
boundary — never mocking away entire page behavior, per the explicit
instruction): rendering, loading/error/empty states, risk-tier badge
rendering per tier, case-list filtering, graph node/edge rendering from
a fixed fixture `CaseGraphResponse`, AI investigation panel rendering
(summary/evidence/conflicts/legitimate-explanations/policy/
recommendation), evidence list rendering + deterministic-vs-AI visual
distinction, human-review panel's `human_approval_required` display and
disabled-action state, and demo-case selection. Full list and file
mapping: `frontend/tests/` (co-located `*.test.tsx`).

Visual/E2E validation (Playwright, §6) is a separate, manual-inspection
pass — not part of the automated `npm test` suite, since its output is
images a person reads, not pass/fail assertions.
