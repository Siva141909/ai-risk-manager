# ML + Graph Ablation — Phase 3H/3I/3J

**Central question:** does graph-based coordinated-risk analysis add
measurable value beyond transaction-level ML? Tested empirically, not
assumed. **The honest answer has two parts that must not be collapsed
into one number** — see §4.

**Method:** `scripts/ml_graph_ablation.py`, run against **validation +
test only** (177,162 rows) — the Phase 2 XGBoost model was fit on train,
so a "score" on a train row would be in-sample and not a fair test of
anything; train rows are excluded from this entire analysis, not scored
at all. **The Phase 2 model itself was not retrained, retuned, or
modified in any way** — the explicit Phase 3 experimental rule. Full
output: `data/processed/ml_graph_ablation_report.json`.

**Not the same measurement as the Track 02 held-out ring-recovery
metrics (Phase 6 clarification, no numbers below changed):** §4's 84%
is a *transaction-level* statistic — of ring-member transactions in the
validation+test split (seed 42, the design/validation benchmark), what
fraction were also `graph_flagged=True`. `docs/RAZORPAY_TRACK_02_COMPLIANCE.md`
§4/§5 reports a different, *ring-level* statistic (precision/recall of
recovering each of 8 whole rings) on a genuinely separate, independent
held-out benchmark (seed 20260824). Both are honest, correctly-computed
numbers about the same detector — they are not comparable line items
and neither supersedes the other; a reader citing "the recall of the
graph detector" should specify which of the two questions they mean.

---

## 1. The three stages

| Stage | Flagging rule |
|---|---|
| **A. Rules only** | `src/models/baseline_rules.py`, thresholds fit on TRAIN (Phase 2B, unchanged) |
| **B. Rules + ML** | A **OR** `ml_risk_tier ∈ {HIGH, CRITICAL}` (frozen Phase 2 thresholds, unchanged) |
| **C. Rules + ML + Graph** | B **OR** `graph_flagged` (community_size ≥ 3 in the frozen multi-attribute view, `docs/GRAPH_BENCHMARK_FULL.md` §6) |

---

## 2. Transaction-level metrics (against real `isFraud`)

| Stage | Precision | Recall | F1 | PR-AUC | Cases generated | Est. workload (₹) |
|---|---|---|---|---|---|---|
| A. Rules only | 0.0368 | 0.6160 | 0.0694 | n/a (no continuous score) | 102,659 | 15,398,850 |
| B. Rules + ML | 0.0462 | 0.7868 | 0.0873 | 0.5207 | 104,258 | 15,638,700 |
| **C. Rules + ML + Graph** | **0.0462** | **0.7868** | **0.0873** | **0.5207** | 104,330 | 15,649,500 |

**Adding graph changes NOTHING measurable at the transaction/`isFraud`
level** — same precision, recall, F1, PR-AUC to 4 decimal places. The
only difference is 72 additional flagged transactions (§3).

**PR-AUC is identical between B and C by construction, not by
coincidence or a bug:** graph contributes a discrete community-
membership flag, not a continuous ranking score, so it structurally
cannot move a rank-based metric — noted explicitly rather than
manufacturing a fake blended score to make PR-AUC "move" (which Phase 3H
explicitly forbids: "do not combine unrelated metrics into one arbitrary
score").

## 3. Incremental contribution of graph (Stage C vs. Stage B)

| | Count |
|---|---|
| Additional transactions flagged | 72 |
| Additional **real** fraud (`isFraud=1`) caught | **0** |
| Additional false positives | 72 |

**At face value, this looks like graph adds zero value and pure cost.
That reading is incomplete — see §4.**

---

## 4. Why the transaction-level result is expected, not a failure — and what the graph actually catches

**The synthetic ring labels are constructed independently of real
`isFraud`** (design doc Section 9, Phase 1 Ground Truth Strategy) — ring
membership tests whether coordinated-structure detection *works
mechanically*, not whether it correlates with this specific dataset's
real fraud label. Given that independence by construction, **zero
additional real-fraud recall from graph fusion is the expected result,
not evidence the graph layer is broken.** Reporting only §2/§3 without
this context would be misleading in the other direction — implying
"graph adds nothing" when what's actually true is "graph answers a
different question than `isFraud` measures."

**The question graph fusion actually needs to answer: can it recover
coordinated structure that ML, which has no access to any graph
information, structurally cannot?**

| | Count |
|---|---|
| Ring-member transactions in validation+test | 25 |
| ...with `ml_risk_tier` LOW/MEDIUM (ML did not flag them) | 25 (100%) |
| ...of those, also `graph_flagged=True` (graph caught them) | **21 (84%)** |
| ...NOT graph-flagged (noise members — deliberately unconnected) | 4 (16%) |

**Every single ring-member transaction in validation+test had a LOW/MEDIUM
ML tier** — confirming ML has literally zero mechanism to see ring
membership (expected: it was never given graph features, Phase 3's
architectural rule). **The graph layer recovers 84% of them** — the 16%
miss is not a graph failure, it's the `noise_ratio` mechanism working as
designed (noise members deliberately don't share the synthetic
attribute, so they are structurally invisible to ANY attribute-sharing
graph, correctly).

**This is the actual test of the central hypothesis, and it is
confirmed:** "transaction-level ML... alone" has 0% capability to detect
this class of coordinated structure (by construction — it was given no
graph signal). "Graph-based coordinated-risk analysis" recovers 84% of
the structurally-recoverable cases. The two layers are not redundant —
they answer different questions (design doc Section 1: "ML answers 'how
risky is this transaction,' graph answers 'is this transaction part of
something bigger'"), and §2's flat transaction-level ablation table
obscures this because it forces both questions through one metric
(`isFraud` recall) that only one of the two layers was ever trying to
answer.

**One concrete worked example** (full detail `docs/CASE_MODEL.md` §4):
transaction `3457202` — `ml_risk_score=0.011` (very low), `isFraud=0`
(not real fraud) — yet it is a core member of `RING-SHARED_BANK_ACCOUNT-000`.
Transaction-level scoring correctly sees nothing wrong with this
transaction in isolation; graph analysis correctly surfaces that its
customer_proxy shares a bank account with 3 others. Neither layer is
"wrong" — they are reporting on different properties of the same
transaction.

---

## 5. Missed-by-ML analysis (Phase 3I)

182 validation+test transactions have `ml_risk_tier ∈ {LOW, MEDIUM}` AND
`graph_flagged=True`. Classified (mutually exclusive, ground-truth-driven,
`scripts/ml_graph_ablation.py::classify_missed_by_ml`):

| Category | Count | % | Definition |
|---|---|---|---|
| **Legitimate shared infrastructure** | 140 | 76.9% | `synthetic_entity_label ∈ {legitimate_shared_infra, decoy_bystander}` — correctly-flagged-as-structural, correctly-not-fraud hard negatives |
| **Genuine additional signal** | 21 | 11.5% | `synthetic_entity_label == ring_member` — a real injected coordination pattern ML had no way to see |
| **Synthetic artifact** | 21 | 11.5% | `synthetic_entity_label == normal` and `isFraud == 0` — the ambient leakage mechanism (`docs/SYNTHETIC_DATA_GENERATION.md` §2) coincidentally connected unrelated customers; a cost of the generator's own realism mechanism, not a real signal |
| **Model blind spot** | 0 | 0% | `synthetic_entity_label == normal` and `isFraud == 1` — none found in this run |

**If the graph mostly found synthetic artifacts, that would need
immediate reporting per Phase 3I's instruction — it does not.** The
majority (76.9%) is exactly what Phase 1.5's hard-negative work was
built to produce and correctly hold as non-fraud (§`docs/GRAPH_BENCHMARK_FULL.md`
§5's 0% FP result is the flip side of this same number). A meaningful
minority (11.5%) is genuine additional structural signal ML cannot see.
Another 11.5% is an honestly-labeled cost of the leakage mechanism
(§`docs/SYNTHETIC_DATA_GENERATION.md` §2) — real but bounded and
understood, not hidden.

---

## 6. ML/Graph quadrant matrix (Phase 3J)

| | Graph Low | Graph High |
|---|---|---|
| **ML Low** | **A**: n=173,059, fraud rate 2.03%, ring-member rate 0.01% | **B**: n=182, fraud rate 2.20%, **ring-member rate 11.5%**, legit-infra rate 76.9% |
| **ML High** | **C**: n=4,103, fraud rate **63.71%**, ring-member rate 0.0% | **D**: n=0 |

**Quadrant D is empty — not a bug, a direct consequence of §4's finding.**
Ring membership and real fraud are independent by construction, so a
transaction being simultaneously "ML-flagged for looking like real
fraud" AND "graph-flagged for coordinated structure" essentially never
co-occurs in this benchmark. In a system where coordinated abuse and
individual-transaction fraud genuinely correlate (the real-world
scenario Section 1 of the design doc describes), quadrant D is exactly
where the two layers would reinforce each other — this benchmark cannot
test that correlation because the synthetic design deliberately keeps
the two ground truths independent (Phase 1 Section 9), a limitation
carried forward from Phase 1, not introduced here.

**Quadrant B is confirmed as the most important category** (Phase 3J's
own framing) — real fraud rate here (2.20%) isn't dramatically different
from quadrant A's background rate (2.03%), but the ring-member
concentration is **800x higher** (11.5% vs 0.014%) — this is precisely
the population an investigation agent (Phase 4+) should prioritize
*for coordination review*, distinct from (not a replacement for)
quadrant C's fraud-review priority.

---

## 7. What this means for "does the graph add value"

**Reported honestly, in two parts, per Phase 3's explicit instruction
not to let one number hide the other:**

1. **At the transaction/fraud-detection level, measured against this
   benchmark's real `isFraud` label: no.** Precision/recall/F1/PR-AUC
   are unchanged to 4 decimal places. This is stated plainly, not
   downplayed.
2. **At the coordinated-structure-detection level, which transaction-
   level ML has zero capability to address by construction: yes,
   substantially.** 84% recovery of ring-member transactions ML could
   never see, 0% false positives against all 4 hard-negative types in
   the recommended view, and a quadrant-B population 800x enriched for
   ring membership relative to background.

Whether this constitutes "the graph adds meaningful value" depends on
whether coordinated-abuse detection is treated as a goal in its own
right (design doc Section 3: "why an investigation agent is
necessary... a risk score and a ring ID are not an investigation") or
folded into a single fraud-recall metric. This benchmark's answer: **the
graph adds a real, distinct capability, not an improvement to the
existing one** — and the ablation table in §2 must always be reported
alongside §4's ring-recovery numbers, never in isolation, or it produces
exactly the misleading "graph adds nothing" conclusion Phase 3's brief
warned against pre-judging.

## 8. Known limitation carried into this conclusion

The independence of synthetic ring labels from real `isFraud` (Phase 1
Section 9) means this benchmark **cannot** test the design doc's
strongest claim — that coordinated abuse and individual fraud actually
correlate in the real world (quadrant D would be where that shows up,
and it's structurally empty here). This is a benchmark-design limitation
inherited from Phase 1, not something Phase 3 introduced or can fix —
flagged explicitly for whoever validates this against real Razorpay data
later.
