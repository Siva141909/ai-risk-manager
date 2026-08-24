# Pitch Recording Plan — Phase 7, Parts 16-17

Companion to `docs/PITCH_SCRIPT_V1.md` — this document is the
reproducible click-by-click recording spec.

## Setup

```bash
# Terminal 1 — backend, REAL Claude (primary recording path)
cd /path/to/repo
source .venv/bin/activate
RISK_MANAGER_LLM_BACKEND=claude_agent_sdk uvicorn src.api.main:app --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev -- --port 5173
```

**Before recording:** confirm both are healthy —
`curl http://127.0.0.1:8000/health` should show
`"llm_backend": "claude_agent_sdk"`. If it shows `"stub"`, the backend
was started wrong — stop and fix before recording, never narrate a stub
run as if it were real (per this project's own standing rule, restated
in `docs/PITCH_QA.md` Q6).

**Do NOT pre-warm the demo case's investigation cache before
recording** — the whole point of the live-click segment (0:22:10–0:22:55)
is a *first* investigation, `cache_hit: false`. If `CASE-3457202` was
investigated earlier in the same backend process, restart the backend
to clear the in-memory cache before the recording take.

## Browser / display

- **Resolution:** 1440×900 (matches every screenshot already validated
  in `docs/DEMO_FLOW.md`/`docs/JUDGE_REVIEW.md` — the layout was
  designed and visually verified at this width; do not record at a
  narrower width where the 2-column Case Investigation layout would
  collapse mid-recording).
- **Browser:** any Chromium-based browser, zoomed to 100% (no OS-level
  scaling), full-screen or a cleanly cropped window — no bookmarks bar,
  no other tabs, no extensions' icons visible in the toolbar.
- **Cursor:** move deliberately, pause on each element being narrated
  for ≥1s before moving on — no wandering.

## Exact route sequence

| Time | Route | Action |
|---|---|---|
| 0:00 | `http://localhost:5173/` | Already loaded before recording starts; cut straight to the "Recent coordination-flagged cases" table |
| 0:22 | *(same page)* | Pan to tier tiles, then the coordination-detection tile |
| 1:20 | `http://localhost:5173/cases/CASE-3457202` | Navigate directly by URL (fastest, avoids an on-camera search/filter detour) |
| 1:20–2:10 | *(same page)* | Scroll order: Risk Summary (right rail) → "Why This Case Was Flagged" (ML column, then graph column) → inline Network graph |
| 2:10 | *(same page)* | Click the **"Start Investigation"** button (right rail, primary blue button) |
| 2:10–2:55 | *(same page)* | Hold on the "Investigating…" panel state; do not scroll away; let the result render in place |
| 2:55–3:30 | *(same page)* | Scroll to: Conflicting Evidence block → Legitimate Explanations block → Policy Findings block → Human Review panel (right rail) |
| 3:30 | *(cut to static asset)* | `docs/ARCHITECTURE.md` diagram (screen-share the rendered markdown or a slide built from it — see note below) |
| 4:05 | *(cut to static asset)* | Results table (§I of the script — build as a simple slide, do not screen-record `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` scrolling) |
| 4:35 | `http://localhost:5173/` | Return to Risk Overview as the calm closing shot, OR hold the architecture diagram — either is acceptable, pick whichever cuts more smoothly from the results slide |

## What must NOT be clicked

- **Demo Mode** nav pill — do not open it on camera; it's dev tooling
  (`docs/FRONTEND_UX.md`), and clicking it mid-pitch signals "here's our
  internal testing page," undermining the "this is a real product" framing.
- **Case Queue**'s filter dropdowns — do not demonstrate filtering live;
  it adds clicks with no narration value in a 5-minute budget.
- **"Open Graph Explorer"** link — the inline graph already proves the
  point; opening the full-screen version adds a page transition with
  nothing new to say.
- **Any UI-only, disabled Human Review action button** — do not click
  them even though they're inert; clicking a visibly-disabled button on
  camera reads as confused, not as a demonstration of the boundary
  (pointing at them, not clicking, is what §E.11/§G ask for).
- **Browser back/forward buttons** — always navigate by direct
  interaction (clicking a link/button or typing a URL), never browser
  history, to avoid an accidental wrong-page flash on camera.

## Zoom / pause guidance

- Zoom in (screen-recording software zoom, not browser zoom) on: the ML
  score number (1.1%), the graph legend, the "HUMAN APPROVAL REQUIRED"
  badge, and the disabled action buttons row — these four moments are
  the ones a judge should be able to freeze-frame and read clearly even
  from a compressed video upload.
- Pause (hold the frame, no scrolling) for a full 2 seconds on the
  "Investigating…" state before any narration resumes — the pause
  itself communicates "this is really happening," faster than any line
  of narration could.

## Switching to slides/diagram

Two static-asset moments (3:30 architecture, 4:05 results) should be
prepared as simple, high-contrast slides **built from the exact content
already in `docs/ARCHITECTURE.md` and `docs/RAZORPAY_TRACK_02_COMPLIANCE.md`**
— transcribed, not paraphrased, so the on-screen text matches the repo
exactly and a judge who pauses the video and cross-checks the repo
finds identical wording. Do not invent new diagram styling under time
pressure during editing — reuse the existing labeled REAL/SYNTHETIC/
DETERMINISTIC/AI/HUMAN diagram as-is.

---

## Failure plan (Part 17)

**PRIMARY:** the real Claude investigation at 2:10, run live during
the actual recording session, `RISK_MANAGER_LLM_BACKEND=claude_agent_sdk`.

**FALLBACK, if the primary take fails during recording** (Claude Code
session/rate limit, backend crash, browser crash, investigation
exceeding a reasonable wait, or the graph failing to render): use a
**previously-recorded successful investigation segment** for
`CASE-3457202` specifically (a real run already exists on file per
`docs/DEMO_FLOW.md` §5, `agent_duration_ms=44304`) — re-record that one
segment in isolation once the issue is resolved, then edit it into the
same take. **Never fake a live call**: if a fallback segment is used,
the edited video must make this legible rather than pretending it's
one continuous live take —

- Do not claim on-camera "watch this happen live" if the segment being
  shown was recorded separately.
- Prefer neutral phrasing that stays true regardless of which take is
  used: *"This takes real time — about 40 seconds — because it's a real
  model call, not a script."* This sentence is honest whether the
  footage is the primary take or a legitimately re-recorded real
  investigation of the same case; it never claims "watch this specific
  moment being called right now" in a way a spliced edit would falsify.
- If the edited video visibly cuts between a live segment and a
  separately-recorded one, a simple, unobtrusive on-screen label (e.g.,
  a timestamp caption, or a brief "investigation segment" caption) is
  preferable to a seamless splice that could be mistaken for one
  continuous take — matching the explicit instruction not to present a
  recorded segment as a live network call.

**Specific fallback triggers and responses:**

| Failure | Response |
|---|---|
| Claude session/rate limit hit | Wait for reset (observed pattern: resets are same-day, `docs/AGENT_EVALUATION.md`), or substitute a legitimately re-recorded real run of the same case from a different session |
| Backend crashes mid-recording | Restart backend (`uvicorn` command above), re-take from 1:20 (case navigation) — cache will be empty again, so the "Start Investigation" click will still be a genuine first run |
| Browser fails/freezes | Restart browser, re-take from 1:20; do not attempt to resume mid-scroll, since a stitched mid-scroll cut is visually jarring |
| Investigation exceeds ~90s | This would itself indicate a real problem (the backend's own configured timeout is 90s, `docs/DEVELOPMENT_RUNBOOK.md`) — stop the take, investigate the cause before re-recording, do not speed up the footage in editing to hide a genuinely long wait (that would misrepresent the real latency claim) |
| Graph fails to render | Re-take from 1:20; if the issue recurs, fall back to `CASE-3410549` (also has a prior successful real-Claude run, richer graph) rather than debugging live during a recording session — but only as a last resort, since switching cases mid-plan means re-verifying every specific number in the script against the new case first |

**Never used as a fallback:** fabricating a new demo case, hand-writing
an `InvestigationReport`, or narrating stub output as if it were real
Claude reasoning — all explicitly prohibited by this project's standing
rules (`docs/AGENT_ARCHITECTURE.md` §3) and restated here because a
recording-day time crunch is exactly when that rule is most tempting to
bend.
