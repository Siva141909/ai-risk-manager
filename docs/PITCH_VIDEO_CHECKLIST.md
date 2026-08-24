# Pitch Video Checklist — Phase 7, Part 19

Run through this immediately before submitting the final export.

## AUDIO
- [ ] Voice is clear and intelligible at normal playback volume with no boosting needed
- [ ] No background noise (fan, traffic, keyboard clatter) audible under the narration
- [ ] Volume is consistent across the whole 5 minutes — no segment noticeably louder/quieter than another (a common artifact of stitching a fallback take in, Part 17 — check this specifically if a fallback segment was used)

## SCREEN
- [ ] All on-screen text is readable at normal video-platform playback size, not just at full resolution — test by watching at the platform's default embed size, not full-screen
- [ ] No terminal window visible except the one optional log line used for the latency claim (`docs/PITCH_SCRIPT_V1.md` §K) — no `pip install`, `npm install`, or stray shell prompts
- [ ] No personal information visible anywhere (no real name/email in a browser profile menu, no OS notification banners)
- [ ] No API keys, tokens, or credentials visible in any terminal, `.env` file, or browser dev tools panel — **confirm no dev-tools panel is open at all** during recording
- [ ] No unrelated browser tabs, bookmarks bar, or extension icons visible
- [ ] Cursor movement is deliberate — no wandering, no idle circling while narration catches up

## DEMO
- [ ] The product shown is the real, running application (`http://localhost:5173`), not a mockup or slide pretending to be the product
- [ ] The demo case shown is `CASE-3457202`, an actual case from the real synthetic benchmark — not a fabricated example
- [ ] The graph shown is the real rendered network graph for that case, not a hand-drawn or slide-based illustration
- [ ] The Claude investigation shown is a real `claude_agent_sdk` run (verify `/health` showed `"llm_backend": "claude_agent_sdk"` before recording) — or, if a fallback segment was used, it is still a genuine prior real run of the same case, never stub output narrated as real (`docs/PITCH_RECORDING_PLAN.md` Failure Plan)
- [ ] No metric shown anywhere in the video is invented, rounded up, or different from what's in `docs/RAZORPAY_TRACK_02_COMPLIANCE.md`

## STORY
- [ ] The problem is stated concretely (the three-transactions hook) within the first 25 seconds
- [ ] Track 02 alignment is clear — "coordinated payment fraud / abuse-ring detection" is stated as the one class of loss, not implied
- [ ] The architecture is shown as one diagram with REAL/SYNTHETIC/DETERMINISTIC/AI/HUMAN labels legible
- [ ] The evidence-grounded nature of the agent's report is demonstrated on screen (real evidence IDs, real source tools), not just claimed in narration
- [ ] The five held-out metrics are shown together, clearly labeled as held-out and post-freeze
- [ ] The synthetic-ground-truth limitation is acknowledged once, plainly, without apologizing and without hiding it
- [ ] The closing line restates the core insight, not a generic "thanks for watching"

## TIME
- [ ] Total runtime is ≤ 5:00 (script targets 4:58, confirm the actual edited export matches — re-time after any cuts/re-takes, don't assume the script's timing survived editing unchanged)
