# Design System — Phase 5B.4

Source of truth for every token and component `frontend/src/` implements
against. Light theme only (an analyst workstation console, not a
consumer app — restrained, high information density, not decorative).
Values here are final — the React implementation reads them from
`frontend/src/styles/tokens.css`, never hardcodes a hex value in a
component.

**Fonts:** system font stack only (`-apple-system, "Segoe UI", Roboto,
"Helvetica Neue", Arial, sans-serif`; monospace stack for IDs/codes:
`ui-monospace, "SF Mono", "Cascadia Code", Menlo, monospace`) — no
external font loading, so the app never has a network dependency (or a
flash-of-unstyled-text) just to render, and stays fast on an analyst's
workstation regardless of network conditions.

**Brand note:** deliberately distinct from Razorpay's own brand blue
(`#3395FF`-family) — this is an original product interface for the
competition, not a Razorpay UI clone (per the explicit instruction).

## 1. Color tokens

```css
/* Neutrals */
--color-bg: #F6F7F9;              /* page background */
--color-surface: #FFFFFF;          /* cards, table, panels */
--color-surface-sunken: #FAFBFC;    /* nested/secondary surface, e.g. table header */
--color-border: #E3E6EB;
--color-border-strong: #C7CCD6;
--color-text-primary: #12151C;
--color-text-secondary: #565D6B;
--color-text-tertiary: #8A909C;
--color-text-inverse: #FFFFFF;

/* Brand / accent */
--color-accent: #3D4EEA;            /* primary actions, links, focus */
--color-accent-hover: #3140C4;
--color-accent-subtle: #EEF0FD;      /* accent-tinted backgrounds */

/* Risk tiers — each pairs a bg/text/border triplet, never used alone (icon+label always accompany) */
--color-risk-low-bg: #ECFDF5;    --color-risk-low-text: #047857;    --color-risk-low-border: #A7F3D0;
--color-risk-medium-bg: #FFFBEB; --color-risk-medium-text: #B45309; --color-risk-medium-border: #FDE68A;
--color-risk-high-bg: #FFF4ED;   --color-risk-high-text: #C2410C;   --color-risk-high-border: #FDBA8C;
--color-risk-critical-bg: #FEF2F2; --color-risk-critical-text: #B91C1C; --color-risk-critical-border: #FCA5A5;

/* Graph / coordination — a distinct hue from risk tiers, since it's a different signal axis */
--color-graph-bg: #F5F3FF; --color-graph-text: #6D28D9; --color-graph-border: #DDD6FE;
--color-graph-ip-text: #0891B2; /* SHARED_IP edge color — see §8; kept far in hue from --color-graph-text */

/* Semantic status (non-risk) */
--color-success-bg: #ECFDF5; --color-success-text: #047857;
--color-warning-bg: #FFFBEB; --color-warning-text: #B45309;
--color-danger-bg: #FEF2F2;  --color-danger-text: #B91C1C;
--color-info-bg: #EFF6FF;    --color-info-text: #1D4ED8;

/* AI-generated content — a visually distinct family from deterministic evidence,
   dashed borders reinforce "interpreted, not measured" (see §7) */
--color-ai-bg: #F8F7FF; --color-ai-text: #5B3DEA; --color-ai-border: #D9D3FB;
```

Contrast checked against WCAG AA for normal text (all `*-text` tokens
on their paired `*-bg` and on `--color-surface` exceed 4.5:1).

## 2. Typography scale

| Token | Size / line-height | Weight | Use |
|---|---|---|---|
| `--text-display` | 28px / 1.25 | 650 | Page title (e.g. "Case CASE-3457202") |
| `--text-h1` | 20px / 1.3 | 600 | Section header (e.g. "AI Investigation") |
| `--text-h2` | 16px / 1.4 | 600 | Subsection header (e.g. "Evidence") |
| `--text-body` | 14px / 1.55 | 400 | Default body text |
| `--text-body-strong` | 14px / 1.55 | 600 | Emphasized inline text, table primary cell |
| `--text-small` | 12.5px / 1.4 | 500 | Meta text, labels, table secondary cell |
| `--text-mono` | 12.5px / 1.4 | 500 | Case IDs, evidence IDs, transaction IDs (monospace stack) |

## 3. Spacing scale (4px base)

`--space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-6: 24px; --space-8: 32px; --space-12: 48px; --space-16: 64px;`

Page gutters: `--space-8` desktop, `--space-6` at 1024px. Card internal
padding: `--space-6`. Table cell padding: `--space-2` vertical /
`--space-4` horizontal (dense but not cramped).

## 4. Radii & elevation

```css
--radius-sm: 4px;   /* inputs, small badges */
--radius-md: 8px;   /* cards, buttons */
--radius-lg: 12px;  /* panels, dialogs */
--radius-pill: 999px; /* status badges */

--shadow-none: none;                              /* cards use border, not shadow — restraint */
--shadow-popover: 0 4px 16px rgba(18, 21, 28, 0.12); /* tooltips, dropdowns only */
--shadow-dialog: 0 8px 32px rgba(18, 21, 28, 0.18);  /* modals only */
```

Cards/tables/panels are bordered (`1px solid var(--color-border)`), not
shadowed — shadow is reserved for genuinely floating elements
(tooltips, dropdowns, dialogs) so it still communicates "above the
page" when it appears, per "subtle borders... minimal decoration."

## 5. Core components

### Button
Variants: `primary` (accent fill, white text — the one clear call to
action per view, e.g. "Start Investigation"), `secondary` (bordered,
`--color-surface` fill — most actions), `ghost` (no border/fill, text
only — tertiary actions, table row actions), `destructive` (danger
colors — reserved, not currently used anywhere in Phase 5B since no
destructive backend action exists). Sizes: `sm` (28px height, table/
inline use), `md` (36px height, default). Disabled state: 40% opacity,
`cursor: not-allowed`, never removed from layout (so a disabled "Human
Review" action stays visible-but-inert, per §4 of FRONTEND_UX.md).

### Badge
Pill-shaped (`--radius-pill`), `--text-small` weight 600, colored via
one of the semantic token triplets above. Every risk-tier badge
includes a leading icon (see §6) — color is never the only signal.
Variants: `risk` (LOW/MEDIUM/HIGH/CRITICAL), `graph` (Graph Flagged /
No Graph Evidence), `status` (Investigated / Not Investigated /
Investigating…), `ai` (small "AI" chip prefixing AI-generated content
blocks).

### Card / Panel
`--color-surface` background, `1px solid --color-border`,
`--radius-md`, `--space-6` padding. A `Card` header row (title +
optional right-aligned action) is a fixed sub-component, not
freehand-styled per usage — this is the componentization the
authorization message requires ("do not create 20 slightly different
cards").

### Table
Header row: `--color-surface-sunken` background, `--text-small`
weight 600 uppercase-tracking labels, bottom border
`--color-border-strong`. Body rows: `--color-surface`, bottom border
`--color-border`, hover state `--color-bg` background (signals
row-level interactivity without relying on a shadow). No zebra
striping — restraint over decoration; row separation comes from the
border only.

### Tabs
Underline style (not pill/segmented) — a bottom `2px solid
--color-accent` under the active tab label, `--color-text-secondary`
for inactive labels. Used within Case Investigation to switch between
"Evidence" / "Investigation Timeline" if both are long, and on
Investigation Report vs. raw JSON toggle in dev tooling only.

### Tooltip
`--shadow-popover`, `--color-text-primary` background /
`--color-text-inverse` text, `--radius-sm`, `--text-small`. Used for
disabled-button explanations (§4 of FRONTEND_UX.md) and evidence
`source_tool` clarification.

### Dialog
Reserved for a future confirm-style interaction; not required by any
Phase 5B screen (no destructive/write action exists to confirm).
Tokens defined for completeness (`--shadow-dialog`, `--radius-lg`) so a
later phase doesn't invent a second dialog style.

### Evidence component (`EvidenceItem`)
See §7 — the one component the authorization message calls out as a
first-class, dedicated design concern.

### Graph node/edge styles
See §8.

### StatTile (Risk Overview)
A `Card` variant: large `--text-display`-weight number, `--text-small`
label below, optional risk-colored left accent bar (`4px`,
`border-radius: --radius-sm 0 0 --radius-sm`) when the tile represents
a specific risk tier. Never a decorative chart behind the number.

### FilterBar (Case Queue)
A horizontal row of `secondary`-style dropdown/select controls +
segmented risk-tier quick-filter chips, with a `ghost`-style "Clear
filters" button that only renders when at least one filter is active.

### EmptyState / ErrorState
Shared component: centered icon + `--text-h2` message +
`--text-body` `--color-text-secondary` explanation + optional action
button. Same component, different icon/copy/action per §5 of
FRONTEND_UX.md's state table — never a bespoke empty/error layout per
screen.

### Skeleton
`--color-border` background pulse animation, shaped to match the final
content's bounding box (table row skeleton, card skeleton) — never a
generic full-page spinner for list/detail content.

## 6. Iconography

A small, fixed icon set (outline style, 16-20px, `currentColor` fill so
it inherits the token color it sits inside): check-circle (LOW),
alert-triangle (MEDIUM/HIGH, filled variant for HIGH), alert-octagon
(CRITICAL), share-2/network (graph-flagged), clock (timeline/pending),
shield-check (deterministic evidence), sparkles (AI-generated content),
user-check (human review). Implemented as inline SVG components (no
icon-font/network-dependent icon library), consistent with the
no-external-font decision in the preamble.

## 7. Evidence UX — deterministic vs. AI interpretation

This is the one place the authorization message calls "critical for
trust," so it gets an explicit, non-negotiable rule:

- **Deterministic evidence** (an `EvidenceItem` from the report, or any
  ML/graph field shown in "Risk Summary"/"Why This Case Was Flagged"):
  solid `1px solid --color-border` card, `shield-check` icon,
  `--color-text-primary` body text. Caption line always states its
  `source_tool` (e.g. "Source: get_graph_context").
- **AI interpretation** (`summary`, `graph_findings`,
  `behavioral_findings`, `legitimate_explanations`,
  `conflict_description`, `recommendation` — i.e., any prose the LLM
  generated, as opposed to a structured field it merely reported):
  `1px dashed var(--color-ai-border)` card, `--color-ai-bg`
  background, `sparkles` icon, an "AI" `Badge` in the card header.
  Every such block is prefixed with the literal label **"AI
  INVESTIGATION"** at the section level (per the authorization
  message's exact wording) — never presented as if it were a
  deterministic system output.
- The ML risk tier and graph evidence values ("Risk Summary" and "Why
  This Case Was Flagged") **never** render from
  `investigation_report.risk_tier` — always from `case.ml_risk_tier`
  directly, even though the two are guaranteed equal by the frozen
  agent's own validation (Phase 4N). This is a rendering-source rule,
  not just a visual one: it keeps the UI correct even if that
  invariant were ever weakened upstream.

## 8. Graph node/edge styling

- **Center node** (the case's own customer proxy): filled
  `--color-accent` circle, white label text, slightly larger radius
  than neighbor nodes.
- **Neighbor nodes**: `--color-surface` fill, `1.5px solid
  --color-graph-border` stroke, `--color-text-primary` label.
- **Edges**: colored by `relationship_type` — `SHARED_DEVICE` solid
  `--color-graph-text` (violet), `SHARED_IP` solid `--color-graph-ip-text`
  (cyan — corrected during Phase 5B visual validation from an earlier
  `--color-accent` choice that read too close to the violet at
  edge-stroke widths), `SHARED_BANK_ACCOUNT` solid `--color-risk-high-text`
  (orange) — three visually distinct strokes so multiple relationship
  types between the same pair of nodes remain individually legible,
  with a small legend rendered once per graph view (not per-edge label
  clutter — the legend is the label).
- Edge hover/selection reveals a tooltip with `shared_entity_value` and
  the neighbor's transaction id/dt (from `GraphVizEdge` +
  `GraphContextOutput`/`GraphNeighbor` data already fetched) — no new
  API call on hover.

## 9. Layout grid

12-column grid, `--space-8` gutters at ≥1440px; 8-column at 1280px;
narrows margins (not columns) at 1024px, per FRONTEND_UX.md's desktop-
first, three-breakpoint scope (Phase 5B.12). Case Investigation uses a
2-column layout above 1280px (main content ~66%, a persistent right
rail for Risk Summary + Human Review so those two things are always
visible without scrolling) and stacks to 1 column at 1024px.
