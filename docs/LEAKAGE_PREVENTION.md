# Leakage Prevention — Phase 2M

Maps each of Phase 2M's 7 required leakage guarantees to the specific
mechanism enforcing it and the test(s) proving it, so this is a checked
contract, not a claim.

---

## 1. Test rows cannot enter training

**Mechanism:** `src/ingestion/split.py::assign_split` (Phase 1A,
unchanged) produces a strict row-time-order partition; `src/features/pipeline.py::get_split`
filters by the `split` column and every training script
(`scripts/train_baseline.py`) reads only `df[df["split"] == "train"]`.
There is no code path that reads the `test` split before
`scripts/evaluate_baseline.py`.

**Tests:**
`tests/integration/test_pipeline_leakage.py::test_test_rows_never_appear_in_train_split`,
`tests/unit/test_temporal_split.py::test_no_duplicate_transaction_id_across_splits`,
`tests/integration/test_temporal_split_real_data.py` (Phase 1A, real data).

## 2. Future rows cannot influence historical aggregates

**Mechanism:** `src/features/historical.py` — `cumcount()` (0-indexed,
excludes current row by construction), `.diff()` (previous row only),
and a `searchsorted`-based prior-24h count that only counts rows with
strictly earlier `TransactionDT`. See §7 below for the bug this
category of test actually caught.

**Tests:**
`tests/unit/test_historical_features_leakage.py::test_no_future_row_ever_influences_a_past_row`
(hand-crafted, truncation-based), `tests/integration/test_pipeline_leakage.py::test_historical_features_leak_safe_on_real_pipeline_output`
(same method, real data, all 435 final feature columns' historical
subset checked).

## 3. Synthetic ground-truth fields cannot enter feature matrices

**Mechanism:** `src/features/leakage_guard.py::NON_FEATURE_COLUMNS` —
denylists `GROUND_TRUTH_COLUMNS` (`original_isFraud`,
`synthetic_ring_id`, `synthetic_abuse_type`, `synthetic_ring_role`,
`legitimate_cluster_id`, `legitimate_cluster_type`,
`synthetic_entity_label`) plus `SYNTHETIC_ENTITY_COLUMNS`
(`device_synthetic_id` and 7 others — Phase 2A addition, docs/FEATURE_AUDIT.md
§G). `src/features/pipeline.py::_feature_columns` filters against this
set; `get_split` calls `assert_no_leakage` before returning `X`.

**Tests:**
`tests/unit/test_no_synthetic_leakage_in_feature_matrix.py` (6 tests,
Phase 2-specific, checking the actual pipeline output — not just the
denylist definition, which Phase 1H's
`tests/unit/test_ground_truth_and_leakage.py` already covers in
isolation).

## 4. Target is not accidentally included

**Mechanism:** `isFraud` is in `NON_FEATURE_COLUMNS`.

**Test:** `tests/unit/test_no_synthetic_leakage_in_feature_matrix.py::test_feature_columns_never_include_target`.

## 5. TransactionID is not used as a predictive feature unless explicitly justified

**Mechanism:** `TransactionID` is in `NON_FEATURE_COLUMNS`
(docs/FEATURE_AUDIT.md §E: it's a pure row identifier, and correlates
0.998 with `TransactionDT`, so using it raw would smuggle in absolute
temporal position). No code path re-adds it. `customer_proxy_id` and
`payment_instrument_proxy_id` (the raw ID strings) are excluded the same
way — their *confidence tier* (ordinal-encoded) is a permitted feature,
the raw ID string is not.

**Test:** `tests/unit/test_no_synthetic_leakage_in_feature_matrix.py::test_feature_columns_never_include_transaction_id`,
`::test_feature_columns_never_include_proxy_identifiers`.

## 6. Validation/test thresholds are not used during training

**Mechanism:** structural, not just procedural — `src/models/thresholds.py::select_thresholds`'s
function signature has no parameter that could accept test data at all
(only `y_val`/`val_scores`); `scripts/train_baseline.py` never imports
`select_thresholds`; `scripts/calibrate_and_threshold.py` (which does)
only ever loads `val`, never `test`, from the feature parquet.
`scripts/evaluate_baseline.py` is the only script that reads `test`, and
it only ever *applies* the already-fixed thresholds/calibrator/models —
it fits nothing.

**Test:** `tests/unit/test_no_synthetic_leakage_in_feature_matrix.py::test_threshold_selection_has_no_test_data_parameter`
(inspects the function signature directly).

## 7. No random temporal leakage exists

**Mechanism:** the split is a deterministic function of `TransactionDT`
row order (mergesort-stable), never a random shuffle; historical
features are computed on the full chronological stream sorted by
`TransactionDT` before any split label is applied (a validation/test
row's velocity feature legitimately includes real train-period history —
this is correct, not leakage, since it mirrors what would be available
in production, see `src/features/pipeline.py`'s module docstring).

**Tests:** `tests/integration/test_pipeline_leakage.py::test_split_matches_standalone_phase_1a_split`
(cross-checks the pipeline's internal split against Phase 1A's
standalone function on the same data), plus all of Phase 1A's temporal
tests (`tests/unit/test_temporal_split.py`,
`tests/integration/test_temporal_split_real_data.py`).

---

## A real leakage-adjacent bug this testing caught

`tests/integration/test_pipeline_leakage.py::test_historical_features_leak_safe_on_real_pipeline_output`
caught a genuine implementation bug (not a leakage-guard gap, but the
same category of risk this phase's testing exists to catch): the
original `cust_txn_count_prior_24h` / `card1_txn_count_prior_24h`
implementation used `pandas.groupby().rolling()`, whose result is
ordered group-by-group rather than in original row order; converting it
straight to `.to_numpy()` for positional assignment silently
misattributed values across unrelated customers. A customer with
exactly one transaction ever showed a nonzero "transactions in the prior
24 hours" count — an impossible value that only a real-data,
end-to-end test surfaced (the hand-crafted unit test's small example
didn't happen to interleave groups in the way that exposed it). Fixed
with a `searchsorted`-based, index-preserving implementation
(`src/features/historical.py`), re-verified against both the original
hand-crafted example and real data. Full impact analysis in
`docs/ML_BASELINE.md` §7 — this is exactly why Phase 2M asked for tests
at both the unit (hand-crafted, exact-answer-known) and integration
(real-data, property-based) level: the bug was invisible to the former
and caught by the latter.
