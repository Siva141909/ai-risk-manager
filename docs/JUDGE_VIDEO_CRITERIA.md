# Judge Video Criteria — Phase 7, Part 2

**INTERNAL JUDGE SIMULATION — not Razorpay's official scoring
criteria.** The official page (`docs/PITCH_REQUIREMENTS.md`) says
nothing about pitch-video structure; everything below is this
project's own judgment about what a judge watching a 5-minute video
cold, with only the public repo behind it, would actually respond to.

---

**1. What would make me immediately understand the product?**
A concrete before/after: three individually unremarkable transactions,
shown side by side, then revealed to share infrastructure. Not a
mission statement — a specific example on screen within the first 20
seconds.

**2. What would make me believe it actually works?**
Watching it run live, on the actual product, not slides. A judge who
sees a real click produce a real 40-second wait and a real result
trusts it more than any claim, because the wait itself is evidence
nothing was faked.

**3. What evidence would I expect?**
Numbers with a stated population and a stated split (held-out vs.
validation), not a bare percentage. "85.66% precision" alone is a
claim; "85.66% precision, on 8 rings, on a held-out benchmark generated
after the detector was frozen" is evidence.

**4. What would make me distrust the metrics?**
A single blended "accuracy" number. Precision/recall not broken out.
No mention of *when* the test set was generated relative to when the
detector was tuned. No confidence interval on a result computed from a
tiny sample (this project's own campus n=2 finding is exactly the kind
of thing that builds trust *if disclosed* and destroys it *if a judge
finds it later in the repo after the video implied everything was clean*).

**5. What technical depth would I want to see?**
One real architectural decision explained with its reasoning, not a
list of technologies. "We rejected a GNN because at this scale it would
just relearn our own injection rules" is depth. "We used XGBoost,
NetworkX, LangGraph, and Claude" is a tech-stack slide, not depth.

**6. What would make the project look like an LLM wrapper?**
Leading with the chat/investigation panel before showing that a
risk score and a graph flag already existed *before* the LLM was ever
called. If the video shows Claude first, it reads as "an LLM feature
with some data behind it." If it shows the deterministic detector
first, producing a real signal with zero LLM involvement, then
introduces Claude as an investigation layer *on top of* that signal, it
reads as the opposite.

**7. What would make the graph component convincing?**
Showing that the ML score for the same case was unremarkable — the
contrast is the proof, not the graph visualization by itself. A pretty
node-and-edge picture with no ML-score contrast next to it looks like
generic graph tech, not a fraud-specific capability.

**8. What would make the agent component convincing?**
The agent surfacing something a human would have had to look up itself
(a policy citation, a legitimate-explanation the presenter didn't
script) or explicitly flagging a conflict rather than picking a side.
Watching it hedge/escalate rather than confidently declare "this is
fraud" is more convincing than confidence would be, because
overconfidence from an LLM reads as scripted.

**9. What would make the UX convincing?**
The human-approval boundary being visually impossible to miss, and the
disabled action buttons being *visibly* disabled with a reason, not
silently absent. A judge who has to ask "wait, can this thing actually
freeze an account?" and gets no answer from the UI itself is a judge
who assumes the worst.

**10. What weaknesses should the presenter proactively acknowledge?**
Exactly one, stated once, briefly: the ground truth is synthetic
because no real abuse-ring-labeled dataset exists, so the metrics
measure recovery of an injected pattern, not real-world prevalence.
Said as a fact, not an apology — and said *before* a judge can ask it
as a "gotcha" question, which changes its effect entirely.

**11. What would make this memorable after watching 20 other
submissions?**
A specific, sourceable number said out loud, on camera, that most other
teams won't have: not "our model is accurate" but "every single
injected ring member had a LOW or MEDIUM ML score — the model was
structurally blind to every one of them, and the graph layer recovered
most of that group anyway." A judge remembers a claim they can check.

**12. What would make the metrics seem inflated or cherry-picked?**
Showing only the strong numbers (85.66% precision, 0% FP on one
category) without also showing that campus clusters had a 100%
false-positive rate at n=2. A judge who later opens the repo and finds
that number *not* mentioned in the video will read the whole pitch as
selectively edited — this project's own compliance docs already
disclose it, so the video should too, briefly.
