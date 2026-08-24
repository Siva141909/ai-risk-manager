# Pitch Script V1 — Phase 7, Parts 3-15

## A. Screen inventory and ranking (Part 3)

Inspected: `frontend/src/pages/*` (live), `docs/DEMO_FLOW.md`,
`docs/JUDGE_REVIEW.md` §10 (fresh-install screenshots),
`docs/RAZORPAY_TRACK_02_COMPLIANCE.md`, `docs/ARCHITECTURE.md`.

| Screen | Priority | What the judge sees | What the presenter says | Technical point proven | On-screen duration |
|---|---|---|---|---|---|
| Case Investigation (hero) | **P0** | ML score, graph evidence, network graph, AI Investigation panel, evidence, human-review boundary — all in one view | Most of the narration happens here | The whole product story in one screen | ~90s total, the longest single screen |
| Live "Start Investigation" → "Investigating…" → result | **P0** | A real click, a real wait, a real result rendering | "This is a live call, not a recording" (only if true — see Part 17) | The system isn't a mockup | ~15-45s depending on primary/fallback path |
| Human Review panel (within Case Investigation) | **P0** | "HUMAN APPROVAL REQUIRED" badge + visibly disabled action buttons | "The agent recommends. It cannot act." | Defense-only, human-in-the-loop | ~10s |
| Network graph (inline, within Case Investigation) | **P0** | Center node, neighbor nodes, colored typed edges, legend | "The graph connects transactions through shared device, IP, and bank-account signals" | Coordination detection is structural, not a black box | ~20-30s |
| Risk Overview | **P1** | Tier counts, coordination-detection tile, "Recent coordination-flagged cases" table | Sets up the problem before the demo | The product has real operational scale (177K cases) | ~15-20s, opening only |
| Architecture diagram | **P1** | The 8-stage labeled pipeline (README/`docs/ARCHITECTURE.md`) | "Here's the full path from a real transaction to a human decision" | REAL/SYNTHETIC/DETERMINISTIC/AI/HUMAN boundaries are explicit, not blurred | ~30-40s |
| Held-out metrics table | **P1** | Precision/recall/F1/FP rate/FP cost, one clean table | "We tested this once, on data the detector never saw while being built" | Track 02's exact evaluation-rigor bar is met | ~20-25s |
| Case Queue | **P2** | The full case list, filters | Skip narration, use only as a 2-3s transition shot if needed for pacing | Real triage scale exists | 0-3s, cut if time is tight |
| Demo Mode page | **P2** | 5 curated categories, labeled "dev tooling" | Optional one-line mention: "we picked this from a fixed, curated set of five" | Not cherry-picked from an unlimited pool | 0-5s, optional |
| Investigation Report page | **P2** | Same content as the inline panel, report-styled | Skip — redundant with what's already shown inline | Nothing new | 0s, don't show |
| Graph Explorer (full-screen) | **P3** | Same graph as inline, larger | Don't show — the inline graph already proves the point | Nothing new | 0s |
| Terminal / pytest output | **P3** | Test pass counts | Don't show unless proving latency via a real log line | Marginal — a number on a slide does the same job faster | 0s, or ≤3s if used for the latency claim only |
| OpenAPI docs / raw JSON | **P3** | API schema | Don't show — reads as a code review, not a product demo | Nothing a judge needs in 5 minutes | 0s |

## B. Chosen demo case (Part 7)

**`CASE-3457202`** (label: `ml_low_graph_high` in `src/api/demo_data.py`).
Chosen over the alternatives for one deciding reason: **it is the only
demo case with an already-verified, real (non-stub) Claude
investigation on record** — proven end-to-end in Phase 5B
(`docs/DEMO_FLOW.md` §5: real browser click, server log
`agent_duration_ms=44304`, `cache_hit=false`, `validation_status="passed"`)
and re-confirmed in Phase 6. Using a case with a real precedent
materially lowers the Part 17 failure risk — this case is known to
reliably complete a real Claude call, not merely theorized to.

It also happens to be the strongest **narrative** fit: ML score 1.1%
(MEDIUM tier — genuinely unremarkable on its own), graph evidence
places it in a 4-member community sharing one bank account with
relationship rarity score 1.00. Its real Claude report (already
produced, not hypothetical) contains every element Part 9 asks to show:
a stated conflict between structural and behavioral evidence, two
legitimate explanations, three policy citations, and
`recommendation=investigate_further` with `requires_human_review=true`.

**Not chosen, noted for transparency:** `CASE-3410549` (`strong_coordinated_ring`)
has a visually richer graph (11 members, two relationship types,
device+IP) and was considered for the graph-visualization moment
specifically — not used, to keep the demo to one continuous case rather
than switching mid-pitch, which would cost time without adding proof.
It remains available as a fallback case if the primary's real-Claude
call fails during recording (Part 17) since it also has a prior
successful real-Claude run on record (Phase 5B visual validation).

## C. The core story (Part 4)

```
PROBLEM
  A transaction can look normal in isolation while being part of
  coordinated abuse.
      ↓
WHY ORDINARY DETECTION MISSES IT
  Transaction-level scoring only ever sees one transaction at a time —
  it cannot structurally see that three "unrelated" accounts share a
  bank account.
      ↓
KEY INSIGHT
  ML asks "does this look risky?" Graph asks "is this connected to
  something bigger?" Those are different questions with different
  answers.
      ↓
SOLUTION
  Score every transaction. Separately, build a graph of shared device/
  IP/bank-account signals. When a connected structure forms, raise a
  case — regardless of what the individual score said.
      ↓
LIVE PRODUCT
  [demo]
      ↓
ARCHITECTURE
  [diagram]
      ↓
EVALUATION
  [held-out metrics]
      ↓
AI INVESTIGATION
  [already shown during the live demo — referenced, not re-demoed]
      ↓
LIMITATIONS
  Synthetic ground truth, stated once, plainly.
      ↓
WHY IT MATTERS
  [closing line]
```

Not chronological, not phase-by-phase — matches the explicit
instruction. The word "Phase" does not appear anywhere in this script.

## D. Three alternative hooks (Part 6)

**Hook 1 — chosen.** Cold open on the actual Risk Overview screen,
already showing real numbers, narrator not yet on camera:

> "Three transactions. Each one scores low or medium risk on its own.
> [cut to graph, edges drawing in] But they share a bank account. That's
> not three risky transactions — that's one coordinated one, wearing
> three faces."

**Hook 2 — alternative.** Direct statement, no visual yet:

> "A fraud model can be exactly right about a transaction and still
> completely miss the fraud — because the fraud isn't in the
> transaction. It's in the connections between transactions the model
> was never shown."

**Hook 3 — alternative.** Question-first:

> "What does a coordinated fraud ring look like to a model that only
> ever sees one transaction at a time? Individually risk-free. That's
> the problem we built for."

**Why Hook 1 wins:** it's the only one that opens on a real, specific,
on-screen number (this project's actual case data) instead of an
abstraction — matching Judge Criteria Q1/Q12 (`docs/JUDGE_VIDEO_CRITERIA.md`)
directly: concrete and memorable beats well-phrased and generic.

## E. Live UX demo flow (Part 7) — exact steps

1. Risk Overview loads — narrate the tier tiles and the "Recent
   coordination-flagged cases" table (Phase 6's fix — this table is
   what makes the opening hook's claim visible on the actual product,
   not just asserted).
2. Click into `CASE-3457202` (search or direct navigation — see
   `docs/PITCH_RECORDING_PLAN.md` for the exact URL).
3. Point at "Risk Summary": ML score 1.1%, tier MEDIUM.
4. Point at "Why This Case Was Flagged": graph signals column —
   community size 4, shared bank account, rarity score 1.00.
5. Point at the inline network graph — center node, 3 neighbor nodes,
   one colored edge type, legend.
6. Click "Start Investigation."
7. Let the genuine "Investigating…" state hold on screen (no fast-forward
   — the wait itself is evidence, per Judge Criteria Q2).
8. Result renders: read (don't paraphrase) the real Summary line.
9. Point at Evidence — real evidence IDs, real source tools.
10. Point at Conflicting Evidence + Legitimate Explanations side by
    side — this is the single best "the agent isn't just confirming
    the alarm" beat in the whole product.
11. Point at Human Review: "HUMAN APPROVAL REQUIRED" + the four visibly
    disabled action buttons.

## F. Graph demo language (Part 8)

Exact narration, ≤35 seconds on screen:

> "The transaction model sees these payments individually. The graph
> connects transactions through shared device, IP, and bank-account
> signals. When those connections form a coordinated structure — three
> or more accounts, one shared attribute, in this case a bank account —
> we raise a case. The model's own score for this transaction was 1.1
> percent. The graph is why we're looking at it anyway."

No mention of "heterogeneous graph," "connected components," or
"NetworkX" in the narration — that vocabulary belongs in the Q&A doc
(`docs/PITCH_QA.md`), not the pitch itself, per the explicit instruction
to avoid "we constructed a heterogeneous graph with..." phrasing.

## G. Claude demo language (Part 9)

> "The model doesn't decide this transaction is fraud. The deterministic
> system already produced the risk score and the graph evidence before
> Claude was ever called. What Claude does is investigate that evidence
> — check it against policy, look for a legitimate explanation, flag
> where the signals disagree — and write a cited report. [point to
> Conflicting Evidence] Here, it found exactly that: the structural
> signal says 'connected,' the behavioral signal says 'almost no
> history to judge by' — and it says so, instead of picking a side.
> [point to Human Review] And whatever it recommends, a person still has
> to approve it. The system investigates. It doesn't act."

## H. Architecture section (Part 10)

Show the diagram already committed to `README.md`/`docs/ARCHITECTURE.md`
verbatim — do not build a new one for the video:

```
REAL IEEE-CIS DATA → ML RISK MODEL → COORDINATION GRAPH →
ABUSE-RING CASE → LANGGRAPH INVESTIGATION → CLAUDE →
EVIDENCE-BACKED REPORT → HUMAN REVIEW
```

Narration (~30s):

> "Real transaction data in, at the top. A calibrated model scores
> individual risk. A separate graph layer finds coordination. Those two,
> together, become a case. LangGraph gathers the evidence a case needs;
> Claude reasons over it. Every claim in the final report traces back
> to a real tool call — nothing invented. And a human is the only thing
> that can turn any of this into a real action."

Point at the REAL/SYNTHETIC/DETERMINISTIC/AI/HUMAN labels explicitly —
this is the one moment in the video to say the word "synthetic" before
the limitations section does, so it isn't a surprise later.

## I. Results section (Part 11)

On-screen table, exactly these five numbers, nothing else:

| Metric | Value |
|---|---|
| Precision | 85.66% |
| Recall | 78.12% |
| F1 | 80.27% |
| False-positive rate | 4.17% |
| Illustrative FP cost | ₹1,500 |

Narration:

> "These numbers come from an independently generated held-out
> benchmark, evaluated once, after the detector's configuration was
> already frozen. Not the same data used to build it."

**Explicitly not shown:** the ML-only PR-AUC, the transaction-level 84%
figure, the full per-ring-type breakdown, any confidence interval — all
real, all in the repo, all one click away in
`docs/RAZORPAY_TRACK_02_COMPLIANCE.md`, none of it earns its 15-20
seconds in a 5-minute video. If a judge asks about the 84% figure,
`docs/PITCH_QA.md` has the answer ready.

## J. Limitation (Part 12)

Said once, ~15 seconds, no apology, right before the closing line:

> "One honest limitation: there's no public dataset with real
> coordinated-abuse labels, so our coordination ground truth is
> synthetic — injected, controlled, and independent of the real fraud
> label. The transaction-risk layer trains on real IEEE-CIS data. The
> coordination layer is evaluated against a benchmark we built and then
> held out. We're not claiming these numbers describe real-world
> abuse-ring prevalence — we're claiming the detector can find the
> structure when it exists, measured honestly."

## K. What NOT to show (Part 13)

Installation commands, any `pip install`/`npm install` terminal output,
a walkthrough of any of the 258 tracked files, a recitation of the
264-test count, feature-engineering detail, the full IEEE-CIS schema,
the weighting-strategy grid search, RAG/retrieval internals, the
`LLMClient` provider-abstraction code, any documentation *page* shown
as a scrolling wall of text, and any terminal log **except** the one
optional real-latency log line if it's used to support the ~43s claim
instead of just asserting it.

## L. Transitions (Part 14)

| From → To | Line |
|---|---|
| Problem → Why ordinary detection misses it | "So we asked a different question: not just 'is this transaction risky?' but 'are these transactions coordinated?'" |
| Solution → Live product | "That's not a slide. Let's look at the actual product." |
| Graph → Agent | "But detecting the pattern is only half the problem. An investigator still needs to know *why* the system flagged it." |
| Agent → Architecture | "Here's how that whole path actually fits together." |
| Architecture → Results | "And we don't want you to take any of that on faith." |
| Results → Limitation | "One honest limitation, stated plainly." |
| Limitation → Closing | "That's the whole point of testing it this way." |

---

## M. Full timed script (Part 15)

Total: **4:58**, under the 5:00 ceiling with 2 seconds of margin.

### 0:00–0:22 (22s)
**VISUAL:** Risk Overview, live product, cold open (no title card, no
narrator-on-camera yet).
**ACTION:** Page already loaded; cut straight to the "Recent
coordination-flagged cases" table.
**NARRATION:** "Three transactions. Each one scores low or medium risk
on its own. But they share a bank account. That's not three risky
transactions — that's one coordinated one, wearing three faces."
**TECHNICAL POINT:** The product's real data already contains this
exact pattern — not a staged example.
**JUDGE TAKEAWAY:** This is a real product, not a concept slide, from
second one.

### 0:22–0:50 (28s)
**VISUAL:** Narrator on camera or voiceover continues over the Overview screen.
**ACTION:** Point at the risk-tier tiles, then the coordination-detection tile.
**NARRATION:** "Ordinary fraud models score one transaction at a time.
That works when the fraud lives inside a single transaction. It
doesn't work when the fraud lives in the *relationship* between several
transactions that each look fine alone. So we asked a different
question: not just 'is this transaction risky?' but 'are these
transactions coordinated?'"
**TECHNICAL POINT:** States the core insight explicitly.
**JUDGE TAKEAWAY:** The problem is specific, not generic "fraud is bad."

### 0:50–1:20 (30s)
**VISUAL:** Split framing or quick cut: ML score alone, then graph
evidence appearing.
**ACTION:** None yet — this is the conceptual bridge before the live click-through.
**NARRATION:** "ML evaluates transaction-level risk. Graph evaluates
coordination across entities. The investigation agent explains the
evidence. A human keeps the final control. Let's watch that happen on
one real case."
**TECHNICAL POINT:** States the 4-layer architecture in one breath, before showing it.
**JUDGE TAKEAWAY:** Sets expectation for exactly what's about to be demoed.

### 1:20–2:10 (50s)
**VISUAL:** Navigate to `CASE-3457202` (Case Investigation page).
**ACTION:** Steps E.2–E.5 above — Risk Summary, Why This Case Was
Flagged (ML column vs. graph column), inline network graph.
**NARRATION:** "ML score: 1.1 percent. Medium tier — nothing alarming
on its own. But this customer's graph puts them in a 4-member community
connected by one shared bank account, with a maximum relationship
rarity score. [point at graph] The transaction model sees these
payments individually. The graph connects them through shared device,
IP, and bank-account signals. When that connection forms a coordinated
structure, we raise a case — regardless of what the individual score said."
**TECHNICAL POINT:** ML-low + graph-high divergence is the whole value
proposition, shown on one real case.
**JUDGE TAKEAWAY:** The graph isn't decoration — it's why this case exists at all.

### 2:10–2:55 (45s)
**VISUAL:** Click "Start Investigation." Genuine "Investigating…" state
holds. Result renders.
**ACTION:** Steps E.6–E.9 above.
**NARRATION (before the click):** "The model doesn't decide this is
fraud. The risk score and the graph evidence already exist,
deterministically, before Claude is ever called. What Claude does is
investigate that evidence." [click] "This takes real time — about
40 seconds — because it's a real model call, not a script." [while
waiting, hold silence or brief context] [on result] "Cited evidence.
Real source tools. Nothing invented."
**TECHNICAL POINT:** Detection and reasoning are separate layers;
latency is honest, not hidden or sped up.
**JUDGE TAKEAWAY:** This is a live system, proven by the wait itself, not a recording pretending to be one (see Part 17 for the fallback-labeling rule if this segment must use a backup take).

### 2:55–3:30 (35s)
**VISUAL:** Scroll to Conflicting Evidence, Legitimate Explanations, Policy Findings, Human Review.
**ACTION:** Step E.10–E.11.
**NARRATION:** "Here, it found a real conflict: the structural signal
says 'connected.' The behavioral signal says 'almost no history to
judge by.' It says so, instead of picking a side — and it lists a
legitimate explanation a joint account would produce the same pattern.
[point] Whatever it recommends, a person still has to approve it. The
system investigates. It doesn't act."
**TECHNICAL POINT:** Evidence-grounded reasoning + hardcoded human-approval boundary.
**JUDGE TAKEAWAY:** Defense-only isn't a policy statement — it's visibly, structurally true on screen.

### 3:30–4:05 (35s)
**VISUAL:** Cut to the architecture diagram (README/`docs/ARCHITECTURE.md`).
**ACTION:** Static diagram, narrator points through each stage left to right.
**NARRATION:** (§H above, verbatim)
**TECHNICAL POINT:** REAL/SYNTHETIC/DETERMINISTIC/AI/HUMAN boundaries are explicit engineering, not an afterthought.
**JUDGE TAKEAWAY:** The whole system's honesty is visible in one diagram.

### 4:05–4:35 (30s)
**VISUAL:** Cut to the results table (§I above).
**ACTION:** Static table, five numbers only.
**NARRATION:** "And we don't want you to take any of that on faith.
These numbers come from an independently generated held-out benchmark,
evaluated once, after the detector's configuration was already frozen
— not the same data used to build it." [read the five numbers once, plainly]
**TECHNICAL POINT:** Held-out, manifest-verified, Track 02's exact evaluation bar.
**JUDGE TAKEAWAY:** This team can defend every number on screen.

### 4:35–4:50 (15s)
**VISUAL:** Return to a calm product shot (Risk Overview or the architecture diagram, static).
**ACTION:** None.
**NARRATION:** (§J above, verbatim, ~15s)
**TECHNICAL POINT:** Experimental honesty stated proactively.
**JUDGE TAKEAWAY:** This team already knows their weak spot and isn't hiding it.

### 4:50–4:58 (8s)
**VISUAL:** Final static frame — product logo/name or the architecture diagram held.
**NARRATION (closing line — see Part 20 for the chosen one):** "A
transaction can look normal in isolation. We built the system that
checks whether it's part of something bigger — and never lets it act
alone."
**JUDGE TAKEAWAY:** The last sentence a judge hears is the core insight, restated once, memorably.

**Total runtime: 4:58.**
