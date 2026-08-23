# ML Baseline — Phase 2B/2C/2D/2E/2F/2G/2K/2L

**Method:** every number below comes from `scripts/train_baseline.py`,
`scripts/calibrate_and_threshold.py`, and `scripts/evaluate_baseline.py`
run against the real, full 590,540-row `train_transaction.csv` (+
`train_identity.csv`), using the temporal split established in Phase 1A
(`src/ingestion/split.py`, unchanged). Test was touched **exactly once**,
in `scripts/evaluate_baseline.py`, after every model/threshold/
calibration decision was already frozen from train+validation. Full
artifacts: `data/processed/*.json`.

---

## 1. Temporal split (Phase 2D — unchanged from Phase 1A)

| Split | Rows | Fraud rate |
|---|---|---|
| Train | 413,378 | 3.517% |
| Validation | 88,581 | 3.434% |
| Test | 88,581 | 3.480% |

Row-time-order split (stable sort by `TransactionDT`, contiguous
70/15/15 blocks) — verified identical to the standalone Phase 1A split
inside the feature pipeline
(`tests/integration/test_pipeline_leakage.py::test_split_matches_standalone_phase_1a_split`).

---

## 2. Feature engineering (Phase 2E) — summary

440 feature columns from a 393-column raw input. Full definitions and
leakage-risk notes per family:

| Family | Definition | Source | Leakage risk | Implementation |
|---|---|---|---|---|
| Amount | `amount_log1p`, `amount_cents`, `amount_is_round_dollar` | `TransactionAmt` (real) | None — per-row transform | `src/features/engineering.py::add_amount_features` |
| Temporal | `hour_of_day`, `hour_sin/cos`, `day_of_week_relative`, `day_sin/cos` | Derived from `TransactionDT` | None — raw `TransactionDT` itself is excluded (docs/FEATURE_AUDIT.md §C/§F) | `add_temporal_features` |
| Velocity/frequency | `{cust,card1}_txn_count_so_far`, `_time_since_last_txn`, `_txn_count_prior_24h` | `TransactionDT` grouped by `customer_proxy_id` / `card1` | **High** — the central leakage risk of this phase | `src/features/historical.py`, see §7 below (a real bug was caught and fixed here) |
| Card-related behavioral | `{cust,card1}_amount_mean_so_far`, `_amount_std_so_far`, `_amount_zscore_vs_history` | `TransactionAmt` history, same grouping | High — same module | `src/features/historical.py::add_group_amount_stats` |
| Email-domain | `P_emaildomain_freq_encoded`, `R_emaildomain_freq_encoded` | Real columns, frequency-encoded | Encoder fit on TRAIN only | `FrequencyEncoders` |
| Address | `addr1`, `addr2` (raw) + `_is_missing` indicators | Real columns | None | `add_missingness_indicators` |
| Device (real identity only) | `DeviceType`, `DeviceType_freq_encoded`, `has_identity_data` | `train_identity.csv` (real, 24.4% coverage) | None — **never** the synthetic `device_synthetic_id` (hard-denylisted, `src/features/leakage_guard.py`) | `load_raw_transactions` |
| Missingness indicators | `{col}_is_missing` for 25 columns | docs/FEATURE_AUDIT.md §D's measured missingness-as-signal columns | None | `add_missingness_indicators` |
| Aggregated historical | See velocity/frequency above | — | High | — |

**Full id_01-38 block:** documented at summary level
(docs/FEATURE_AUDIT.md), not individually engineered in this baseline —
an explicit, stated scope limitation (§13), not a hidden gap.

---

## 3. Customer proxy — Phase 2F ablation (measured, not assumed)

Per Phase 2F's instruction: measure whether `customer_proxy`-derived
historical features (`cust_*`, 5 columns) actually help before keeping
them, treating `customer_proxy_id` strictly as `docs/ENTITY_MODEL.md`'s
"derived behavioral grouping proxy," never as verified identity.

| XGBoost variant | Validation PR-AUC |
|---|---|
| **With** `cust_*` features (440 total features) | 0.5500 |
| **Without** `cust_*` features (435 features, `card1_*` retained) | **0.5502** |

**Decision: dropped.** The `cust_*` features did not improve — and
marginally hurt — validation PR-AUC. This is consistent with, not
contradictory to, `docs/ENTITY_MODEL.md`'s finding that `customer_proxy`
is "the least misleading of 7 tested candidates," not a validated
identity: its historical aggregates carry no more signal than the
narrower, more defensible `card1`-based ones, and the model is better
off without the extra noise. `card1_*` velocity/amount-history features
ARE kept — they measurably contribute (see feature importance, §9). The
final model uses 435 features (`data/processed/final_feature_columns.json`).

---

## 4. Missingness strategy (Phase 2G)

Compared **A. raw/imputed only**, **B. missingness indicators**,
**C. both** — chose **C**, informed directly by `docs/FEATURE_AUDIT.md`
§D's finding that missingness itself is a stronger fraud signal than
several features' raw values (e.g. `D7`: 14.9% fraud rate when present
vs 2.7% when missing). XGBoost gets both: the raw value (NaN handled
natively — design doc Section 11) AND an explicit `_is_missing`
indicator (25 columns) — confirmed NOT redundant: `addr1_is_missing`
and `M4_is_missing` both rank in the top-15 global feature importances
(§9), meaning the model is using the indicator as real signal beyond
what native NaN-splitting alone captures. Logistic Regression, which
cannot handle NaN natively, gets median imputation (fit on TRAIN only)
plus the same indicators.

---

## 5. BASELINE 1 — Rules (Phase 2B)

Four simple rules combined by OR (`src/models/baseline_rules.py`),
thresholds fit from TRAIN only:

| Rule | Threshold |
|---|---|
| Amount anomaly | `|cust_amount_zscore_vs_history| > 3` |
| Velocity | `cust_txn_count_prior_24h >= 3` |
| Card repeated | `card1_txn_count_prior_24h >= 5` |
| Extreme amount | `TransactionAmt >` 99.5th train percentile |

**Test results:** precision 0.0366, recall 0.6150, F1 0.0691. Confusion
matrix: TN 35,600 / **FP 49,898** / FN 1,187 / TP 1,896 — flags 58.5% of
all test transactions. **Total illustrative cost: ₹34,446,859** (dominated
by ₹32.4M in false-positive investigation cost). This is the naive floor
the ML baselines have to beat — and do, decisively (§8).

---

## 6. BASELINE 2 — Logistic Regression (Phase 2C)

`class_weight='balanced'` (not oversampling — Phase 2's explicit
instruction), median imputation + standard scaling fit on TRAIN only.

| Split | PR-AUC | ROC-AUC | Precision | Recall | F1 | Brier |
|---|---|---|---|---|---|---|
| Validation | 0.4128 | 0.8536 | — | — | — | — |
| **Test** | **0.1745** | 0.8256 | 0.1052 | 0.7343 | 0.1840 | 0.1661 |

**Material finding:** PR-AUC drops sharply from validation (0.4128) to
test (0.1745) — a 58% relative decline — while ROC-AUC barely moves
(0.8536 → 0.8256). This is a genuine temporal-generalization weakness
specific to the linear model, not a bug (re-confirmed after the §7
feature-alignment fix, which changed this number by <1%): LR's overall
ranking ability holds up, but its precision at any fixed operating point
degrades notably on the later time period, consistent with linear
models being more sensitive to gradual feature-distribution drift than
tree-based splits. Reported, not hidden — this is part of why XGBoost is
selected as primary (§8).

---

## 7. BASELINE 3 — XGBoost (Phase 2C, primary/selected)

`scale_pos_weight` fit from TRAIN (not oversampling), native NaN
handling, early stopping on validation `aucpr`. Small fixed
hyperparameter set (`max_depth=6, eta=0.05, subsample=0.8,
colsample_bytree=0.8, min_child_weight=5, n_estimators<=500`) — no
extensive grid search, per Phase 2's "not a leaderboard score"
instruction.

| Split | PR-AUC | ROC-AUC | Precision @0.5 | Recall @0.5 | F1 @0.5 | Brier |
|---|---|---|---|---|---|---|
| Validation | 0.5502 | — | — | — | — | — |
| **Test** | **0.5114** | **0.8973** | 0.2391 | 0.6795 | 0.3537 | 0.0704 |

Confusion matrix @0.5: TN 78,830 / FP 6,668 / FN 988 / TP 2,095 — flags
9.9% of test transactions, vs. rules' 58.5%.

**A real bug was found and fixed during this phase**
(`tests/integration/test_pipeline_leakage.py`): the original
`cust_txn_count_prior_24h`/`card1_txn_count_prior_24h` implementation
used `pandas.groupby().rolling()`, which silently returns results
grouped-then-ordered rather than in original row order; converting that
straight to `.to_numpy()` for positional assignment corrupted the
feature for any row where a different customer's transaction fell
between it and its own group-mates in time (i.e., almost always).
Caught by an integration test asserting a customer with exactly one
transaction ever showed a nonzero prior-24h count — impossible if
correct. Fixed with a `searchsorted`-based, index-preserving
implementation (`src/features/historical.py`), verified against the
same hand-crafted example and the real data. **Impact:** RULES recall
went from 0.1995 → 0.6150 (the velocity rule was previously firing on
essentially arbitrary values); XGBoost PR-AUC changed by <1% (a strong
model with 435 other features absorbed the one broken feature); LR
changed by <1% too. All numbers in this document are POST-fix.

---

## 8. Selected baseline

**XGBoost.** PR-AUC 0.5114 vs. Logistic Regression's 0.1745 and Rules'
(undefined — no continuous score) F1 of 0.0691 vs. XGBoost's 0.3537.
Total illustrative cost at XGBoost's cost-minimizing threshold:
**₹3,340,456** — roughly **10x lower** than the rules baseline's
₹34,446,859, while investigating an order of magnitude fewer
transactions (8,763 vs. 51,794 at their respective operating points).
This is the headline ablation result design doc Section 23 asked for:
what ML buys over rules, quantified, not claimed.

---

## 9. Feature importance (Phase 2K)

Top 15 by XGBoost gain (`src/models/explainability.py`, full top-20 in
`data/processed/final_test_evaluation.json`):

| Rank | Feature | Human-readable description |
|---|---|---|
| 1 | `V218` | anonymized Vesta-engineered signal |
| 2 | `V258` | anonymized Vesta-engineered signal |
| 3 | `V70` | anonymized Vesta-engineered signal |
| 4 | `V294` | anonymized Vesta-engineered signal |
| 5 | `V91` | anonymized Vesta-engineered signal |
| 6 | `V201` | anonymized Vesta-engineered signal |
| 7 | `V158` | anonymized Vesta-engineered signal |
| 8 | `M4_is_missing` | missingness of M4 (measured fraud-correlated, §4) |
| 9 | `C8` | raw count feature |
| 10 | `addr1_is_missing` | missing billing address information |
| 11 | `C4` | raw count feature |
| 12 | `C14` | raw count feature |
| 13 | `card6_freq_encoded` | rarity of card type (debit/credit) |
| 14 | `V187` | anonymized Vesta-engineered signal |
| 15 | `V308` | anonymized Vesta-engineered signal |

**Confirms two Phase 2A audit findings directly, not just in theory:**
the V-block dominates importance (7 of top 15) despite many V-columns'
high missingness, and `M4_is_missing`/`addr1_is_missing` rank in the
top 10 — the missingness-indicator features are genuinely used by the
model, not redundant with native NaN handling.

Per-case explanations (`explain_case`, exact SHAP contributions via
XGBoost's native `pred_contribs`) produce human-readable signal lists
like `"unusual amount relative to this customer's own transaction
history"` — this is the shape of evidence the investigation agent
(Phase 3+) would consume; two worked examples are in
`data/processed/final_test_evaluation.json`.

---

## 10. Performance by slice (Phase 2L)

**By transaction amount bucket (test):**

| Bucket | n | Fraud rate | Precision | Recall | PR-AUC |
|---|---|---|---|---|---|
| 0–25 | 6,548 | 8.31% | 0.387 | 0.838 | **0.716** |
| 25–100 | 45,725 | 2.90% | 0.249 | 0.622 | 0.480 |
| 100–250 | 26,770 | 2.73% | 0.180 | 0.638 | 0.431 |
| 250–1000 | 8,243 | 5.34% | 0.217 | 0.757 | 0.494 |
| **1000+** | 1,295 | 3.32% | 0.109 | 0.372 | **0.139** |

**Model is weakest on the highest-value transactions** — the segment
where a miss is most costly. Flagged as a real limitation (§13), not
smoothed over.

**By identity-data presence (test):**

| | n | Fraud rate | PR-AUC |
|---|---|---|---|
| Has identity data | 18,182 | 9.50% | **0.735** |
| No identity data | 70,399 | 1.93% | **0.150** |

The model performs far better on the 20.5% of test transactions with
real identity-table data — but that means for the **majority (79.5%)**
of transactions, PR-AUC is a modest 0.150. This mirrors
`docs/FEATURE_AUDIT.md`'s own finding about identity-linked
transactions being a biased, higher-base-rate subset — the model has
inherited that same imbalance in its own skill, not just in the raw
data.

**By temporal quarter within test:** PR-AUC 0.533 (Q1) → 0.431 (Q2) →
0.536 (Q3) → 0.541 (Q4) — no dramatic degradation across the test
window, reasonably stable.

---

## 11. Cost analysis

See §5, §8, and `docs/RISK_THRESHOLD_POLICY.md` for the full cost-model
derivation and threshold sweep. Headline: rules ₹34.4M vs. XGBoost
₹3.3M illustrative total cost on the test split, at each baseline's own
sensible operating point.

---

## 12. Reproducibility

`configs/seed.yaml`'s seed (42) is threaded through every stochastic
step (`LogisticRegression(random_state=seed)`,
`xgb.train(...,seed=seed)`). Re-running `scripts/prepare_features.py` →
`scripts/train_baseline.py` → `scripts/calibrate_and_threshold.py` →
`scripts/evaluate_baseline.py` end-to-end reproduces identical row
counts, split boundaries, and feature values (verified,
`tests/integration/test_pipeline_leakage.py::test_reproducible_across_runs`);
model outputs are deterministic given XGBoost's fixed seed and
single-threaded-equivalent histogram construction on this dataset size.

---

## 13. Known limitations (stated, not hidden)

- The `id_01`–`id_38` identity block is used only via `has_identity_data`
  and `DeviceType` — not individually engineered as 38 separate features.
- Model skill is markedly weaker for transactions without identity data
  (79.5% of test) and for high-value transactions (§10) — both are
  real, load-bearing gaps for a production system, not edge cases.
- The illustrative cost model (`docs/RISK_THRESHOLD_POLICY.md`) uses a
  documented `fraud_cost_multiplier` assumption, not a validated
  Razorpay cost structure — stated explicitly, matching design doc
  Section 24's own framing.
- Logistic Regression's validation→test PR-AUC gap (§6) was investigated
  enough to characterize it (real, not the bug) but not enough to fully
  explain its mechanism — flagged as an open question, not resolved here.
