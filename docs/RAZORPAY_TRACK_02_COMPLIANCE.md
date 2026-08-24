# Razorpay AI Buildathon — Track 02 Compliance — Phase 5C

**Track:** Track 02 — AI Risk Manager
**Selected direction:** Abuse-Ring Sentinel → **Coordinated Payment Fraud / Abuse-Ring Detection**
**Source of truth:** `https://razorpay.com/buildathon/`, fetched directly on 2026-08-24
(Requirement 17 — see §17 for the exact fetched text and confirmation
that this checklist matches the live page, not just this prompt).

---

## 1. Working detector

**1. Requirement:** Prove the system is a working, end-to-end detector for coordinated payment fraud / abuse rings.

**2. Razorpay wording:** *"Build a working detector, verifier or auto-responder for one class of loss, with measured precision and recall on a held-out test set."*

**3. Our implementation:** A real, executable pipeline —
```
Real transaction (IEEE-CIS)
  → ML risk scoring (frozen XGBoost + isotonic calibration, src/models/)
  → Graph construction (device/IP/bank_account relationship views, src/graph/relationship_views.py)
  → Multi-attribute coordination detection (connected components, community_size>=3, src/graph/signals.py)
  → Case generation (src/graph/case_interface.py::build_case)
  → Investigation (LangGraph + Claude, src/agents/graph.py)
```
Every stage is real code that runs — not a frontend mockup.

**4. Evidence / file / test / metric — exact commands, exact input, exact output:**

```bash
# 1. Generate the synthetic coordinated-abuse benchmark (full scale, 590,540 real rows)
python -m scripts.generate_full_benchmark
# 2. Score ML risk (frozen model, val/test split only)
python -m scripts.score_val_test_for_graph_fusion
# 3. ML + graph ablation over the full benchmark
python -m scripts.ml_graph_ablation
# 4. Held-out Track 02 evaluation (this phase's new, independent test set)
python -m scripts.generate_holdout_benchmark
python -m scripts.run_track02_evaluation
# 5. Live end-to-end case investigation (real Claude)
RISK_MANAGER_LLM_BACKEND=claude_agent_sdk uvicorn src.api.main:app
curl -X POST http://127.0.0.1:8000/api/v1/cases/investigate \
  -H "Content-Type: application/json" -d '{"case_id": "CASE-3457202"}'
```
**Reproducible demo case:** `CASE-3457202` (transaction 3457202, `ml_low_graph_high` — ML score 1.1%/MEDIUM tier alone, graph flags a 4-member community sharing one bank account). Full real run already executed and recorded: `docs/DEMO_FLOW.md` §5 — real Claude, `agent_duration_ms=44304`, `validation_status="passed"`, full report with real evidence/policy citations, no stub markers. `data/processed/track02_holdout_evaluation_report.json` is the detector-only (no LLM) reproducible output for §3-6 below.

**5. Status:** **PASS**

**6. Remaining gap:** None.

---

## 2. One class of loss

**1. Requirement:** Lock the claimed scope to exactly one class of loss.

**2. Razorpay wording:** Example directions include *"chargeback evidence responder, return-risk scorer, fraud-spike detector, abuse-ring sentinel."*

**3. Our implementation:** The measured, claimed detector target is **coordinated payment fraud / abuse-ring activity** — full stop. We do **not** claim to solve returns, chargebacks, or generic/all merchant fraud. The XGBoost transaction-risk model exists only as supporting context feeding the graph layer's case-triage input (Requirement 11) — it is explicitly not the measured detector for Track 02 purposes; its own separate ML-only metrics (`docs/ML_BASELINE.md`) are development context, not the Track 02 headline numbers.

**4. Evidence / file / test / metric:** `README.md`'s opening scope statement; this document's title and every metric in §3-7 below is scoped to ring/cluster recovery, never a generic "fraud caught" number. Grepped the entire repo for `returns`/`chargeback` language (§9 below) — zero instances claim either capability.

**5. Status:** **PASS**

**6. Remaining gap:** None.

---

## 3. Held-out test set

**1. Requirement:** A formally held-out test evaluation for the graph detector — configuration frozen *before* the held-out test is touched.

**2. Razorpay wording:** *"...with measured precision and recall on a held-out test set."*

**3. Our implementation — the gap we found and closed:**

`data/synthetic/full/` (the existing Phase 1-3 "full benchmark," seed 42) was **not** a valid held-out set: `scripts/graph_benchmark_full.py` grid-searches 3 weighting strategies × 2 community-detection methods **against this exact dataset**, and `docs/GRAPH_BENCHMARK_FULL.md` §6 explicitly derives the "frozen configuration" (multi-attribute view, flat weighting, connected components) from those results. Reporting numbers computed on that same dataset as "held-out" would be leakage — the config was chosen by looking at outcomes on it.

**Fix (this phase, evaluation infrastructure only — the detector itself, `src/graph/*`, `src/generator/*`, is untouched):**

```
DEVELOPMENT / TRAINING  →  data/synthetic/dev/   (seed 42, 20,000 rows, Phase 1)
VALIDATION              →  data/synthetic/full/  (seed 42, 590,540 rows, Phase 3 — used for the weighting/view grid search)
FREEZE CONFIGURATION    →  docs/GRAPH_BENCHMARK_FULL.md §6 (already committed, unmodified this phase)
HELD-OUT TEST           →  data/synthetic/holdout_test/  (seed 20260824, generated THIS phase, NEW)
FINAL METRICS           →  data/processed/track02_holdout_evaluation_report.json
```

**A. Real IEEE-CIS fraud evaluation** (the `isFraud` column) is entirely separate — `docs/ML_BASELINE.md` — and is never conflated with:

**B. Synthetic coordinated-abuse detection evaluation** — this section. `original_isFraud` has zero relationship to injected ring/cluster labels (`docs/CASE_MODEL.md` §1, `docs/SYNTHETIC_DATA_GENERATION.md` §5).

**Held-out generation protocol** (`scripts/generate_holdout_benchmark.py`):
- **Seed:** `20260824` — verified via `git grep` (see below) to have never been used in any prior generator run, weighting comparison, or threshold decision in this project's history. (Seed 42 = all dev/validation/design work. Seed 99 = used only in two small unit-test sanity checks on a tiny in-memory sample — `tests/integration/test_graph_percolation_fixed.py`, `tests/integration/test_reproducibility.py` — never for benchmark generation or any design decision.)
- **Generation protocol:** identical, unmodified `src/generator/pipeline.py::run_generator` + `GeneratorConfig()` the frozen/validated benchmark used — same real 590,540 IEEE-CIS rows, same `configs/generator.yaml` counts/rules, only the seed differs (this is what makes it independent, not a different generator).
- **Development portion:** `data/synthetic/dev/` (20,000 rows, seed 42) — used to design the generator itself (Phase 1).
- **Validation portion:** `data/synthetic/full/` (590,540 rows, seed 42) — used to select view/weighting/community-method (Phase 3).
- **Held-out test portion:** `data/synthetic/holdout_test/` (590,540 rows, seed 20260824) — generated once, this phase, never inspected before scoring.
- **Ring counts/types/sizes (held-out):** 8 rings — 3 `shared_device`, 3 `shared_bank_account`, 2 `multi_attribute`; sizes drawn from the same configured 3-8/4-8 ranges as every prior run (`configs/generator.yaml`, unmodified).
- **Legitimate hard negatives (held-out):** 100 clusters — 60 household, 20 office, 15 business, 5 campus (unmodified counts).
- **No entity/ring-ID overlap between splits:** every ring/cluster ID and every `customer_proxy_id` is freshly derived from `(seed, TransactionID, role)` via `src/generator/rng.py::derive_seed` (SHA-256-based, deterministic, seed-dependent) — a different seed structurally cannot reproduce the same `customer_proxy_id` or ring/cluster ID assignment as seed 42's run (verified generally by `tests/integration/test_reproducibility.py::test_different_seed_produces_different_assignment`; specifically for this held-out run, the printed ring/cluster IDs in `data/synthetic/holdout_test/rings.json`/`legitimate_clusters.json` use the same `RING-*-NNN`/`LEGIT-*-NNN` naming scheme but represent entirely different underlying transactions/customers than the seed-42 run, since the anchor-transaction selection itself is seed-derived).
- **Same-structural-pattern-in-all-splits risk, addressed:** the *pattern types* (household/office/campus/business/shared_device/shared_bank_account/multi_attribute) are necessarily the same across splits — that's intentional (Requirement 4/5 asks for precision/recall *by ring type*, which requires the held-out set to contain the same taxonomy). What differs, and what actually matters for leakage, is *which specific transactions/customers* instantiate each pattern — confirmed disjoint by construction (different seed → different SHA-256-derived selection).

**5. Status:** **PASS**

**6. Remaining gap:** None. (A genuine, if minor, residual note: both splits draw from the identical 590,540-row real transaction pool, so in principle the *same real transaction* could be selected as an anchor by both seed-42 and seed-20260824 runs by pure chance — checked: seed-derived anchor selection makes this astronomically unlikely at these injection densities (8 rings among 156,316 customers) and does not construct any correlated structure even if it happened once, since ring/cluster membership and shared-attribute values are independently re-derived per seed regardless of which transaction is the anchor.)

---

## 4. Precision

**1. Requirement:** Final held-out-test precision, overall and by ring type, with 95% CI, predicted positives, true positives, false positives.

**2. Razorpay wording:** *"...with measured precision and recall..."*

**3. Our implementation:** Computed by `scripts/run_track02_evaluation.py` Step 5, entirely deterministic (no LLM), against `data/synthetic/holdout_test/` only.

**4. Evidence / file / test / metric** (full detail: `data/processed/track02_holdout_evaluation_report.json`):

| | Overall | `shared_device` | `shared_bank_account` | `multi_attribute` |
|---|---|---|---|---|
| Mean precision (per-ring) | **0.8566** | 0.7843 | 0.9167 | 0.8750 |
| Pooled precision (member-level) | 33/46 members = **0.7174** | — | — | — |
| Pooled precision 95% CI | **[0.5745, 0.8268]** | — | — | — |
| Rings scored | 8 | 3 | 3 | 2 |

Member-level pooled counts (`ring_recovery.member_level_pooled` in the report): **predicted positive members = 46, true positive members = 33, false positive members = 13** (extra non-ring customers swept into a ring's detected community — a mechanism the generator's decoys/incidental overlap are designed to test, `docs/SYNTHETIC_DATA_GENERATION.md` §4).

No aggressive rounding — 4 decimal places throughout the JSON report; this document quotes them exactly as computed.

**5. Status:** **PASS**

**6. Remaining gap:** None. Per-ring-type precision is reported for all 3 types, including `shared_device`'s comparatively lower 0.7843 — not hidden.

---

## 5. Recall

**1. Requirement:** Final held-out-test recall, overall and by ring type, with 95% CI, true positives, false negatives, missed rings, partially recovered rings.

**2. Razorpay wording:** *(same as §4)*

**3. Our implementation:** Same script/run as §4.

**4. Evidence / file / test / metric:**

| | Overall | `shared_device` | `shared_bank_account` | `multi_attribute` |
|---|---|---|---|---|
| Mean recall (per-ring) | **0.7812** | 0.7778 | 0.8055 | 0.7500 |
| Pooled recall (member-level) | 33/42 = **0.7857** | — | — | — |
| Pooled recall 95% CI | **[0.6406, 0.8829]** | — | — | — |
| Missed rings | **0** | 0 | 0 | 0 |
| Partially recovered rings | **8 (all)** | 3 | 3 | 2 |
| Fully recovered rings | 0 | 0 | 0 | 0 |

**No ring was missed entirely; no ring was perfectly recovered either — every ring is "partial," by design.** `noise_ratio` (0.15-0.2, `configs/generator.yaml`) deliberately leaves that fraction of each ring's members without the shared synthetic attribute, modeling an evasive participant — a `1 - noise_ratio` recall ceiling exists structurally, documented since `docs/GRAPH_BENCHMARK.md` §9, and holds again here on genuinely independent held-out data.

**5. Status:** **PASS**

**6. Remaining gap:** None. `shared_device`'s 0.7778 (lowest of the three) is reported, not hidden.

---

## 6. F1

**1. Requirement:** F1 as a supporting metric, not a replacement for precision/recall.

**3. Our implementation / 4. Evidence:**

| | Overall | `shared_device` | `shared_bank_account` | `multi_attribute` |
|---|---|---|---|---|
| Mean F1 | **0.8027** | 0.7487 | 0.8561 | 0.8035 |

`data/processed/track02_holdout_evaluation_report.json::ring_recovery.overall.mean_f1` and `.by_abuse_type.*.mean_f1`.

**5. Status:** **PASS**

**6. Remaining gap:** None.

---

## 7. False-positive cost

**1. Requirement:** An explicit false-positive cost framework for the coordinated-abuse detector, using hard negatives, clearly labeled illustrative.

**2. Razorpay wording:** *"Honest metrics including false-positive cost."*

**3. Our implementation:** `src/evaluation/track02_cost.py`. **False positive = legitimate shared infrastructure (household/office/campus/business) incorrectly flagged as coordinated abuse** — exactly Track 02's stated definition, operationalized as: a legitimate cluster whose detected community also contains a ring member (`src/graph/ring_recovery.py::evaluate_legitimate_false_positives`, unmodified this phase).

**4. Evidence / file / test / metric** — held-out test results:

| Cluster type | Scored | False positives | FP rate | 95% CI |
|---|---|---|---|---|
| Household | 41 | 0 | **0.0%** | [0.0%, 8.6%] |
| Office | 19 | 1 | **5.3%** | [0.9%, 24.6%] |
| Business | 10 | 0 | **0.0%** | [0.0%, 27.8%] |
| Campus | 2 | 2 | **100.0%** | [34.2%, 100.0%] |
| **Overall** | **72** | **3** | **4.17%** | **[1.43%, 11.55%]** |

**Not hidden: campus scored 100% false-positive on this held-out run** (2 of 2 scored clusters), a genuinely different, worse result than the Phase 3 full-benchmark's "0% campus FP, n=1" — this is exactly the kind of result a real held-out test is supposed to be able to surface, and per Requirement 3/7's explicit instruction, **the detector was not modified in response to this finding.** Root cause (documented, not fixed): campus clusters' primary sharing mechanism is an IP-*range* prefix (`docs/SYNTHETIC_DATA_GENERATION.md` §3), which the multi-attribute exact-value view doesn't track directly — on the rare occasion a campus cluster *also* incidentally shares an exact device/IP/bank value with a ring member (ambient leakage, `docs/SYNTHETIC_DATA_GENERATION.md` §2), it contaminates. At only 2 scored campus clusters, this is a small-sample result (wide CI, [34.2%, 100.0%]) — reported honestly as low-confidence, not as a stable rate.

**ILLUSTRATIVE COST MODEL — not Razorpay's real internal cost:**
- Cost per false-positive investigation: **₹500** (reused from the existing ML-layer illustrative cost, `src/evaluation/cost.py`, for consistency — "analyst investigation time + customer friction," an assumption, not a measured figure)
- False-positive clusters: **3**
- False-positive transactions: **104** (actual transaction rows belonging to the 3 FP clusters' members, held-out data)
- **Total illustrative FP cost: ₹1,500**

**5. Status:** **PASS**

**6. Remaining gap:** None for compliance purposes. Campus's small sample size (n=2) is a known, stated limitation of the injection density, not a compliance gap — Requirement 7 asks for honest reporting, which this provides in full, including the uncomfortable number.

---

## 8. Honest metrics (final table)

**1. Requirement:** One final metrics table, not collapsed into an arbitrary overall score.

**3. Our implementation / 4. Evidence:**

| Metric | Value |
|---|---|
| Precision (mean, per-ring) | 0.8566 |
| Precision (pooled, member-level) | 0.7174 (95% CI [0.5745, 0.8268]) |
| Recall (mean, per-ring) | 0.7812 |
| Recall (pooled, member-level) | 33/42 = 0.7857 (95% CI [0.6406, 0.8829]) |
| F1 (mean, per-ring) | 0.8027 |
| False-positive rate (hard negatives) | 4.17% (95% CI [1.43%, 11.55%]) |
| False-positive cost (illustrative) | ₹1,500 (3 clusters × ₹500) |
| Held-out test size | 590,540 real transactions, seed 20260824 |
| Ring (positive) population | 8 rings, 50 ring-member rows (41 core + 9 noise) |
| Hard-negative population | 100 legitimate clusters, 72 scored (present in the detection view) |
| Missed / partial / full rings | 0 / 8 / 0 |

Full JSON: `data/processed/track02_holdout_evaluation_report.json`.

**5. Status:** **PASS**

**6. Remaining gap:** None.

---

## 9. Real data vs. synthetic ground truth

**1. Requirement:** Precise, non-conflating language.

**3. Our implementation:** Every evaluation script, report, and doc in this project states the distinction explicitly:
- **IEEE-CIS: REAL TRANSACTION DATA** — `TransactionID`, `TransactionDT`, `TransactionAmt`, `isFraud`, etc.
- **Synthetic layer: CONTROLLED COORDINATION STRUCTURES** — `customer_proxy_id`, device/IP/bank/address proxies, legitimate clusters, rings.
- **Synthetic labels: EVALUATION GROUND TRUTH** — `synthetic_ring_id`, `synthetic_entity_label`, etc. — used only to score the detector, never fed to it.

`scripts/run_track02_evaluation.py`'s output report includes a `real_vs_synthetic_disclaimer` field verbatim in every generated report (not just this document) — see the JSON.

**4. Evidence / file / test / metric:** Grepped the full repo (`docs/`, `README.md`, `src/`, `scripts/`) for risky phrasing patterns (`"% of real fraud"`, `"real fraud detected"`) — **zero matches**. `docs/CASE_MODEL.md` §1 structurally separates `Case` (production) from `CaseGroundTruth` (evaluation-only) so this distinction is enforced in code, not just prose.

**5. Status:** **PASS**

**6. Remaining gap:** None.

---

## 10. Defense only

**1. Requirement:** Verify and document that the system cannot take an offensive action.

**3. Our implementation:** Full dedicated audit — `docs/DEFENSE_ONLY_AUDIT.md`.

**4. Evidence / file / test / metric:** `tests/unit/test_defense_only_audit.py` (5 tests, all passing): exactly one mutating API route exists (`POST /investigate`); every tool is read-only by name; `human_approval_required_for_action=False` is structurally rejected; a full static scan of `src/` finds zero offensive/write-capable code patterns; the output schema has no action-execution field.

**5. Status:** **PASS**

**6. Remaining gap:** None.

---

## 11. Working AI

**1. Requirement:** Demonstrate meaningful AI/ML use; the core detector must work without the LLM.

**3. Our implementation — what each component contributes:**

| Component | Contribution | Works without the others? |
|---|---|---|
| **XGBoost** (`src/models/`) | Per-transaction risk score/tier from real IEEE-CIS features — supporting context, not the measured detector (§2) | Yes — fully independent of graph/LLM |
| **Graph analytics** (`src/graph/`) | The **primary coordinated-abuse detector** — structural relationship discovery ML cannot see | Yes — `scripts/run_track02_evaluation.py` computes every §3-8 metric with **zero LLM calls** |
| **LangGraph** (`src/agents/graph.py`) | Deterministic orchestration of evidence-gathering tool calls around a case | Runs the same whether the LLM is `StubLLMClient` or real Claude — orchestration itself is not AI |
| **Claude investigation** (`src/agents/llm_client.py`) | Synthesizes already-deterministic evidence into a cited narrative, surfaces conflicts/legitimate explanations, cites policy — real reasoning, verified live (`docs/DEMO_FLOW.md` §5, 44.3s real call, no stub markers) | This is the one genuinely AI-only layer — by design, since it's synthesis, not detection |

**"AI" is not claimed merely because an LLM is present** — the detector (§1-8's measured precision/recall/F1) never invokes Claude at all, verified directly: `scripts/run_track02_evaluation.py` imports nothing from `src.agents.llm_client`.

**4. Evidence / file / test / metric:** `docs/ARCHITECTURE.md` (labeled diagram); `docs/AGENT_ARCHITECTURE.md`; `data/processed/track02_holdout_evaluation_report.json` (produced with zero LLM involvement, timestamped independent of any Claude call).

**5. Status:** **PASS**

**6. Remaining gap:** None.

---

## 12. Agent must not cheat the metrics

**1. Requirement:** The LLM never receives ground truth, never determines evaluation labels, never changes detector output/threshold, cannot manufacture graph evidence or citations.

**3. Our implementation / 4. Evidence:**

| Check | Evidence |
|---|---|
| LLM never receives ground truth | `AgentInput`'s only constructor is `build_agent_input(case: Case)` — `CaseGroundTruth` is never importable into the agent's input path (`docs/CASE_MODEL.md` §1, structurally, not conventionally) |
| LLM never determines evaluation labels | `scripts/run_track02_evaluation.py` never touches `src.agents` at all — the held-out precision/recall/F1 numbers are 100% pre-LLM |
| LLM never changes detector output/risk threshold | The final report's `risk_tier` is always `case.ml_risk_tier` verbatim, never the LLM's own field in isolation — proven exactly across all 4 tiers, `tests/integration/test_agent_investigation_pipeline.py::test_risk_tier_in_final_report_matches_frozen_ml_tier_exactly` |
| LLM cannot manufacture graph evidence | Graph evidence (`GraphEvidence`) is computed once, deterministically, before the agent ever runs (`src/graph/case_interface.py::build_case`) — the agent only ever *reports* it |
| LLM cannot manufacture citations | Every `evidence_id` cited in a report is checked against the actual tool-call log for that investigation; an invented ID fails deterministic validation (`docs/SAFETY_MODEL.md` §3, `tests/unit/test_agent_safety.py::test_invented_evidence_id_fails_validation`) |

**5. Status:** **PASS**

**6. Remaining gap:** None.

---

## 13. Held-out test immutability

**1. Requirement:** A manifest (config hash, generator config hash, seed, graph config, threshold, weighting, evaluation version) created after freezing, before the held-out test runs; invalidate and rerun on any config change.

**3. Our implementation:** `src/evaluation/track02_manifest.py::compute_frozen_config_manifest()` — hashes every source file that determines detector behavior (`src/generator/*`, `src/graph/relationship_views.py`/`ring_recovery.py`/`signals.py`/`build_graph.py`, `configs/generator.yaml`, `configs/seed.yaml`) plus the explicit frozen parameter values (view, weighting, community method, `graph_flag_min_community_size`), combined into one `combined_config_hash`, plus the current git commit for provenance. `scripts/run_track02_evaluation.py` also separately manifests the held-out **test-set** files themselves (`data/processed/track02_holdout_test_manifest.json`) — on first run it records file hashes; on every subsequent run it recomputes and **fails hard** if the held-out files changed without an explicit new manifest, rather than silently re-scoring different data under the old result's name.

**4. Evidence / file / test / metric:**
```
combined_config_hash = d8f89b68bfd160e8f43df2fd20316d08a645f1abccd75de066a96684699b3a38
git_commit           = 4c5be06d1d0e2c44b6a599f142a2cf082ddeea57
```
Verified by running `scripts/run_track02_evaluation.py` twice in immediate succession: second run printed *"OK: held-out benchmark matches the previously recorded manifest (unchanged since first freeze)"* rather than re-freezing.

**5. Status:** **PASS**

**6. Remaining gap:** None.

---

## 14. Reproducibility

**1. Requirement:** `scripts/run_track02_evaluation.py`, verifying inputs/config/manifest, running the detector, computing metrics + FP cost, outputting a final report — no silent restricted-data download.

**3. Our implementation:** Exactly this script, exactly these 7 steps (printed at each step, §1's exact commands). `step1_verify_inputs()` **exits with a clear message** (never attempts a download) if `data/raw/train_transaction.csv` is absent.

**4. Evidence / file / test / metric:** `scripts/run_track02_evaluation.py`; live-run transcript (§3-7 above) — every number in this document was read directly from that script's actual output and `data/processed/track02_holdout_evaluation_report.json`, not computed by hand or estimated.

**5. Status:** **PASS**

**6. Remaining gap:** None.

---

## 15. Public repository readiness

**1. Requirement:** No raw IEEE-CIS files, API keys, credentials, secrets, local paths, private/generated-restricted artifacts, or unnecessary large binaries tracked by git.

**3. Our implementation:** `scripts/pre_submission_check.py` — scans exactly `git ls-files` (what would actually be pushed) for raw dataset filenames, any tracked file under `data/`, `.env` files, tracked files >2MB, and secret/local-path-shaped strings in every text file.

**4. Evidence / file / test / metric:**
```
$ python -m scripts.pre_submission_check
Scanning 246 git-tracked files...

PASS — no raw dataset files, no tracked data/ artifacts, no .env files,
no oversized files, no secret-shaped strings, no local machine paths found
in any git-tracked file.
```
`.gitignore` already excludes `data/raw/*`, `data/synthetic/*`, `data/processed/*` (including this phase's new `holdout_test/` and `track02_*.json` outputs — verified: `git status --short data/` shows nothing new tracked after generating them). Largest tracked file: `frontend/package-lock.json` at 88KB.

**5. Status:** **PASS**

**6. Remaining gap:** One untracked, pre-existing stray file (`data/test_identity.textClipping`, a macOS drag-and-drop clipping, harmless, never staged) sits in the working directory — not a git risk (it's not tracked and never has been), noted here only for full transparency, not a compliance gap.

---

## 16. Architecture

**1. Requirement:** One clear, honestly-labeled architecture diagram (REAL/DERIVED/SYNTHETIC/AI/DETERMINISTIC/HUMAN).

**3. Our implementation / 4. Evidence:** `docs/ARCHITECTURE.md` — full labeled pipeline diagram plus a "where each stage is proven" evidence table.

**5. Status:** **PASS**

**6. Remaining gap:** None.

---

## 17. Current Razorpay requirement audit

**1. Requirement:** Re-read the live official page; do not rely solely on this prompt; STOP and report any new explicit requirement found.

**3. Our implementation:** Fetched `https://razorpay.com/buildathon/` directly (not from training-data memory, not from the prompt) on 2026-08-24. Full fetched text for Track 02 and general submission requirements:

> **Tagline:** "Stop the merchant losing money to fraud, returns and chargebacks."
> **Core Requirement:** "Build a working detector, verifier or auto-responder for one class of loss, with measured precision and recall on a held-out test set."
> **Why Now:** "AI-enabled fraud is hitting Indian BFSI while returns and chargebacks quietly eat margin. This track surfaces the risk and ML minded builders the others miss."
> **Example Directions:** Chargeback evidence responder · Return-risk scorer · Fraud-spike detector · Abuse-ring sentinel
> **The Bar:** "Honest metrics including false-positive cost. Strictly defense-only: anything offense-capable is disqualified."
> **General Submission Requirements (all tracks):** Public repository · 5-minute pitch video · Architecture documentation · No resume screening or aptitude tests · Shortlisted builders go to panel interview only.
> **The Offer:** ₹75,000 monthly stipend, 6- or 12-month duration, in-person in Bangalore from September.

**4. Evidence / file / test / metric:** Live WebFetch of the official page, this session, cross-checked against a live WebSearch summary — both agree verbatim with each other and with the requirements this checklist was already built against.

**No new explicit Track 02 requirement was discovered.** Nothing here was not already covered by items 1-16. **No STOP was triggered.**

**5. Status:** **PASS**

**6. Remaining gap:** None. (General submission items — public repo, pitch video, architecture doc — are explicitly out of scope for Phase 5C per your own instruction, "those happen AFTER compliance is complete"; architecture documentation itself is already satisfied, §16.)

---

## Deployment

**No live URL / deployment requirement exists anywhere in the fetched official page or the general submission requirements** (§17's verbatim quote is exhaustive — "Public repository, 5-minute pitch video, Architecture documentation" is the complete general-submission list; no track-specific deployment requirement exists for Track 02 either).

**DEPLOYMENT: NOT REQUIRED.** No deployment infrastructure was introduced this phase, per the explicit instruction not to invent this requirement.

---

## Final compliance table

| # | Requirement | Evidence | Status |
|---|---|---|---|
| 1 | Working detector, end-to-end | `docs/RAZORPAY_TRACK_02_COMPLIANCE.md` §1; `data/processed/track02_holdout_evaluation_report.json`; `docs/DEMO_FLOW.md` §5 | **PASS** |
| 2 | One class of loss (coordinated abuse) | §2; README scope statement | **PASS** |
| 3 | Held-out test set (genuinely independent) | §3; `scripts/generate_holdout_benchmark.py`; `data/synthetic/holdout_test/` | **PASS** |
| 4 | Precision (overall + by ring type, 95% CI) | §4; `data/processed/track02_holdout_evaluation_report.json` | **PASS** |
| 5 | Recall (overall + by ring type, 95% CI) | §5; same report | **PASS** |
| 6 | F1 | §6; same report | **PASS** |
| 7 | False-positive cost (illustrative, hard negatives) | §7; `src/evaluation/track02_cost.py` | **PASS** |
| 8 | Honest metrics (no collapsed score) | §8 | **PASS** |
| 9 | Real vs. synthetic language | §9; `docs/CASE_MODEL.md` | **PASS** |
| 10 | Defense only | §10; `docs/DEFENSE_ONLY_AUDIT.md`; `tests/unit/test_defense_only_audit.py` | **PASS** |
| 11 | Working AI (detector works without LLM) | §11; `docs/ARCHITECTURE.md` | **PASS** |
| 12 | Agent cannot cheat the metrics | §12; Phase 4 safety tests | **PASS** |
| 13 | Held-out test immutability (manifest) | §13; `src/evaluation/track02_manifest.py` | **PASS** |
| 14 | Reproducibility (`run_track02_evaluation.py`) | §14 | **PASS** |
| 15 | Public repository readiness | §15; `scripts/pre_submission_check.py` | **PASS** |
| 16 | Architecture diagram | §16; `docs/ARCHITECTURE.md` | **PASS** |
| 17 | Current requirement re-audit | §17 | **PASS** |
| — | Deployment | Not required, per §17's live page text | **NOT REQUIRED** |

**No item is PARTIAL, FAIL, or UNKNOWN.**
