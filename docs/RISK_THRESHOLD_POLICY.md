# Risk Threshold Policy — Phase 2I

**The LLM/agent never determines the risk tier.** `src/models/thresholds.py::classify_risk_tier`
is a pure, deterministic function of `(risk_score, fixed thresholds)` —
same input always produces the same tier
(`tests/unit/test_threshold_determinism.py`). The thresholds themselves
are numbers selected once, from validation data, using the framework
below — never touched by the agent, never re-derived at inference time.

---

## 1. Structure

```
risk_score < low         -> LOW       (auto_clear)
low <= risk_score < high      -> MEDIUM    (analyst_review)
high <= risk_score < critical   -> HIGH      (mandatory_human_approval)
risk_score >= critical            -> CRITICAL  (escalate)
```

Mirrors the design doc's Section 20 structure. Risk scores here are the
**calibrated** probabilities (docs/ML_BASELINE.md §Calibration below),
not raw XGBoost output — thresholds are meaningless as fixed numbers
otherwise.

---

## 2. Calibration (Phase 2H) — fit and selected on VALIDATION only

| Method | Brier score (validation) |
|---|---|
| Raw XGBoost score | 0.06482 → 0.06379 (post §5 bugfix) |
| Platt scaling | 0.02217 → 0.02213 |
| **Isotonic regression** | **0.02128 → 0.02133** |

**Isotonic selected** (marginally lower Brier both before and after the
historical-feature bugfix — a stable, small margin over Platt, not a
close call decided by noise). Both calibrators improve Brier score by
~3x over the raw score — the raw XGBoost output is a good *ranking* but
a poor *probability*, exactly the gap calibration exists to close
(design doc Section 11: "the downstream cost model needs probabilities,
not just a ranking"). Reliability-curve bins (10 quantile bins) for all
three are in `data/processed/calibration_comparison.json`.

---

## 3. Cost model (Phase 2I) — false positive / false negative / investigation cost

Illustrative ₹ costs, explicit assumptions (design doc Section 24), fit
from TRAIN only:

| Cost | Value | Basis |
|---|---|---|
| False positive (per flagged-but-legitimate case) | ₹500 | Illustrative analyst investigation friction |
| Investigation cost (per case that reaches a human, regardless of outcome) | ₹150 | Illustrative analyst time |
| False negative (per missed fraud) | `mean_fraud_amount(TRAIN) x fraud_cost_multiplier` = ₹145.64 x 10 = **₹1,456.41** | See below |

### The multiplier — investigated, not asserted

**First attempt used `multiplier=1`** (false-negative cost = the
transaction's own face value only). Result: the cost-minimizing
threshold was **0.975**, capturing only **3.8%** of validation fraud
(116 of 3,042 fraud cases). This is a genuinely degenerate policy — it
happens because the mean fraud transaction amount here (₹145.64) is far
cheaper than a single false-positive investigation (₹650 combined), so
pure per-transaction cost minimization rationally concludes "don't flag
almost anything."

**Why that's not a usable policy:** a single fraudulent transaction that
slips through is not just a one-time ₹145.64 loss — chargeback fees,
reputational damage, and (most relevant to this project's own premise)
enabling repeat abuse by the same actor all compound beyond the face
value. A `fraud_cost_multiplier` corrects for this, stated as an
explicit assumption, not hidden in the number:

| Multiplier | FN cost (₹) | Cost-min. threshold | Recall | Precision | FP count |
|---|---|---|---|---|---|
| 1 (no correction) | 145.6 | 0.975 | 0.038 | 1.000 | 0 |
| 3 | 436.9 | 0.616 | 0.314 | 0.862 | 153 |
| 5 | 728.2 | 0.527 | 0.319 | 0.856 | 163 |
| 8 | 1,165.1 | 0.371 | 0.403 | 0.719 | 479 |
| **10 (selected)** | **1,456.4** | **0.305** | **0.440** | **0.658** | 698 |
| 15 | 2,184.6 | 0.233 | 0.479 | 0.595 | 990 |
| 20 | 2,912.8 | 0.183 | 0.531 | 0.512 | 1,541 |

**Selected: 10x** — a commonly-cited illustrative range in fraud-cost
literature is 3–15x face value depending on merchant category; 10x sits
in the middle of that range and produces a threshold (0.305) with
non-degenerate, defensible recall/precision (0.440/0.658 on validation).
This is a documented assumption for demonstration, explicitly not
Razorpay's real cost structure (matching design doc Section 24's own
framing) — a real deployment would calibrate this from actual chargeback
and repeat-abuse data, not an illustrative multiplier.

---

## 4. Three-threshold selection — each independently justified

| Boundary | Method | Selected value (validation, post-fix) |
|---|---|---|
| `low` (LOW/MEDIUM) | Largest threshold that still captures ≥98% of validation fraud above it — auto-clearing below it sacrifices at most 2% of recall | **0.0031** |
| `high` (MEDIUM/HIGH) | Single cost-minimizing threshold from the §3 sweep | **0.329** |
| `critical` (HIGH/CRITICAL) | Smallest threshold ≥ `high` where precision reaches 0.85 | **0.641** |

**`critical_precision` default is 0.85, not 0.5 — investigated, not
assumed.** At 0.5, the search for "smallest threshold ≥ `high` with this
precision" immediately returned `high` itself (validation precision at
the cost-minimizing threshold was already ~0.66), collapsing the HIGH
tier to empty — an early, real result caught while building this policy
(`docs/RISK_THRESHOLD_POLICY.md`'s working notes, `src/models/thresholds.py`'s
docstring). Swept precision targets 0.5–0.95 against the actual
validation precision curve (`data/processed/risk_thresholds.json`'s
predecessor runs) and picked 0.85 as the value producing a real,
non-empty HIGH band.

**Guaranteed ordering:** `low <= high <= critical` is enforced in
`select_thresholds` (`low = min(low, high)`), never assumed —
`tests/unit/test_threshold_determinism.py::test_thresholds_are_monotonically_ordered`.

---

## 5. Resulting tier distribution and fraud-rate separation

**Validation** (thresholds fit here):

| Tier | n | Fraud rate |
|---|---|---|
| LOW | 27,803 | 0.198% |
| MEDIUM | 58,783 | 2.826% |
| HIGH | 1,011 | 46.390% |
| CRITICAL | 984 | 87.093% |

**Test** (thresholds applied, never re-fit):

| Tier | n | Fraud rate |
|---|---|---|
| LOW | 27,845 | 0.298% |
| MEDIUM | 58,628 | 2.920% |
| HIGH | 1,007 | 34.657% |
| CRITICAL | 1,101 | 85.286% |

Clean, monotonic fraud-rate separation holds on test with thresholds
fixed entirely from validation — LOW stays under 0.3%, CRITICAL stays
above 85%. HIGH's test fraud rate (34.7%) is meaningfully lower than
validation's (46.4%) — a real generalization gap in that specific
middle band worth watching, though the overall tier ordering and
CRITICAL/LOW extremes hold up well.

---

## 6. What changed after the Phase 2E bugfix (docs/ML_BASELINE.md §7)

The velocity-feature alignment bug affected the rule baseline
dramatically but not calibration/threshold numbers materially — Brier
scores moved by <0.001, selected thresholds moved by less than the
grid resolution (0.001) in most cases. This document's numbers are all
POST-fix; no threshold in this policy was ever selected using the
buggy feature values.
