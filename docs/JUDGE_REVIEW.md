# Judge Review — Phase 6

Adversarial self-audit: acting as a Razorpay Buildathon judge, a senior
ML engineer, a fraud/risk-domain reviewer, a security reviewer, a
backend engineer, an AI/agent evaluator, a frontend/product UX
reviewer, and a reproducibility/open-source reviewer. Every claim below
was checked against the actual repository this session — file paths,
grep output, live-run output, and fresh screenshots — not recalled from
memory or assumed from prior reports.

---

## 1. Executive verdict

**The project is technically strong and unusually honest about its own
limits, but it had one real, judge-relevant UX gap (now fixed) and one
real reproducibility gap (now documented) that a first-time reviewer
would have hit within the first three minutes.** No P0 issue survives
this audit. The core technical claims (held-out precision/recall/F1,
defense-only architecture, real-Claude execution) all check out against
primary evidence, not just prose.

## 2. Requirement alignment (Part 0)

Re-fetched `https://razorpay.com/buildathon/` live this session — see
§3's exact quoted text. **Nothing has changed since the Phase 5C
fetch.** One new detail surfaced that Phase 5C's fetch didn't quote:
**"Eligibility: Students only."** This is a program eligibility
criterion (who may apply), not a Track 02 technical requirement — it
does not change anything about this project's compliance status, and
per the instruction to STOP only on a *requirement* change, this does
not trigger a stop. No Track 02 technical requirement, evaluation bar,
or general submission deliverable differs from what
`docs/RAZORPAY_TRACK_02_COMPLIANCE.md` already checks.

## 3. Frontend skill discovery (Part 1)

Checked the actual skills available in this Claude Code session before
touching any UI code:

| Skill | Relevant? | Used this phase? |
|---|---|---|
| `ui-ux-pro-max:ui-ux-pro-max` | Yes — UI/UX design intelligence, accessibility/interaction checklist | **Yes** — loaded its Pre-Delivery Checklist and used it to verify `cursor-pointer`, ARIA labels, `prefers-reduced-motion`, alt-text/icon conventions against the actual frontend code (§8) |
| `example-skills:webapp-testing` | Yes — Playwright browser automation | **Yes** — used to take fresh, adversarial screenshots of a genuinely clean install (zero pre-seeded investigations), which is what actually surfaced the P1 finding (§10) |
| `example-skills:frontend-design` | Yes — aesthetic direction guidance | Not invoked — the existing design system (`docs/DESIGN_SYSTEM.md`) already covers this ground and no P0/P1 issue required a new aesthetic direction |
| `dataviz` | Marginal (no charts in this product by design — `docs/FRONTEND_UX.md` explicitly avoids decorative charts) | Not invoked |
| `design` (Figma canvas) | No — no Figma MCP/plugin available in this environment (re-verified, unchanged since Phase 5B) | Not invoked, not installed |
| `example-skills:web-artifacts-builder` | No — targets Claude-artifact React/Tailwind apps, not a standalone repo | Not invoked |

No skill was installed. No skill claim is made without the verification
shown above.

## 4. Judge's first 3-minute experience (Part 2)

| # | Question | Answer location | Obvious in 30s? |
|---|---|---|---|
| 1 | What is this project? | `README.md` line 1, one-sentence summary | Yes |
| 2 | What track? | `README.md` "Razorpay AI Buildathon Track 02" banner (top) | Yes |
| 3 | What loss? | `README.md` scope-lock line: "coordinated payment fraud / abuse-ring detection" | Yes |
| 4 | What is the detector, exactly? | `docs/ARCHITECTURE.md` diagram; `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §1 | Yes, if the reader opens `docs/`; **not** from `README.md` alone within 30s — the README points to it but doesn't inline the pipeline diagram |
| 5 | Why a graph? | `docs/ML_GRAPH_ABLATION.md` §4 ("can it recover coordinated structure ML structurally cannot?") | Yes, once in that doc; not surfaced on `README.md` |
| 6 | Why an LLM? | `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §11 (component contribution table) | Yes, but requires knowing to look at the compliance doc, not the README |
| 7 | What is measured? | `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §4-8 | Yes |
| 8 | Where are the metrics? | `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §8 (one final table) + `data/processed/track02_holdout_evaluation_report.json` | Yes |
| 9 | Can I reproduce it? | `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §1 exact commands; `docs/REPRODUCIBILITY_AUDIT.md` for the full gap analysis | Partially — the exact commands are given, but **before this phase**, running them cold would have hit undocumented ordering issues (§11) |
| 10 | Can I run the demo? | `docs/DEMO_FLOW.md` | Yes |
| 11 | What is real data? | `docs/ARCHITECTURE.md` legend; `docs/CASE_MODEL.md` §1 | Yes |
| 12 | What is synthetic? | Same as above | Yes |
| 13 | What are the limitations? | `docs/AGENT_EVALUATION.md` §4 (agent marginal value), `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §7 (campus FP rate) | Yes, and unusually candid — not buried |

**Verdict: 11/13 clear within 30 seconds; 2/13 (#4, #9) required
already knowing which doc to open, i.e., the top-level `README.md`
didn't inline enough to answer them without one more click.** Not
severe enough to be P0 (the docs exist and are linked), noted as a P2
polish item, not fixed this phase (README already links every relevant
doc; adding a full pipeline diagram inline would be a nice-to-have, not
a correctness fix).

---

## 5. Judge questions — full answer set (Part 3/4)

Format per question: ANSWER / EVIDENCE / SECTION / STATUS.
STATUS legend: **CLEAR** = repo has a findable, correct answer (whether
flattering or not). **WEAK** = an answer exists but is incomplete,
hard to find, or under-tested. **MISSING** = no evidence found.
**CONTRADICTORY** = conflicting claims found.

### PRODUCT

**Q1. What problem are you solving?**
ANSWER: Coordinated payment fraud / abuse rings — accounts that look
individually low-risk but are structurally connected (shared device/IP/
bank account) and acting together.
EVIDENCE: `README.md`; `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §2.
SECTION: Scope-lock statement. STATUS: **CLEAR**

**Q2. Why is this a Razorpay problem?**
ANSWER: Razorpay Track 02 explicitly names "abuse-ring sentinel" as an
example direction under "stop the merchant losing money to fraud."
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §17 (verbatim fetched page text).
SECTION: §17. STATUS: **CLEAR**

**Q3. What exactly is the "one class of loss"?**
ANSWER: Coordinated payment fraud / abuse-ring activity — explicitly
not returns, chargebacks, or generic fraud.
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §2.
SECTION: §2. STATUS: **CLEAR**

**Q4. Why abuse-ring detection instead of ordinary fraud detection?**
ANSWER: Ordinary per-transaction fraud detection (XGBoost) already
exists as the "supporting context" layer; the graph layer answers a
structurally different question (coordination) that transaction-level
scoring cannot see by construction — demonstrated directly: every
injected ring member in validation+test had a LOW/MEDIUM ML tier (100%
missed by ML alone).
EVIDENCE: `docs/ML_GRAPH_ABLATION.md` §4.
SECTION: "Why the transaction-level result is expected." STATUS: **CLEAR**

**Q5. What happens if the graph detector didn't exist?**
ANSWER: Explicitly modeled — configuration A (`docs/AGENT_EVALUATION.md` §5)
is "raw ML score only," which for every one of the 8 held-out rings
would classify the ring member as LOW/MEDIUM risk and never surface the
coordination.
EVIDENCE: `docs/AGENT_EVALUATION.md` §5; `docs/ML_GRAPH_ABLATION.md` §4/§6 (quadrant D empty).
SECTION: as cited. STATUS: **CLEAR**

**Q6. What does the LLM actually add?**
ANSWER: Synthesizes already-deterministic evidence into a cited
narrative, surfaces conflicting signals explicitly, matches
legitimate-explanation policy text to the specific relationship type
found, and — demonstrated concretely on the held-out synthetic-test
case (`CASE-3400379`) — independently verified a pre-computed graph
narrative against live tool calls and caught a real discrepancy.
EVIDENCE: `docs/AGENT_EVALUATION.md` §4 ("strongest positive finding").
SECTION: §4. STATUS: **CLEAR**

**Q7. Could this work without an LLM?**
ANSWER: Yes — the entire measured Track 02 detector
(`scripts/run_track02_evaluation.py`) runs with zero LLM calls; the
XGBoost + graph layers are fully independent and produce the held-out
precision/recall/F1 numbers on their own.
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §11 (verified: the
script imports nothing from `src.agents.llm_client`).
SECTION: §11. STATUS: **CLEAR**

**Q8. Is the LLM making the risk decision?**
ANSWER: No — `risk_tier` in every final report is always
`case.ml_risk_tier` verbatim; the deterministic validator would reject
a report that tried to change it, and this is proven exactly across all
4 tiers by an automated test.
EVIDENCE: `tests/integration/test_agent_investigation_pipeline.py::test_risk_tier_in_final_report_matches_frozen_ml_tier_exactly`.
SECTION: n/a (test name is the section). STATUS: **CLEAR**

### DATA

**Q9. Where did the dataset come from?**
ANSWER: IEEE-CIS Fraud Detection (Kaggle competition dataset).
EVIDENCE: `docs/DATASET_ACQUISITION.md`.
SECTION: whole doc. STATUS: **CLEAR**

**Q10. Is IEEE-CIS real data?**
ANSWER: Yes — real transactions, real `isFraud` labels, never modified.
EVIDENCE: `tests/integration/test_reproducibility.py::test_real_columns_byte_identical_before_and_after_generation`.
SECTION: n/a. STATUS: **CLEAR**

**Q11. What fields are real?**
ANSWER: `TransactionID`, `TransactionDT`, `TransactionAmt`, `ProductCD`,
`card1-6`, `addr1`, `P_emaildomain`, `isFraud`, and the `train_identity.csv`
fields (`DeviceType`, `id_*`) for the 24.4% of rows with a matching identity record.
EVIDENCE: `docs/DATASET_AUDIT.md`, `docs/FEATURE_AUDIT.md`.
SECTION: field-provenance tables. STATUS: **CLEAR**

**Q12. What fields are synthetic?**
ANSWER: `customer_proxy_id`, `payment_instrument_proxy_id`,
device/IP/bank_account/address `_synthetic_id` columns, and all
`synthetic_*`/`legitimate_cluster_*` ground-truth columns.
EVIDENCE: `docs/SYNTHETIC_DATA_GENERATION.md` §5; `docs/ENTITY_MODEL.md`.
SECTION: as cited. STATUS: **CLEAR**

**Q13. Why are synthetic entities necessary?**
ANSWER: IEEE-CIS has no ground-truth coordinated-abuse-ring labels at
all — without an injected, controlled ground truth there is nothing to
measure ring-detection precision/recall against.
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3 ("Important question: what exactly is the held-out test set").
SECTION: §3. STATUS: **CLEAR**

**Q14. Are the synthetic labels independent from `isFraud`?**
ANSWER: Yes, by construction — ring membership assignment never reads
`isFraud`.
EVIDENCE: `docs/SYNTHETIC_DATA_GENERATION.md` §5; `tests/unit/test_ground_truth_and_leakage.py`.
SECTION: as cited. STATUS: **CLEAR**

**Q15. Could there be leakage?**
ANSWER: Multiple leakage vectors were identified and closed across
project history: ground-truth columns leaking into ML features (closed,
`src/features/leakage_guard.py`), the held-out test set being
contaminated by design-time tuning (found and closed this project's
Phase 5C, §3), and same-transaction reuse across splits (checked, not
found — `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3's residual-risk note).
EVIDENCE: `docs/LEAKAGE_PREVENTION.md`; `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3.
SECTION: as cited. STATUS: **CLEAR**

**Q16. How was leakage tested?**
ANSWER: `src/features/leakage_guard.py::assert_no_leakage` raises on any
denylisted column reaching a feature matrix, tested including a
simulated "forgot to filter" case; graph-detector leakage is tested by
the held-out immutability manifest (`scripts/run_track02_evaluation.py`).
EVIDENCE: `tests/unit/test_ground_truth_and_leakage.py`; `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §13.
SECTION: as cited. STATUS: **CLEAR**

**Q17. Could the customer proxy be misleading?**
ANSWER: Yes, explicitly documented as such — `customer_proxy_id` is "the
least-misleading of 7 tested [candidates], not a validated one," with a
confidence tier (`singleton`/`small`/`large_low_confidence`/`mega_unresolved`)
carried through every downstream consumer specifically because it is not
a clean 1:1 identity.
EVIDENCE: `docs/ENTITY_MODEL.md` (candidate comparison table, §3).
SECTION: candidate comparison. STATUS: **CLEAR**

**Q18. What happens to transactions without identity data?**
ANSWER: 75.6% of rows have no matching `train_identity.csv` row;
`DeviceType` and a `has_identity_data` boolean are both kept as
features specifically to let the model use "identity data is absent"
as a signal itself, rather than imputing a fake value.
EVIDENCE: `docs/FEATURE_AUDIT.md` (identity-field section).
SECTION: real identity-table fields. STATUS: **CLEAR**

### MODEL

**Q19. Why XGBoost?**
ANSWER: Best tabular fraud-detection performance/effort ratio; more
mature calibration tooling than LightGBM at the time of the decision.
EVIDENCE: `ai_risk_manager_system_design.md` §26 (Technology Decisions table).
SECTION: §26. STATUS: **CLEAR**

**Q20. What alternatives were tested?**
ANSWER: Rules-only baseline and logistic regression, both reported
alongside XGBoost in the same ablation table (not just claimed better
by assertion).
EVIDENCE: `docs/ML_BASELINE.md`; `docs/ML_GRAPH_ABLATION.md` §2 (stages A/B/C).
SECTION: as cited. STATUS: **CLEAR**

**Q21. What is the held-out ML performance?**
ANSWER: PR-AUC and precision/recall/F1 reported on the temporal
validation+test split, separate from the graph detector's own held-out
evaluation.
EVIDENCE: `docs/ML_BASELINE.md`; `docs/ML_GRAPH_ABLATION.md` §2 (PR-AUC 0.5207 for the fused pipeline).
SECTION: as cited. STATUS: **CLEAR**

**Q22. Why PR-AUC rather than only accuracy?**
ANSWER: Fraud is heavily class-imbalanced; accuracy is dominated by the
majority class and would look deceptively high for a model that flags
nothing.
EVIDENCE: `docs/ML_BASELINE.md`.
SECTION: metric-choice rationale. STATUS: **CLEAR**

**Q23. How was calibration handled?**
ANSWER: Isotonic calibration compared against Platt scaling; isotonic
selected and used for the frozen model (`data/processed/calibrator_isotonic.joblib`).
EVIDENCE: `docs/ML_BASELINE.md`; `data/processed/calibration_comparison.json` (gitignored, regenerable).
SECTION: calibration section. STATUS: **CLEAR**

**Q24. How were thresholds chosen?**
ANSWER: A documented, three-part framework — cost-minimizing sweep on
VALIDATION only for the MEDIUM/HIGH boundary, a recall-floor rule for
LOW/MEDIUM, a precision-floor rule for HIGH/CRITICAL — with the
`critical_precision=0.85` choice specifically investigated and justified
(0.5 was tried first and produced a degenerate empty HIGH tier).
EVIDENCE: `docs/RISK_THRESHOLD_POLICY.md`.
SECTION: whole doc, esp. §3-4. STATUS: **CLEAR**

**Q25. Was the test set used for tuning?**
ANSWER: No, for the ML layer — thresholds are fit on VALIDATION only,
verified by code inspection (no `.fit` call on test data anywhere in the
threshold-selection script). **Yes, this WAS true of the graph layer
before Phase 5C** (§3's central finding) — closed this project's own
Phase 5C by generating a genuinely independent held-out set.
EVIDENCE: `src/models/thresholds.py::select_thresholds` (takes `y_val`/`val_scores` only); `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3.
SECTION: as cited. STATUS: **CLEAR** (and notably, this project found
and disclosed its own prior leakage rather than a reviewer finding it first)

### GRAPH

**Q26. Why a graph?**
ANSWER: Ring detection is fundamentally a connectivity problem —
representing shared attributes as a graph turns "who is connected to
whom" into a well-studied algorithmic problem (connected components)
instead of ad hoc SQL joins.
EVIDENCE: `ai_risk_manager_system_design.md` §35 Judge Q&A #2.
SECTION: Judge Q&A. STATUS: **CLEAR**

**Q27. Why NetworkX instead of Neo4j?**
ANSWER: No measured algorithmic benefit at this data volume (max
component size 0.033% of the customer population at full scale); Neo4j
would add deployment/engineering risk for zero demonstrated accuracy
gain.
EVIDENCE: `ai_risk_manager_system_design.md` §26/§35 Q18; `docs/GRAPH_BENCHMARK_FULL.md` §2.
SECTION: as cited. STATUS: **CLEAR**

**Q28. Why no GNN?**
ANSWER: Explicitly rejected in the design doc — at this data volume,
with entirely synthetic ring labels, a GNN would learn to detect
exactly the injection rules that were written, which classical
structural metrics (component size, shared-attribute count) already
capture directly, at far lower engineering cost and better
interpretability.
EVIDENCE: `ai_risk_manager_system_design.md` line 216 (Technology Decisions table).
SECTION: as cited. STATUS: **CLEAR**

**Q29. Why exclude hub entities?**
ANSWER: `merchant_proxy`, `email_domain_proxy`, `payment_instrument_proxy`
were empirically confirmed as graph-topology hubs (near-universal
degree) that percolate any component containing them into one giant,
meaningless cluster — measured directly, not assumed, before being
excluded.
EVIDENCE: `docs/GRAPH_BENCHMARK.md` §3/§5; `docs/GRAPH_DATA_MODEL.md` Decision 2.
SECTION: as cited. STATUS: **CLEAR**

**Q30. How is a ring defined?**
ANSWER: A connected component of size ≥3 in the multi-attribute
(device+IP+bank_account) relationship graph — the threshold matches the
generator's own minimum configured ring size, a structural choice, not
fit to data.
EVIDENCE: `src/graph/signals.py::GRAPH_FLAG_MIN_COMMUNITY_SIZE`; `docs/GRAPH_BENCHMARK_FULL.md` §6.
SECTION: as cited. STATUS: **CLEAR**

**Q31. How are legitimate shared infrastructures handled?**
ANSWER: A dedicated hard-negative generator (household/office/campus/
business, 100 clusters at full scale) explicitly designed to look like
shared infrastructure *without* the ring's burst-timing/amount-sync
signature, then measured directly as false-positive rate — not assumed
safe.
EVIDENCE: `docs/SYNTHETIC_DATA_GENERATION.md` §3; `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §7.
SECTION: as cited. STATUS: **CLEAR**

**Q32. What is the graph false-positive rate?**
ANSWER: **Held-out: 4.17%** (3/72 scored hard-negative clusters, 95% CI
[1.4%, 11.6%]) — not the earlier full-benchmark's 0%, which was
development/validation data (§3).
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §7; `data/processed/track02_holdout_evaluation_report.json`.
SECTION: §7. STATUS: **CLEAR**

**Q33. What is the held-out graph precision?**
ANSWER: Mean (per-ring) 0.8566; pooled (member-level) 0.7174, 95% CI [0.5745, 0.8268].
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §4.
SECTION: §4. STATUS: **CLEAR**

**Q34. What is the held-out graph recall?**
ANSWER: Mean (per-ring) 0.7812; pooled (member-level) 0.7857, 95% CI [0.6406, 0.8829].
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §5.
SECTION: §5. STATUS: **CLEAR**

**Q35. What is the graph F1?**
ANSWER: Mean 0.8027 overall (0.7487 shared_device / 0.8561 shared_bank_account / 0.8035 multi_attribute).
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §6.
SECTION: §6. STATUS: **CLEAR**

**Q36. What is the confidence interval?**
ANSWER: Wilson score 95% CIs throughout (chosen specifically because
ring counts are small — a normal approximation would be unreliable or
produce out-of-[0,1] bounds); pooled precision [0.57, 0.83], pooled
recall [0.64, 0.88], FP rate [1.4%, 11.6%].
EVIDENCE: `src/graph/ring_recovery.py::wilson_confidence_interval`; `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §4/§5/§7.
SECTION: as cited. STATUS: **CLEAR**

**Q37. Why did performance differ between ring types?**
ANSWER: `multi_attribute` rings score lower precision (0.875 mean, but
one ring at 0.3529) because sharing 3 attributes gives decoys 3 separate
channels to coincidentally attach through, widening the detected
community; `shared_device` has the widest per-ring variance (one ring
recovered at 17 detected vs. 8 true members).
EVIDENCE: `docs/GRAPH_BENCHMARK_FULL.md` §4 (original finding); `data/processed/track02_holdout_evaluation_report.json::ring_recovery.detail` (held-out confirmation, `RING-SHARED_DEVICE-002`).
SECTION: as cited. STATUS: **CLEAR**

**Q38. Why did campus clusters produce false positives?**
ANSWER: Campus's primary sharing mechanism is an IP-*range* prefix,
which the multi-attribute exact-value detection view doesn't track
directly — the rare occasions a campus cluster *also* incidentally
shares an exact device/IP/bank value (ambient leakage) contaminate it.
Held-out result: 2 of 2 scored campus clusters were false positives
(100%, wide CI [34.2%, 100.0%], n=2) — reported plainly, not hidden.
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §7.
SECTION: §7. STATUS: **CLEAR** (and this is a genuinely weak result, disclosed as such)

**Q39. Did you tune against the held-out test set?**
ANSWER: No — verified two ways: (1) the held-out benchmark was
generated with a seed never used in any prior design decision, after
the detector config was already frozen and committed; (2) a manifest +
immutability check fails loudly if the held-out files or the detector's
source-hash ever diverge from what was first recorded.
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3/§13; `src/evaluation/track02_manifest.py`.
SECTION: as cited. STATUS: **CLEAR**

### AGENT

**Q40. Why LangGraph?**
ANSWER: Explicit state machine with conditional routing and a bounded
retry/fail-safe loop — matches the investigation workflow's actual
shape more transparently than an ad hoc function-calling loop.
EVIDENCE: `ai_risk_manager_system_design.md` §26; `docs/AGENT_ARCHITECTURE.md` §2.
SECTION: as cited. STATUS: **CLEAR**

**Q41. Why Claude?**
ANSWER: Structured tool use and reliable JSON-schema-constrained output;
also a deliberate narrative alignment with Razorpay's own Agent Studio
being built on the Claude Agent SDK (stated as a minor, not deciding, factor).
EVIDENCE: `ai_risk_manager_system_design.md` §26.
SECTION: Technology Decisions. STATUS: **CLEAR**

**Q42. What tools can Claude call?**
ANSWER: Exactly 10, all read-only, all named `get_*`, all schema-validated and allowlisted.
EVIDENCE: `src/tools/registry.py::TOOL_REGISTRY`; `docs/TOOL_CONTRACTS.md`.
SECTION: as cited. STATUS: **CLEAR**

**Q43. Can Claude access ground truth?**
ANSWER: No — structurally impossible, not just policy: `AgentInput`'s
only constructor takes a `Case`, which has no field that could hold
`CaseGroundTruth` data.
EVIDENCE: `docs/CASE_MODEL.md` §1; `tests/unit/test_agent_case_contract.py`.
SECTION: §1. STATUS: **CLEAR**

**Q44. Can Claude modify the risk score?**
ANSWER: No — see Q8.
EVIDENCE: same as Q8. STATUS: **CLEAR**

**Q45. Can Claude execute an irreversible action?**
ANSWER: No — exactly one mutating API route exists in the entire
system (`POST /investigate`, which only *requests* an investigation),
verified by an automated test that enumerates every route/method.
EVIDENCE: `tests/unit/test_defense_only_audit.py::test_only_one_mutating_route_exists_and_it_is_investigate`; `docs/DEFENSE_ONLY_AUDIT.md`.
SECTION: as cited. STATUS: **CLEAR**

**Q46. What happens if Claude hallucinates?**
ANSWER: A deterministic (non-LLM) validator checks every cited
`evidence_id` against the actual tool-call log for that investigation;
an invented ID fails validation and the report is routed to a bounded
repair-then-fail-safe path.
EVIDENCE: `docs/SAFETY_MODEL.md` §3; `tests/unit/test_agent_safety.py::test_invented_evidence_id_fails_validation`.
SECTION: §3. STATUS: **CLEAR**

**Q47. How are citations validated?**
ANSWER: Every `EvidenceItem.evidence_id` in the final report is checked
for membership in the set of IDs actually returned by tool calls in
this investigation — including a scan of free-text fields for
ID-shaped tokens that were never cited structurally, catching an attempt
to slip an invented entity into prose instead of the evidence list.
EVIDENCE: `src/agents/safety.py::validate_investigation_report`.
SECTION: as cited. STATUS: **CLEAR**

**Q48. What happens when evidence conflicts?**
ANSWER: A dedicated `conflicting_evidence` boolean + required
`conflict_description` field — validation fails if the flag is true but
the description is empty, so a conflict can't be silently flagged
without being explained.
EVIDENCE: `src/agents/schemas.py::InvestigationReport`; `tests/unit/test_agent_safety.py::test_conflicting_evidence_without_description_fails`.
SECTION: as cited. STATUS: **CLEAR**

**Q49. What happens when data is missing?**
ANSWER: Explicitly tested as one of the 5 demo categories
("missing_data") — the agent correctly recommends `close` with
`conflicting_evidence=false` when evidence is genuinely, not just
sparsely, absent; contrasted directly against a structurally similar
but inconsistently-scored case (`docs/AGENT_EVALUATION.md` §4's
cases-2-vs-12 finding — disclosed as a real limitation, not hidden).
EVIDENCE: `docs/AGENT_EVALUATION.md` §3/§4; `src/api/demo_data.py`.
SECTION: as cited. STATUS: **CLEAR**

**Q50. What happens when Claude fails?**
ANSWER: Two distinct failure modes, both handled: (1) the graph's own
evidence-validation failure routes to `fail_safe_human_review`
(`validation_status="failed_human_review"`, a normal 200 response, not
an error); (2) an LLM transport failure (session limit, connectivity)
is caught at the API layer and mapped to a 503.
EVIDENCE: `docs/SAFETY_MODEL.md` §4; `docs/BACKEND_ARCHITECTURE.md` §6.
SECTION: as cited. STATUS: **CLEAR**

**Q51. What happens if the Claude session/API is unavailable?**
ANSWER: This actually happened during Phase 4 evaluation (a genuine
Claude Code session-limit error on 5/12 cases) — documented honestly at
the time, re-run once the limit reset, never backfilled with stub
output relabeled as real.
EVIDENCE: `docs/AGENT_EVALUATION.md` §3 (git history of the doc records
the original failure and resolution); `src/api/errors.py::LLMUnavailableError`.
SECTION: as cited. STATUS: **CLEAR**

**Q52. What is the average investigation latency?**
ANSWER: **~42.9 seconds** (arithmetic mean of the 12 published
real-Claude per-case latencies: 53.72, 19.05, 44.49, 58.72, 55.80,
42.51, 51.64, 45.34, 38.17, 35.58, 49.88, 20.06 — computed from the
already-published table, not a new measurement).
EVIDENCE: `docs/AGENT_EVALUATION.md` §3 (per-case table; this average
itself was not pre-computed in any doc before this audit).
SECTION: §3. STATUS: **WEAK** — the underlying data is fully public
and correct, but no doc stated a single "average latency" figure before
this review computed one from it; worth adding to `docs/AGENT_EVALUATION.md`
in a future pass (not done this phase — would be a documentation
addition with no factual change, but out of this audit's minimal-touch scope).

**Q53. Is the agent actually better than deterministic rules?**
ANSWER: Mixed, and reported as mixed — clear, material value on cases
with no graph evidence at all (config A/B have nothing to say; the
agent independently investigates and reaches differentiated
conclusions) and on the one case where it caught a live contradiction
between claimed and verified graph evidence; **marginal or unclear
value** on single-attribute, low-ML shared-infrastructure cases, where
a human using the raw graph flag alone would likely reach the same
practical conclusion.
EVIDENCE: `docs/AGENT_EVALUATION.md` §5 ("Agent value test... not forced positive").
SECTION: §5. STATUS: **CLEAR**

**Q54. Are there cases where the agent provides little additional
value?**
ANSWER: Yes, explicitly identified — cases 3-6 (single-attribute
household/office/campus/business patterns), and a genuine reasoning
inconsistency between two structurally identical cases (2 vs. 12) is
disclosed as an open, unresolved finding.
EVIDENCE: `docs/AGENT_EVALUATION.md` §4/§5.
SECTION: as cited. STATUS: **CLEAR**

### SECURITY

**Q55. Is the system defense-only?**
ANSWER: Yes, audited directly this project (not just asserted).
EVIDENCE: `docs/DEFENSE_ONLY_AUDIT.md`; `tests/unit/test_defense_only_audit.py` (5/5 passing).
SECTION: whole doc. STATUS: **CLEAR**

**Q56. Does any endpoint perform a financial action?**
ANSWER: No — see Q45.
EVIDENCE: same as Q45. STATUS: **CLEAR**

**Q57. Can the user manipulate risk tiers?**
ANSWER: No, at two independent layers: the request schema has no field
for it at all (not just server-side rejection — the TypeScript type
doesn't expose one either), and an attempted extra field is rejected
with 422 (`extra="forbid"`).
EVIDENCE: `src/api/schemas.py::InvestigateRequest`; `frontend/src/types/api.ts`; `tests/api/test_security.py::test_client_cannot_override_risk_tier_via_extra_field`.
SECTION: as cited. STATUS: **CLEAR**

**Q58. Can the user inject arbitrary tools?**
ANSWER: No — `ToolRegistry.call` checks every tool name against a fixed
allowlist before doing anything else; there is no dynamic
dispatch-by-string capable of reaching an unregistered function.
EVIDENCE: `src/tools/registry.py::ToolRegistry.call`; `docs/TOOL_CONTRACTS.md`.
SECTION: as cited. STATUS: **CLEAR**

**Q59. Can prompt injection affect the agent?**
ANSWER: Architecturally mitigated (untrusted text wrapped in explicit
"data, not instructions" delimiters, system prompt instructs the model
never to follow embedded instructions) and tested end-to-end, including
a case where the agent correctly identified and disregarded an
instruction-shaped string embedded in a graph narrative during a real
Claude run. A secondary regex-based detector logs suspicious patterns
but is explicitly documented as *not* the real defense (a regex can
always be evaded).
EVIDENCE: `docs/SAFETY_MODEL.md` §2; `docs/AGENT_EVALUATION.md` §4 (case 7's live example);
`tests/unit/test_agent_safety.py`.
SECTION: as cited. STATUS: **CLEAR**

**Q60. Can the agent access evaluation ground truth?**
ANSWER: No — see Q43.
EVIDENCE: same as Q43. STATUS: **CLEAR**

**Q61. Are secrets excluded from the repository?**
ANSWER: Yes — verified by an automated scan of every git-tracked file,
zero secret-shaped strings found.
EVIDENCE: `scripts/pre_submission_check.py`; live-run result in `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §15.
SECTION: §15. STATUS: **CLEAR**

**Q62. Is the raw IEEE-CIS dataset committed?**
ANSWER: No — `.gitignore` excludes `data/raw/*`, verified: zero raw
dataset filenames among 255 tracked files.
EVIDENCE: `.gitignore`; `scripts/pre_submission_check.py` output.
SECTION: as cited. STATUS: **CLEAR**

### EVALUATION

**Q63. What exactly is the held-out test set?**
ANSWER: A second, independent full-scale (590,540 real transactions)
synthetic coordinated-abuse benchmark, generated with a seed never
used in any prior design decision, after the detector's configuration
was already frozen.
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3.
SECTION: §3. STATUS: **CLEAR**

**Q64. How was it generated?**
ANSWER: The identical, unmodified `src/generator/pipeline.py::run_generator`
the design/validation benchmark used — only the seed differs.
EVIDENCE: `scripts/generate_holdout_benchmark.py`.
SECTION: module docstring. STATUS: **CLEAR**

**Q65. What seed was used?**
ANSWER: `20260824` (documented as chosen: today's generation date,
distinct from seed 42 used for all dev/validation work and seed 99
used only in two small unrelated unit-test sanity checks).
EVIDENCE: `scripts/generate_holdout_benchmark.py::HOLDOUT_TEST_SEED`.
SECTION: as cited. STATUS: **CLEAR**

**Q66. Was it ever used during tuning?**
ANSWER: No — it did not exist until after the detector configuration
was frozen (Phase 5C, chronologically after all Phase 1-3 tuning work).
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3.
SECTION: §3. STATUS: **CLEAR**

**Q67. How was test immutability enforced?**
ANSWER: A file-hash manifest recorded on first evaluation run; every
subsequent run recomputes and fails hard if the held-out files changed
— verified live by running the evaluation script twice in succession.
EVIDENCE: `scripts/run_track02_evaluation.py::step3_verify_test_set_manifest`; `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §13.
SECTION: as cited. STATUS: **CLEAR**

**Q68. Can I reproduce the exact metrics?**
ANSWER: Yes, mechanically — but §11 (Reproducibility) found the
*surrounding* pipeline (feature engineering, model training) lacked a
single documented run order before this phase; the Track 02 evaluation
specifically (`generate_holdout_benchmark` → `run_track02_evaluation`)
was always a clean 2-command sequence.
EVIDENCE: `docs/REPRODUCIBILITY_AUDIT.md`; `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §1.
SECTION: as cited. STATUS: **WEAK before this phase, CLEAR after** — fixed by adding the consolidated sequence to `docs/DEVELOPMENT_RUNBOOK.md` this same session.

**Q69-72. Precision / Recall / F1 / False-positive rate**
ANSWER: 0.8566 (mean precision) / 0.7812 (mean recall) / 0.8027 (mean
F1) / 4.17% (FP rate). See Q33-35, Q32 for the same figures with CIs.
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §4-7. STATUS: **CLEAR**

**Q73. What is false-positive cost?**
ANSWER: ₹1,500 illustrative (3 false-positive clusters × ₹500 per
investigation).
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §7; `src/evaluation/track02_cost.py`.
SECTION: §7. STATUS: **CLEAR**

**Q74. What assumptions are behind the cost model?**
ANSWER: ₹500/investigation is reused from the existing ML-layer
illustrative cost (analyst time + customer friction), explicitly
labeled "ILLUSTRATIVE COST MODEL — not Razorpay's real internal cost"
in both the module docstring and every generated report.
EVIDENCE: `src/evaluation/track02_cost.py` module docstring.
SECTION: as cited. STATUS: **CLEAR**

**Q75. What are the weakest results?**
ANSWER: Campus cluster false-positive rate (100%, n=2, held-out);
`shared_device` ring precision on one specific ring (0.3529, a
17-member detected community for an 8-member true ring); the cases-2-vs-12
agent-consistency finding.
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §7; `data/processed/track02_holdout_evaluation_report.json`; `docs/AGENT_EVALUATION.md` §4.
SECTION: as cited. STATUS: **CLEAR**

**Q76. What results would you NOT advertise?**
ANSWER: The campus 100% FP rate and the pooled (as opposed to
per-ring-mean) precision of 0.7174 are the two numbers a less honest
version of this project might have left out of a headline slide — both
are in the compliance doc's main tables, not buried in an appendix.
EVIDENCE: `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §4/§7 (both appear in the primary tables, not a footnote).
SECTION: as cited. STATUS: **CLEAR**

### ENGINEERING

**Q77. Can I install the project?**
ANSWER: Yes — `pip install -r requirements.txt` (backend) and `npm install` (frontend) both succeed standalone.
EVIDENCE: `docs/REPRODUCIBILITY_AUDIT.md` §1. STATUS: **CLEAR**

**Q78. Can I run it without the private dataset?**
ANSWER: Partially — 146/228 backend tests and all 36 frontend tests,
yes; the live API server and the remaining 82 backend tests, no (they
need the generated pipeline artifacts).
EVIDENCE: `docs/REPRODUCIBILITY_AUDIT.md` §1-2.
SECTION: as cited. STATUS: **WEAK before this phase (undocumented), documented now**

**Q79. Can I run the demo?**
ANSWER: Yes, after the generation pipeline (§68); `docs/DEMO_FLOW.md` gives the exact steps.
EVIDENCE: `docs/DEMO_FLOW.md`. STATUS: **CLEAR**

**Q80. Can I run tests?**
ANSWER: Yes — `pytest -q` (backend), `npm test` (frontend); see Q78 for
the data-dependency caveat.
EVIDENCE: `README.md` "Running tests". STATUS: **CLEAR**

**Q81. Are there deterministic seeds?**
ANSWER: Yes — `configs/seed.yaml` (42) for all dev/validation work,
`HOLDOUT_TEST_SEED` (20260824) for the held-out test, never mixed.
EVIDENCE: as cited in Q65. STATUS: **CLEAR**

**Q82. Is the system provider-agnostic?**
ANSWER: Yes for the LLM layer — `LLMClient` Protocol, three
implementations, LangGraph depends only on the Protocol.
EVIDENCE: `src/agents/llm_client.py`; `docs/AGENT_ARCHITECTURE.md` §3.
SECTION: as cited. STATUS: **CLEAR**

**Q83. Can Claude be replaced with an API provider?**
ANSWER: Architecturally yes (`AnthropicAPIClient` is fully implemented)
— but it has **never actually been exercised end-to-end** in this
project (no `ANTHROPIC_API_KEY` available in any development
environment used so far), honestly disclosed as such in every phase
report that touched it.
EVIDENCE: `src/agents/llm_client.py::AnthropicAPIClient`; `docs/AGENT_ARCHITECTURE.md` §3 ("never exercised in this project").
SECTION: as cited. STATUS: **WEAK** — implemented but untested; this is
the single clearest "trust but verify" gap in the whole agent layer,
and the project itself says so.

**Q84. What happens in stub mode?**
ANSWER: Deterministic template-filled reports, every field prefixed
`"STUB TEST:"`, zero network calls — used for 100% of the automated
test suite.
EVIDENCE: `src/agents/llm_client.py::StubLLMClient`.
SECTION: as cited. STATUS: **CLEAR**

**Q85. What happens in real Claude mode?**
ANSWER: A live, ~43s-average call through the local Claude Code CLI's
own authentication — demonstrated end-to-end via a real browser click
in Phase 5B (`docs/DEMO_FLOW.md` §5, 44.3s, `validation_status="passed"`,
verified via server log + screenshots, not just claimed).
EVIDENCE: `docs/DEMO_FLOW.md` §5. STATUS: **CLEAR**

**Q86. Are frontend and backend contracts typed?**
ANSWER: Yes — `frontend/src/types/api.ts` is a hand-maintained,
field-for-field mirror of `src/api/schemas.py`, snake_case preserved
specifically so the two can be diffed against each other.
EVIDENCE: `docs/FRONTEND_ARCHITECTURE.md` §4.
SECTION: §4. STATUS: **CLEAR**

**Q87. Is the API documented?**
ANSWER: Yes — hand-written reference (`docs/API.md`) plus auto-generated
OpenAPI (every route has summary/description/schemas/error responses,
verified programmatically during Phase 5A).
EVIDENCE: `docs/API.md`; `src/api/routers/*.py` route decorators.
SECTION: as cited. STATUS: **CLEAR**

### UX

**Q88-98:** answered in §8 (UX review) below, since these require
visual evidence (screenshots) rather than a single file citation each.

---

## 6. Evidence map (Part 4 summary)

The single most load-bearing files, if a judge opens only five:
`docs/RAZORPAY_TRACK_02_COMPLIANCE.md` (compliance + metrics),
`docs/ARCHITECTURE.md` (diagram), `docs/DEFENSE_ONLY_AUDIT.md`
(security), `docs/AGENT_EVALUATION.md` (honest agent limitations),
`data/processed/track02_holdout_evaluation_report.json` (raw numbers,
gitignored/regenerable — reproduce via the two-command sequence in
`docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §1).

---

## 7. Claim/evidence consistency audit (Part 5)

Searched the entire repository for every number/phrase listed in the
task: `84%`, `85.66%`, `78.12%`, `80.27%`, `4.17%`, `0% false
positives`, `₹` costs, `"real data"`, `"held-out"`, `"production"`,
`"AI"`, `"agent"`, `"real-time"`, `"fraud"`, `"abuse ring"`.

**One genuine ambiguity found and fixed this phase:** `docs/ML_GRAPH_ABLATION.md`
§4's "84%" (transaction-level: fraction of ring-member rows in
validation+test that are also `graph_flagged=True`) and
`docs/RAZORPAY_TRACK_02_COMPLIANCE.md`'s "78.12%"/"85.66%" (ring-level:
precision/recall of recovering whole rings on the held-out set) measure
genuinely different things, on different datasets (seed 42 vs. seed
20260824), and nothing previously cross-referenced them — a reader
could reasonably wonder which one is "the real number." **Fixed:** a
clarifying paragraph was added to `docs/ML_GRAPH_ABLATION.md` this
session explaining the distinction; **no number was changed.**

**"0% false positives"** appears in `docs/GRAPH_BENCHMARK_FULL.md` §5
(the seed-42, pre-holdout, full-benchmark result) — this is a real,
correctly-labeled number for *that* dataset, and is not contradicted by
the held-out 4.17%; they are different datasets by design (§3), and
`docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3 explicitly explains why the
seed-42 number could never have been the Track 02 compliance figure.
No fix needed — already correctly scoped in its own document, though a
reader who found the 0% figure first (e.g. via search) without also
finding §3's explanation could be misled; this is the same underlying
"multiple valid numbers, needs a map" issue as the 84% case, and the
same fix (the new ML_GRAPH_ABLATION.md cross-reference, plus this
document itself) mitigates it.

**"Real-time"** — checked for overclaiming (e.g. implying live
production streaming). Usage is consistently scoped to the specific,
correct meaning: `Case.ml_risk_score` is a "real-time feature" in the
sense of "computed from strictly-past data relative to the trigger
transaction" (`docs/CASE_MODEL.md` §5), never "the system processes
live traffic in production" (it doesn't — no deployment exists,
`docs/BACKEND_ARCHITECTURE.md` §10).

**"Production"** — searched; the phrase "PRODUCTION CASE DATA" in
`docs/CASE_MODEL.md` refers to the `Case` object's role (what the agent
sees, vs. evaluation-only `CaseGroundTruth`), not a claim of a deployed
production system. No overclaiming found.

**No instance found anywhere of "% of real fraud" applied to a
synthetic-label result** (re-confirmed this phase via repo-wide grep,
matching the Phase 5C finding).

**Verdict: one real ambiguity (fixed this phase), zero contradictions, zero stale/false numbers.**

---

## 8. Experimental validity audit (Part 6)

```
Dataset (IEEE-CIS, real, unmodified)
  ↓
Development (data/synthetic/dev/, seed 42, 20K rows) — generator design
  ↓
Validation (data/synthetic/full/, seed 42, 590K rows) — view/weighting/
             community-method grid search (scripts/graph_benchmark_full.py)
  ↓
Configuration freeze (docs/GRAPH_BENCHMARK_FULL.md §6, committed before
                       Phase 5C began)
  ↓
Held-out test (data/synthetic/holdout_test/, seed 20260824, generated
                Phase 5C, AFTER the freeze)
  ↓
Final metrics (data/processed/track02_holdout_evaluation_report.json)
```

| Check | Verified? | Evidence |
|---|---|---|
| Test wasn't used for tuning | Yes | Held-out data didn't exist until after the freeze; manifest hash-checked |
| Generator configuration frozen | Yes | `configs/generator.yaml` hashed into the manifest, unchanged since Phase 3 |
| Graph configuration frozen | Yes | View/weighting/method are literal values in the manifest, not just "whatever the code does" |
| Thresholds frozen | Yes | `GRAPH_FLAG_MIN_COMMUNITY_SIZE=3` is a structural constant, never fit to data |
| Seed recorded | Yes | Both seeds (42, 20260824) explicitly documented with justification |
| Test benchmark is independent | Yes, with one residual caveat | Same 590,540-row real-transaction pool underlies both seeds — checked and judged astronomically unlikely to matter at this injection density (`docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3's own stated residual note) |
| Evaluation script is deterministic | Yes | Re-ran twice, byte-identical `combined_config_hash` and graph stats both times |

**Nothing flagged as questionable beyond the one residual note already
disclosed by the compliance doc itself.**

---

## 9. Security review (Part 55-62 summary)

All 8 questions **CLEAR** (§5 above). No PARTIAL/FAIL findings. The
system has exactly one mutating capability (request an investigation),
verified structurally, not by policy statement alone.

---

## 10. UX review (Part 8)

Conducted against a **genuinely fresh backend process** (zero
pre-seeded investigations — the actual state a cloned repo would be
in), not Phase 5B's already-warmed demo state. Screenshots taken this
session: `/tmp/phase6_fresh_overview.png`, `/tmp/phase6_fresh_queue.png`,
`/tmp/phase6_fresh_investigation_pre.png`, then after fixes:
`/tmp/phase6_fixed_overview.png`.

### P0 issues
**None found that survive this audit.** One finding (below) was
initially borderline P0/P1 and is now fixed.

### P1 issues found and fixed this phase

**Issue 1 — the product's core differentiator was invisible on the
first screen.** Risk Overview's only case table ("Recent Critical
Cases") showed 5/5 rows with "No Graph Evidence" on a fresh install,
because graph-flagged cases are rare (182/177,162 ≈ 0.1%) and the
CRITICAL ML tier has no correlation with graph flagging (quadrant D is
empirically empty, `docs/ML_GRAPH_ABLATION.md` §6). A judge skimming
only the two primary nav screens (Overview, Queue) in their default
state would see **zero evidence the graph feature does anything.**
**Fixed:** added a "Recent coordination-flagged cases" table to
Overview, now the second thing on the page. Verified visually
(`/tmp/phase6_fixed_overview.png`) — 5 real graph-flagged cases now
visible immediately.

**Issue 2 — unformatted large numbers.** `55648`, `117411` etc. read as
unpolished for a claimed "risk-operations console." **Fixed:**
`toLocaleString('en-IN')` formatting (`1,17,411`) applied to every
count on Overview and the Queue's pagination line.

Full before/after evidence, files changed, and risk assessment:
`docs/UX_IMPROVEMENT_PLAN.md`.

### P2/P3 issues found, deliberately NOT changed (per Part 15's change policy)

- `prefers-reduced-motion` not respected by loading animations (P2, accessibility nicety).
- Redundant "Start Investigation" button in two panels on Case Investigation (P3, contextually justified).
- Case Queue's own default view still shows mostly "No Graph Evidence"
  rows (P2) — deliberately left alone; artificially reordering a real
  analyst's queue to look more "interesting" for a demo would be
  dishonest about what the product actually does by default.
- `frontend/package.json` has no `engines` field (P3) — documented
  instead of constraining `npm install`.

### Q88-98 (UX-specific judge questions)

**Q88. Can a judge understand the product immediately?** Now yes for
the two primary screens (post-fix); the top-level README still requires
one extra click to the architecture doc for the full pipeline picture (§4). **WEAK → CLEAR (partially fixed)**

**Q89. Is Case Investigation the strongest screen?** Yes, by a wide
margin — confirmed via direct screenshot inspection (§10, pre-fix
screenshot already showed a complete, coherent story with zero changes
needed). **CLEAR**

**Q90. Can a judge see why ML missed something?** Yes, on Case
Investigation (always did) and now also on Overview (post-fix).
**Was WEAK, now CLEAR**

**Q91. Can a judge understand the graph?** Yes — typed, colored edges
with a legend, verified to correctly show multiple relationship types
between the same node pair without one color hiding another (a real
rendering bug found and fixed in Phase 5B, `docs/DEMO_FLOW.md` §4).
**CLEAR**

**Q92. Can a judge distinguish deterministic evidence from AI
interpretation?** Yes — solid-bordered cards (deterministic) vs.
dashed-bordered, AI-tinted blocks (interpretation), a rule stated as
"non-negotiable" in the design system and verified present in every
Case Investigation screenshot taken across Phases 5B/6. **CLEAR**

**Q93. Can a judge understand why the agent recommended an action?**
Yes — every recommendation sits directly below the AI's stated
evidence/conflicts/legitimate-explanations sections, in reading order. **CLEAR**

**Q94. Is human approval clearly required?** Yes — a literal
"HUMAN APPROVAL REQUIRED" badge, plus every UI-only action button
visibly disabled with an explanatory tooltip rather than hidden or
faked. **CLEAR**

**Q95. Are loading/error/failure states honest?** Yes — an
"Investigating…" state states realistic latency (no fake progress),
and a `validation_status="failed_human_review"` result renders as a
normal completed investigation, not a scary error banner, matching what
the backend actually did. **CLEAR**

**Q96. Are there unnecessary UI elements?** One minor redundancy noted
(P3, above); nothing rising to "unnecessary" at a product level — no
decorative charts, no chat-box AI interface (explicitly avoided per
`docs/FRONTEND_UX.md`). **CLEAR**

**Q97. Is there anything visually misleading?** The pre-fix Overview
page was arguably misleading by omission (§Issue 1) — not by false
statement, but by failing to show the one thing that most matters.
Fixed. **Was WEAK, now CLEAR**

**Q98. Does the product look like a real risk-operations system?**
Post number-formatting fix, yes — restrained, information-dense,
bordered (not shadowed) cards, semantic risk colors with icons+labels
(never color-alone), no emoji icons anywhere (verified via grep: zero
emoji characters in any `.tsx` file). **Was WEAK (unformatted numbers), now CLEAR**

---

## 11. Reproducibility (Part 7 summary)

Full detail: `docs/REPRODUCIBILITY_AUDIT.md`. Headline finding: 64% of
the backend suite and 100% of the frontend suite run immediately after
install; the remainder needs a previously-undocumented multi-script
sequence, now consolidated into `docs/DEVELOPMENT_RUNBOOK.md` this
session. Zero environment variables are required for anything to
install, build, or pass tests. Verified environment: Python 3.14.3,
Node v22.22.0, npm 10.9.4 (honestly stated as "tested on," not "required minimum").

---

## 12. "Why should I reject this?" (Part 12)

| Weakness | Category |
|---|---|
| Synthetic graph ground truth (no real-world abuse-ring labels exist to validate against) | **NOT FIXABLE WITH AVAILABLE DATA** — no public dataset has real cross-account collusion labels; disclosed explicitly (`ai_risk_manager_system_design.md` §35 Q5) |
| IEEE-CIS limitations (single dataset, single market's card-fraud patterns, not Razorpay's actual transaction mix) | **KNOWN LIMITATION** — stated in the design doc as a limitation up front, not discovered by a reviewer |
| Real-world generalization is unproven (ring precision/recall are true of *this* synthetic generator, not of Razorpay's real fraud population) | **KNOWN LIMITATION**, explicitly disclosed (`ai_risk_manager_system_design.md` §35 Q6) |
| Graph false positives exist (4.17% held-out, campus 100% at n=2) | **KNOWN LIMITATION**, honestly measured and reported, not hidden |
| Campus shared-infrastructure false positives specifically | **FIXABLE** in principle (extend detection to IP-range matching, not just exact value) — **not attempted this phase**, correctly, per the explicit instruction not to tune the detector in response to a held-out finding |
| Customer proxy limitations (not a validated 1:1 identity) | **NOT FIXABLE WITH AVAILABLE DATA** — IEEE-CIS provides no better identity signal; the least-misleading of 7 tested candidates was chosen and the limitation is carried through every downstream field via a confidence tier |
| LLM latency (~43s average) | **KNOWN LIMITATION**, architecturally addressed (async-safe request handling, caching) rather than hidden |
| Agent marginal value on some case types | **KNOWN LIMITATION**, self-disclosed in unusual detail (`docs/AGENT_EVALUATION.md` §5) |
| Lack of deployment | **NOT A GAP** — confirmed not required by the live Track 02 page (`docs/RAZORPAY_TRACK_02_COMPLIANCE.md`, deployment section) |
| Lack of authentication | **KNOWN LIMITATION**, explicitly out of scope by design (`docs/BACKEND_ARCHITECTURE.md` §10), appropriate for a hackathon submission with no deployment |
| Absence of real Razorpay data | **NOT FIXABLE WITH AVAILABLE DATA** — no such data was provided or accessible for this project |
| Benchmark size (8 rings, 100 legitimate clusters at full scale) | **KNOWN LIMITATION** — small absolute ring count means wide confidence intervals on some subcategories (campus n=2); disclosed, not smoothed over |
| Ring/`isFraud` independence (quadrant D empty — can't test whether coordination and real fraud correlate) | **NOT FIXABLE WITH AVAILABLE DATA** — a structural property of how the synthetic ground truth had to be constructed (Phase 1, Section 9's own design constraint), explicitly disclosed as a carried-forward limitation, not new |
| Reproducibility gap (undocumented setup sequence) | **ACTUAL DEFECT** — found and fixed this phase (§11) |
| Overview page didn't surface the product's differentiator | **ACTUAL DEFECT (UX)** — found and fixed this phase (§10) |

**Strongest single rejection argument, stated plainly:** *the ring
precision/recall numbers, however rigorously held-out, measure recovery
of a synthetic generator's own injected patterns — they say nothing
mathematically guaranteed about real-world abuse-ring prevalence or
Razorpay's actual fraud population, and no dataset exists that could
close that gap within a hackathon's constraints.* This is the correct,
honest, load-bearing weakness — everything else is either already fixed
or a disclosed, reasoned design trade-off.

---

## 13. "Why should I select this?" (Part 13)

- **A genuinely held-out graph evaluation exists, with a manifest and
  immutability check** — most hackathon submissions claiming "precision
  and recall on a held-out test set" have not actually verified their
  test set was never touched during tuning; this project found its own
  prior leakage and fixed it, on the record.
- **85.66% mean precision, 78.12% mean recall, 80.27% mean F1**,
  reported with 95% confidence intervals, by ring type, with the
  weakest category (campus, 100% FP at n=2) reported in the same table
  as the strongest — no cherry-picking.
- **ML + graph complementarity is measured, not asserted**: every
  single injected ring member had a LOW/MEDIUM ML tier (100% invisible
  to transaction-level scoring alone); the graph layer recovers a
  documented majority of them.
- **Defense-only by construction, not by policy statement** — one
  mutating route in the entire system, verified by an automated test
  that would fail on the addition of a second one.
- **Evidence-grounded agent**: every citation traced to a real tool
  call, invented evidence structurally rejected, proven with adversarial
  fake-client tests, not just happy-path tests.
- **Human approval is a hardcoded, validator-enforced invariant**, not
  a UI convention that a backend change could silently drop.
- **Honest hard-negative evaluation**: 100 legitimate shared-
  infrastructure clusters explicitly tested as an adversarial set, with
  a real (not zero) false-positive rate reported.
- **Real, live, end-to-end Claude execution demonstrated**, not just
  claimed — server logs and three-stage screenshots (before/during/after)
  of an actual browser click triggering an actual 44.3-second Claude
  Agent SDK call.
- **Reproducibility and engineering depth**: 264 automated tests (228
  backend + 36 frontend), typed cross-stack contracts, a provider-
  agnostic LLM abstraction, and — found by this very audit — the
  project's own habit of catching and fixing its own gaps rather than
  needing an external reviewer to find them first.

Not oversold: the campus false-positive result and the agent's marginal
value on some case types are both included above only implicitly (as
"honest reporting" strengths) — the actual weak numbers are in §12, not
hidden here.

---

## 14. Internal judge score (Part 11)

**INTERNAL JUDGE SIMULATION — not Razorpay's actual scoring rubric.**

| Category | Score /10 | Reason | Evidence | Weakness |
|---|---|---|---|---|
| Problem clarity | 8 | Scope-locked to one class of loss, stated plainly | `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §2 | Took until Phase 5C to formally lock the scope statement in the README |
| Track alignment | 9 | Directly matches a named example direction ("abuse-ring sentinel") | §17 fetched page text | None significant |
| Technical depth | 9 | Full pipeline, calibration, threshold policy, graph algorithms, agent safety, typed frontend | Whole repo | Some depth (GNN, Neo4j) is depth of *justified rejection*, not depth of *implementation* — legitimate but worth noting |
| ML quality | 7 | Real ablation (rules/LR/XGBoost), calibrated, threshold-policy-justified | `docs/ML_BASELINE.md`, `docs/RISK_THRESHOLD_POLICY.md` | PR-AUC 0.5207 is modest in absolute terms (disclosed, not hidden) |
| Graph innovation | 8 | Held-out ring-level evaluation with CIs is genuinely more rigorous than most hackathon graph work | `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §3-8 | Classical connected-components, not a novel algorithm — a deliberate, justified choice, not a limitation of ambition |
| Agent usefulness | 7 | Real value on some case types, honestly marginal on others | `docs/AGENT_EVALUATION.md` §5 | Marginal value on the majority-shape case category (single-attribute legitimate clusters) is a real, unresolved finding |
| Evaluation rigor | 9 | Manifest, immutability check, Wilson CIs, by-type breakdowns, no rounding | `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` | The residual same-real-transaction-pool caveat (§3) is minor but real |
| Honesty/transparency | 10 | Self-found leakage, self-disclosed weak results, self-found UX gap this very phase | Throughout | None found |
| UX | 7 (was 5 pre-fix) | Strong hero screen, honest states, now fixed first-screen differentiator visibility | §10 | P2 items remain (reduced-motion, queue default sparsity) |
| Reproducibility | 6 (was 4 pre-audit) | Deterministic seeds, zero required env vars, but the multi-script setup gap was real and only just documented | `docs/REPRODUCIBILITY_AUDIT.md` | Still no single `make reproduce-all` command — a doc, not a script |
| Security | 9 | Structurally defense-only, tested | `docs/DEFENSE_ONLY_AUDIT.md` | No authentication layer (correctly out of scope, still a real gap for any future deployment) |
| Demo readiness | 8 | Real Claude run demonstrated end-to-end with evidence, not just claimed | `docs/DEMO_FLOW.md` §5 | Demo depends on live Claude Code session availability (rate/session limits observed once already, Phase 4) |

**Total: 97/120 → normalized 80.8/100.**

Not artificially inflated: UX and Reproducibility both start from a
real deduction for gaps this same audit found, not a clean sweep.

---

## 15. Submission readiness

**PHASE 6 STATUS: PASS WITH UX CHANGES**

The project is submission-ready **for the "public repository" and
"architecture documentation" deliverables** right now. It is **not yet
pushed** (per explicit instruction), **has no pitch video** (explicitly
out of scope for this phase), and has **no deployment** (confirmed not required).

**Exact remaining work before a GitHub push:**
1. Nothing blocking — `scripts/pre_submission_check.py` passes clean.
2. Optional, not required: add the computed ~43s average latency figure
   to `docs/AGENT_EVALUATION.md` directly (currently only derivable, §Q52).
3. Optional, not required: inline a compact version of the
   `docs/ARCHITECTURE.md` diagram into `README.md` itself so Q4/Q9 are
   answerable without a second click (§4's only two "not fully obvious
   in 30s" findings).

Neither optional item blocks a push; both are P2 polish, consistent
with Part 15's change policy already applied throughout this phase.
