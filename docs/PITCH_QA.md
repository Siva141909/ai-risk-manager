# Pitch Q&A — Phase 7, Part 18

15 likely judge questions, each answerable out loud in 15-30 seconds.
Every answer traces to a specific repo file — full detail always
available if a follow-up goes deeper than the pitch itself.

**1. Why isn't this just XGBoost?**
"Because XGBoost only ever sees one transaction at a time — it
structurally cannot know that three separate accounts share a bank
account. Every injected coordination pattern in our benchmark had a
LOW or MEDIUM ML score. The model wasn't wrong about the transaction —
it was just never asked the coordination question." (`docs/ML_GRAPH_ABLATION.md` §4)

**2. Why graph?**
"Coordination is a connectivity problem. Representing shared device,
IP, and bank-account signals as a graph turns 'who's connected to
whom' into a well-studied algorithmic problem — connected components —
instead of ad hoc joins across tables."
(`ai_risk_manager_system_design.md` §35 Q2)

**3. Why no GNN?**
"At this data volume, with synthetic ring labels, a GNN would just
learn to detect the exact rules we used to inject the rings — it
can't outperform checking those same structural properties directly,
and it costs a lot more in interpretability. We measured that
trade-off explicitly rather than assuming it." (`ai_risk_manager_system_design.md` line 216)

**4. Why synthetic ring labels?**
"No public dataset has real, labeled cross-account collusion. The
honest alternative to synthetic labels isn't real data — it's not
building the coordination-detection layer at all." (`docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3)

**5. Do these metrics represent real fraud?**
"No, and we say that explicitly. They measure how well the detector
recovers an injected, controlled coordination pattern on data it never
saw during tuning. They're not a claim about real-world abuse-ring
prevalence." (`docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §9)

**6. What does Claude actually do?**
"It never sets the risk score or the risk tier — that's frozen before
Claude is ever called. It reasons over evidence that already exists:
checks it against policy, looks for a legitimate explanation, and
flags when structural and behavioral signals disagree. Every citation
it makes is checked against the real tool-call log — an invented
citation fails validation automatically." (`docs/SAFETY_MODEL.md` §3)

**7. Why does investigation take ~43 seconds?**
"That's a real Claude Agent SDK call gathering and reasoning over
evidence across up to a dozen tool calls — not an API round-trip we
could trivially speed up. It's measured, development-run latency, not
a production SLA claim." (`docs/AGENT_EVALUATION.md` §3, "Average latency" note)

**8. What happens if Claude fails?**
"Two different failure modes, both handled. If the agent's own
evidence validation fails, it's automatically routed to human review
as a normal result, not an error. If the model or connection itself is
unavailable, the API returns a clean 503 — never a stack trace, never
a silent hang." (`docs/BACKEND_ARCHITECTURE.md` §6)

**9. What is your false-positive rate?**
"4.17 percent on the held-out benchmark — 3 of 72 scored legitimate
shared-infrastructure clusters incorrectly flagged, with a 95%
confidence interval of about 1 to 12 percent." (`docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §7)

**10. Why is campus FP 100%?**
"Only 2 campus clusters were even scorable in this run, and both were
false positives — a small-sample result, not a stable rate. Campus
clusters mostly share an IP *range*, which our exact-value detection
view doesn't track directly; the rare case where one also happens to
share an exact device or bank value gets caught. We report that
honestly rather than smoothing it into the headline number." (`docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §7)

**11. Why NetworkX instead of Neo4j?**
"No measured algorithmic benefit at our scale — the largest connected
component is about 0.03 percent of the customer population. Neo4j
would add deployment risk with no accuracy gain we could actually
demonstrate." (`docs/GRAPH_BENCHMARK_FULL.md` §2)

**12. How did you prevent leakage?**
"A denylist blocks every ground-truth column from ever entering a
feature matrix, tested including a simulated 'forgot to filter' case.
And — found and fixed by our own audit, not by an outside reviewer —
our first graph evaluation had been implicitly tuned on the same data
it was reported against. We caught that and rebuilt a genuinely
independent held-out benchmark before finalizing these numbers." (`docs/LEAKAGE_PREVENTION.md`; `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3)

**13. Was the held-out set used for tuning?**
"No — it didn't exist yet when the detector's configuration was
frozen. It was generated afterward, with a seed never used anywhere
else in the project, and a file-hash manifest fails the evaluation
script if the held-out data or the detector's code ever diverge from
what was first recorded." (`docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §13)

**14. What would you change for production?**
"Three things: authentication on the API — deliberately out of scope
for a hackathon submission with no deployment; a real backend
aggregate endpoint instead of our current bounded client-side
enrichment for dashboard counts at scale; and validating the
coordination patterns against actual observed abuse, not just
synthetic injection, the moment real labeled data becomes available." (`docs/BACKEND_ARCHITECTURE.md` §10; `docs/FRONTEND_UX.md` §3)

**15. What is your biggest limitation?**
"The same one we lead with in the pitch: the ground truth is
synthetic. Every number we've shown you measures recovery of a pattern
we built and controlled, not real-world abuse-ring prevalence. We
think that's the honest way to report it — and we'd rather you hear it
from us first than find it yourselves." (`docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §9; `docs/JUDGE_REVIEW.md` §12)
