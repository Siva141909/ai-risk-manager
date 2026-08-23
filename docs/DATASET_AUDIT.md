# IEEE-CIS Dataset Audit — REAL DATA, EMPIRICALLY VERIFIED

**Method:** every number in this document was produced by loading the actual
files in `data/raw/` with pandas and computing the stated statistic —
`scripts/audit_dataset.py` (read-only, no writes to `data/raw/`). Nothing
here is drawn from Kaggle documentation or memory; where the earlier
preliminary `GRAPH_FEASIBILITY.md` pass relied on documented schema, this
document supersedes it with measured values. Full raw script output is in
`scratch_audit_output.json` (git-ignored, local only, regenerable by
re-running the script).

---

## 1. File presence and exact sizes

All 5 expected files are present in `data/raw/`, dated 2019-12-11 (matches
the original Kaggle competition file timestamps):

| File | Size (bytes) | Size | Row count (excl. header) | Columns |
|---|---|---|---|---|
| `train_transaction.csv` | 683,351,067 | 652M | 590,540 | 394 |
| `train_identity.csv` | 26,529,680 | 25M | 144,233 | 41 |
| `test_transaction.csv` | 613,194,934 | 585M | 506,691 | 393 |
| `test_identity.csv` | 25,797,161 | 25M | 141,907 | 41 |
| `sample_submission.csv` | 6,080,314 | 5.8M | 506,691 | 2 |

All five files loaded successfully with pandas — no corruption, truncation,
or parse errors encountered.

## 2. Dtypes

| File | float64 | str/object | int64 |
|---|---|---|---|
| `train_transaction` | 376 | 14 | 4 |
| `test_transaction` | 376 | 14 | 3 (no `isFraud`) |
| `train_identity` | 23 | 17 | 1 |
| `test_identity` | 23 | 17 | 1 |

`train_transaction`'s 4 int64 columns are `TransactionID`, `isFraud`,
`TransactionDT`, `card1` (all zero missingness, which is why pandas could
infer integer rather than float). The 14 object columns are
`ProductCD`, `card4`, `card6`, `P_emaildomain`, `R_emaildomain`,
`M1`–`M9` — all categorical/flag strings. Every other named column
(`card2/3/5`, `addr1/2`, `dist1/2`, `C1`–`C14`, `D1`–`D15`) and the entire
`V1`–`V339` block are float64.

## 3. Target distribution (`train_transaction.isFraud`)

| Class | Count | % |
|---|---|---|
| 0 (legitimate) | 569,877 | 96.501% |
| 1 (fraud) | 20,663 | 3.499% |

**REAL DATA.** Confirms the design doc's implicit assumption of a highly
imbalanced binary target (Section 11's `scale_pos_weight` class-weighting
strategy is well-justified by this ratio — roughly 27.6:1).

`isFraud` exists **only** in `train_transaction.csv`. `test_transaction.csv`
has no label column at all — see Section 8 (temporal split) for why this
matters materially.

## 4. Temporal characteristics — `TransactionDT`

- `TransactionDT` is **not** a wall-clock timestamp; it is a relative
  offset in seconds from an unspecified reference point, consistent with
  the design doc's Section 5–6 note ("relative time").
- **Train range:** 86,400 → 15,811,131 seconds → **182.0 days**.
- **Test range:** 18,403,224 → 34,214,345 seconds → **183.0 days**.
- **Gap between train's last transaction and test's first:** exactly
  **30.0 days**. Train and test are **not contiguous** — there is a real,
  measured 30-day blackout period between them.
- `TransactionID` is monotonically increasing with row order in both
  files, and `corr(TransactionID, TransactionDT) = 0.9983` in train — row
  order is effectively chronological order (near-certainty, not just
  "probably").
- `TransactionID` ranges never overlap between train (2,987,000–3,577,539)
  and test (3,663,549–4,170,239) — zero shared IDs, confirmed by direct
  set intersection (0 matches).

**Conclusion: a strict temporal split is feasible and the data supports
it directly** — this confirms the design doc's Section 11/24 temporal-split
requirement is achievable with this actual file, not just achievable in
principle.

## 5. Temporal train/validation/test split — recommendation (real numbers)

**Material finding requiring explicit acknowledgment:** `test_transaction.csv`
carries **no `isFraud` label** (it is Kaggle's leaderboard holdout). This
means the design doc's Section 24 "train on earliest ~70%, validate on
next ~15%, test on final ~15%" **must be carried out entirely inside
`train_transaction.csv`** — Kaggle's `test_transaction.csv` cannot be used
for any supervised metric (PR-AUC, calibration, cost model) in this
project, only optionally as unlabeled data for e.g. feature-drift checks.
This isn't a contradiction of Section 24's intent, but it is a concrete
implementation detail that wasn't explicit in the design doc and needs to
be stated plainly so Phase 1 doesn't accidentally try to score against
Kaggle's unlabeled test file.

Row-time-order 70/15/15 split of `train_transaction.csv` (590,540 rows,
sorted by `TransactionDT` ascending, split by row position — the standard
way to do this when transaction density isn't perfectly uniform in time):

| Split | Row range | Day range (from train start) | Rows | Fraud rate |
|---|---|---|---|---|
| Train | rows 0–413,377 | day 0.0 → 119.81 | 413,378 | 3.517% |
| Validation | rows 413,378–501,958 | day 119.81 → 151.22 | 88,581 | 3.434% |
| Test (internal) | rows 501,959–590,539 | day 151.22 → 182.0 | 88,581 | 3.480% |

Fraud rate is stable across all three slices (3.43%–3.52%) — no gross
temporal drift in the label rate itself across this window, which is a
reasonable precondition for the split being usable (it doesn't rule out
feature-distribution drift, which Phase 1's model tests should still
check per Section 28).

**Recommendation:** adopt this 70/15/15 row-count-ordered split, computed
fresh from `TransactionDT` at Phase 1 time (don't hardcode the row-index
boundaries above — recompute them programmatically so the split is
reproducible against the actual loaded dataframe, matching Section 24's
"deterministic, seed-driven pipeline" requirement). Kaggle's
`test_transaction.csv`/`test_identity.csv` remain available as an
additional 506,691-row unlabeled pool if a use is found for it later
(e.g. checking that engineered feature distributions don't look wildly
different out-of-sample), but is out of scope for any metric reported in
the ablation study.

## 6. Missingness

**`train_transaction.csv`** (394 columns): mean missingness across all
columns = 41.07%. Distribution: 20 columns 0% missing, 174 columns >50%
missing, only 2 columns >90% missing (`dist2` 93.63%, `D7` 93.41%).

Named (non-`V`) columns, worst to best:

| Column | Missing % |
|---|---|
| `dist2` | 93.628 |
| `D7` | 93.410 |
| `D13` | 89.509 |
| `D14` | 89.469 |
| `D12` | 89.041 |
| `D6` | 87.607 |
| `D8` / `D9` | 87.312 |
| `R_emaildomain` | 76.752 |
| `dist1` | 59.652 |
| `M5` | 59.349 |
| `M7` / `M9` / `M8` | ~58.63 |
| `D5` | 52.467 |
| `M4` | 47.659 |
| `D2` | 47.549 |
| `D11` | 47.293 |
| `M1`/`M2`/`M3` | 45.907 |
| `D3` | 44.515 |
| `M6` | 28.679 |
| `D4` | 28.605 |
| `P_emaildomain` | 15.995 |
| `D15` | 15.090 |
| `D10` | 12.873 |
| `addr1` / `addr2` | 11.126 |
| `card2` | 1.513 |
| `card3`/`card4`/`card5`/`card6` | ~0.27–0.72 |
| `D1` | 0.215 |
| `TransactionID`, `TransactionDT`, `TransactionAmt`, `ProductCD`, `card1`, `isFraud`, `C1`–`C14` | 0.000 |

Notably, many `V` columns share **exactly** the same missingness rate
(e.g. `V138`, `V139`, `V149`, `V153`–`V163` all sit at **86.124%**
missing) — this is measured, not assumed, and indicates block-correlated
missingness (these columns are very likely jointly null/non-null per row,
i.e. missing as a group rather than independently) rather than random
per-column sparsity. This matters for Phase 1 imputation strategy: a
per-column median/mode fill would be defensible, but a missing-indicator
feature is probably more informative given the block structure, and the
V-block should be treated as a unit for that purpose rather than 339
independent decisions.

**`train_identity.csv`** (41 columns): the join-eligible subset has its
own missingness profile — `id_24/25/07/08/21/23/26/27/22` are
~96.4–96.7% missing even *within* the already-small identity-linked
subset. `DeviceInfo` is 17.73% missing, `DeviceType` is 2.37% missing.

## 7. Candidate entity identifiers and cardinality (REAL, measured)

| Field | Cardinality (`train_transaction`, `nunique`) | Role |
|---|---|---|
| `card1` | 13,553 | Highest-cardinality card field — closest to a raw card/BIN identifier |
| `card2` | 500 | — |
| `card3` | 114 | — |
| `card4` | 4 | Card network (visa/mastercard/amex/discover) |
| `card5` | 119 | — |
| `card6` | 4 | debit/credit |
| `addr1` | 332 | Billing region code (anonymized) |
| `addr2` | 74 | Billing country code (anonymized) |
| `P_emaildomain` | 59 | Purchaser email domain |
| `R_emaildomain` | 60 | Recipient email domain |
| `ProductCD` | 5 | Product category |
| `DeviceType` (identity) | 2 (`desktop`/`mobile`) + NaN | — |
| `DeviceInfo` (identity) | 1,786 | See Section 9 — quality caveat below |
| `id_30` (identity, OS string) | 75 | — |
| `id_31` (identity, browser string) | 130 | — |
| `id_33` (identity, screen resolution) | 260 | — |

## 8. Payment-instrument proxy (`card1`–`card6` tuple) — MATERIAL FINDING

The design doc (Section 7) proposes deriving `customer_id` from "unique
card/identity hash groupings." This was tested directly against
`card1`–`card6` treated as a compound key:

- **14,893 unique `card1`–`card6` combinations across 590,540 rows.**
- **10,790 of those combinations (72.5%) appear more than once**, together
  covering **586,437 of 590,540 rows (99.3%)** — almost the entire
  dataset collapses into repeat-combination buckets, only 4,103
  combinations (27.6%) are singletons.
- Combination size distribution is extremely skewed: mean group size
  39.65, but the **largest single combination has 14,112 rows** (the
  99th-percentile+ tail — 99 combinations alone have ≥1,000 rows each).
- **Critically: the fraud rate inside that 14,112-row mega-cluster is
  3.73%**, statistically indistinguishable from the dataset base rate of
  3.50%.

**This mega-cluster is not a fraud ring and is not a single real
customer** — it is far more consistent with `card1`–`card6` collapsing to
a coarse categorical bucket (e.g., "Visa debit, this BIN range, this
issuer bucket") shared by thousands of unrelated real cardholders, the
same way many people share a bank's BIN range. Treating raw `card1`–`card6`
tuple equality as "same customer" — as a literal reading of Section 7's
table would suggest — would inject a false 14,112-node "ring" into the
entity graph purely from card-issuer coincidence, before the synthetic
ring generator even runs. This is exactly the failure mode Section 14
designed Louvain to catch for shared-IP office/campus clusters
("everyone on one shared IP is one giant false ring") — but that mitigation
was scoped for `ip_address`/`device`, not explicitly for the `card1`-`card6`
→ `customer_id` derivation. **Flagged for lead decision before Phase 2** —
see "Architecture changes" at the end of this document. This audit does
not silently pick a fix.

## 9. `DeviceInfo` / identity coverage and quality

**Join coverage (real, measured):**
- Train: **144,233 / 590,540 transactions (24.42%)** have a matching
  `train_identity.csv` row.
- Test: **141,907 / 506,691 transactions (28.01%)** have a matching
  `test_identity.csv` row.
- Fraud rate **with** an identity match: **7.847%**. Fraud rate
  **without** one: **2.094%** — a real, measured 3.75x difference. This
  is a strong, genuine signal (identity-linked transactions are far more
  fraud-prone on average) but also a **selection-bias warning**: any
  device/identity-based feature or graph anchor only exists for ~24–28%
  of transactions, and that subset is not a random sample of all
  transactions — it is already skewed toward higher fraud rate before any
  modeling happens. Entity/graph features derived from identity data must
  be null/`unknown`-flagged for the other ~75%, not silently imputed
  (consistent with Section 22's failure-handling principle).

**`DeviceInfo` quality — MATERIAL FINDING:**
`DeviceInfo` has 1,786 unique values, but its distribution is dominated by
**OS/browser-family labels, not device fingerprints**:

| Value | Count |
|---|---|
| `Windows` | 47,722 |
| *(missing)* | 25,567 |
| `iOS Device` | 19,782 |
| `MacOS` | 12,573 |
| `Trident/7.0` (IE11 UA fragment) | 7,440 |
| `rv:11.0` | 1,901 |
| specific phone model strings (e.g. `SM-J700M Build/MMB29K`) | 549 and falling |

The top value, `Windows`, appearing 47,722 times, obviously represents
tens of thousands of distinct physical machines, not one shared device —
using `DeviceInfo` directly as a "same device" graph anchor the way the
design doc's Section 13 `DEVICE_SHARED_WITH` edge implies would be
badly wrong for the bulk of the field's mass. Only the long tail of
specific Android build strings (e.g. `SM-G935F Build/NRD90M`, 334 rows)
has any device-model specificity, and even those represent "same phone
model," not "same physical device shared by one household" — a Samsung
Galaxy model sold in the thousands is not evidence of coordination.

**This finding does not contradict the design doc — it confirms a
decision the design doc already made.** Section 7's data model table
already marks `device` as **`Synthetic overlay — Injected per Section 8's
ring generator`**, not derived from `DeviceInfo`. This audit provides the
empirical justification for that choice: `DeviceInfo` genuinely cannot
serve as a reliable device-uniqueness anchor at this dataset's resolution,
so the design's decision to keep `device` entirely synthetic is the
correct call, now evidence-backed rather than precautionary.

## 10. Train/test schema differences (REAL, measured)

**Transaction files:** `train_transaction.csv` has exactly one column
`test_transaction.csv` doesn't: `isFraud`. No other schema differences —
confirmed by direct set difference on `df.columns`, zero surprises in
either direction.

**Identity files — confirmed quirk:** `train_identity.csv` uses `id_01`
… `id_38` (underscore); `test_identity.csv` uses `id-01` … `id-38`
(hyphen) for the exact same fields. Verified: after normalizing hyphens to
underscores in `test_identity`'s column names, the two column sets are
**identical** (empty set difference both directions). This is a genuine
quirk of the actual Kaggle files (documented informally in the
competition's discussion forum, but verified here directly against the
files, not assumed) — any ingestion code that joins or unions train/test
identity data must normalize this naming difference first, or every join
against `test_identity.csv` will silently fail to find the `id_*` columns.

## 11. Potential target leakage — scan performed, none found above threshold

Computed `|correlation(feature, isFraud)|` for all 391 numeric feature
columns (excluding `TransactionID`, `isFraud`). Top 15:

| Column | \|corr\| |
|---|---|
| V257 | 0.383 |
| V246 | 0.367 |
| V244 | 0.364 |
| V242 | 0.361 |
| V201 | 0.328 |
| V200 | 0.319 |
| V189 | 0.308 |
| V188 | 0.304 |
| V258 | 0.297 |
| V45 | 0.282 |
| V158 | 0.278 |
| V156 | 0.276 |
| V149 | 0.273 |
| V228 | 0.269 |
| V44 | 0.260 |

**No column exceeds |corr| = 0.5.** No near-duplicate-of-target column
found (a leaked label would show correlation near 1.0). `TransactionID`
uniqueness was verified directly (`is_unique = True` in both train and
test, 590,540 and 506,691 rows respectively) — no duplicate transaction
rows that could cause train/test cross-contamination.

**Scope of this check — stated limitation, not resolved:** this was a
linear (Pearson) correlation scan over numeric columns only. It does not
rule out (a) non-linear leakage, (b) leakage via a categorical column
(`M1`–`M9`, `card4`, `card6`, email domains, `ProductCD`), or (c) leakage
introduced later by entity-level rolling features that accidentally look
into the future (that specific check is Section 24's dedicated unit test,
not something this audit can verify without the feature pipeline
existing). Flagging this as an open item for Phase 3's leakage unit test,
not a finding of "no leakage" — only "no *linear numeric* leakage found."

## 12. Fields suitable for modeling vs. fields to exclude

**Exclude from modeling:**
- `TransactionID` — pure row identifier; also near-perfectly correlated
  with `TransactionDT` (0.998), so including it raw would smuggle a
  temporal-order signal in through the back door.
- Raw `TransactionDT` as a magnitude feature — use it for splitting and
  for deriving relative features (`hour_of_day = TransactionDT % 86400`,
  `time_since_last_txn`, etc.) per Section 10, not as a raw numeric
  feature, or the model will overfit to the specific window it was
  trained on.
- `dist2`, `D7` — >90% missing; likely drop or reduce to a
  missing-indicator only, decide in Phase 3 with a documented rationale
  rather than defaulting silently.
- `id_24/25/07/08/21/23/26/27/22` — >96% missing even within the
  identity-linked subset; same treatment as above.

**Usable, but need explicit handling:**
- `card1`–`card6`, `addr1`/`addr2` — genuinely categorical despite
  numeric-looking codes; must not be treated as ordinal/continuous.
- The `V1`–`V339` block — usable, but given the observed block-correlated
  missingness (Section 6), impute and/or flag as a block, not column by
  column independently.
- `DeviceInfo`, `id_30`, `id_31`, `id_33` — free-text-ish, high
  cardinality; need normalization/parsing (e.g., extracting OS family
  from `DeviceInfo`) before being useful as model features, not
  usable as raw categoricals without cleanup given cardinalities of
  1,786 / 75 / 130 / 260.

**Directly usable as-is:** `TransactionAmt`, `ProductCD`, `card4`, `card6`,
`P_emaildomain`, `R_emaildomain`, `C1`–`C14`, `M1`–`M9`,
`DeviceType` (only 2 real categories + NaN).

## 13. Real vs. Derived vs. Synthetic boundary (confirmed against actual data)

**REAL OBSERVED DATA** (present in the files, used as-is):
`TransactionID`, `isFraud`, `TransactionDT`, `TransactionAmt`, `ProductCD`,
`card1`–`card6`, `addr1`/`addr2`, `dist1`/`dist2`, `P_emaildomain`,
`R_emaildomain`, `C1`–`C14`, `D1`–`D15`, `M1`–`M9`, `V1`–`V339`, all
`id_01`–`id_38`, `DeviceType`, `DeviceInfo`.

**DERIVED FEATURES / PROXIES** (computed from real columns, not present
verbatim, and — per Section 8's finding — need a more careful derivation
rule than naive tuple equality): a `customer_id`-like grouping from
`card1`–`card6` (+ possibly `addr1`/`addr2`, `P_emaildomain`) — **not yet
safe to implement as literally "one customer_id per unique card1–card6
combination,"** pending the Section 8 finding; relative-time features
(`hour_of_day`, `time_since_last_txn`) from `TransactionDT`; OS/browser
family extracted from `DeviceInfo`/`id_30`/`id_31`.

**SYNTHETIC OVERLAY** (no real signal exists in IEEE-CIS at all, must be
generated): `ip_address`, `bank_account`, `upi_id`, `settlement`,
`refund`, and — confirmed by Section 9's finding — `device` as a
uniqueness anchor (real `DeviceInfo` cannot serve this role at the
required resolution). `merchant` remains a category-level proxy via
`ProductCD` (5 values) only, not a real merchant identity — unchanged
from the Phase 0 preliminary finding, now with a measured cardinality
(5) confirming just how coarse this proxy is.

## 14. Fields we previously assumed might exist but do NOT

From the Phase 0 preliminary `GRAPH_FEASIBILITY.md`, confirmed absent by
direct column inspection of both transaction and identity files:
- No `ip_address` / IP field of any kind.
- No `bank_account` / settlement destination field.
- No true `merchant_id` (only `ProductCD`, a 5-value category code).
- No true `customer_id` (only the `card1`–`card6` proxy, now shown in
  Section 8 to be unsafe as a literal 1:1 customer key).
- No real free-text address (only anonymized `addr1`/`addr2` codes,
  332 and 74 distinct values respectively — not usable as pincode-like
  geography).

---

## DATASET AUDIT STATUS: **PASS**

All five expected files are present, readable, internally consistent
(unique keys, matching `sample_submission` IDs, single-column
train/test schema diff on `isFraud`, identical identity schema after
hyphen/underscore normalization), and support the design doc's required
temporal-split methodology. The audit surfaced two material findings that
need explicit lead sign-off before Phase 2 (see below) but found **no
blocking data-integrity problem** and **no evidence the core architecture
is unworkable**.

### Exact dataset dimensions
`train_transaction`: 590,540 × 394. `train_identity`: 144,233 × 41.
`test_transaction`: 506,691 × 393. `test_identity`: 141,907 × 41.

### Fraud rate
3.499% (20,663 / 590,540), train only — test is unlabeled.

### Important missingness findings
Mean 41.07% missing across `train_transaction`'s 394 columns; only 2
columns exceed 90% missing (`dist2`, `D7`); many `V`-block columns share
identical missingness rates (block-correlated, not independent). Identity
fields `id_24/25/07/08/21/23/26/27/22` are >96% missing even within the
already-partial identity-linked subset.

### Strongest real graph anchors
`card1` (13,553 unique values) and `P_emaildomain`/`R_emaildomain`
(59/60 unique domains) are the strongest *real* attribute signals
available — but "strongest available" is not the same as "safe to use
alone": Section 8 shows raw `card1`–`card6` tuple equality already
produces a 14,112-transaction bucket with baseline (non-elevated) fraud
rate, so any real anchor needs multi-attribute confirmation or
time-window narrowing before being trusted as a ring-forming edge, in
the same spirit Section 14 already applies to shared-IP components.

### Weakest / unsafe graph assumptions
1. `card1`–`card6` tuple as literal `customer_id` (Section 8) — measured
   to be unsafe without narrowing.
2. `DeviceInfo` as a "same device" anchor (Section 9) — measured to be
   dominated by OS/browser-family labels, not device fingerprints; the
   design doc's existing "fully synthetic `device`" choice is correct and
   now evidence-backed.
3. Device/identity coverage overall is a 24–28% subset with a 3.75x
   higher fraud rate than the uncovered majority — any graph feature
   built on identity data is describing a biased quarter of the
   transactions, not the whole population, and must be flagged as such
   wherever it's used, not silently generalized.

### Proposed temporal split
70/15/15 by row-time-order **within `train_transaction.csv` only**
(590,540 rows → 413,378 / 88,581 / 88,581), because `test_transaction.csv`
carries no label. Fraud rate is stable across all three slices
(3.43%–3.52%). Recompute split boundaries programmatically from
`TransactionDT` at Phase 1 time rather than hardcoding the row indices
found here.

### Leakage risks
No linear-correlation leakage found (`|corr| < 0.4` for all numeric
features against `isFraud`); this is a partial check (numeric, linear
only) and does not cover categorical-column leakage or future rolling-
feature leakage — both remain open items for Phase 3's dedicated leakage
unit test per Section 24.

### Architecture changes: **none required**, but two items need explicit lead decision before Phase 2

This audit does not find the three-layer architecture (ML / graph /
agent) unworkable, and does not contradict the design doc's core
technology or scope decisions. It does surface two concrete,
evidence-based implementation questions that Section 7's table doesn't
fully resolve as written, and this audit is intentionally **not**
resolving them unilaterally:

1. **How should `customer_id` actually be derived from `card1`–`card6`?**
   Literal tuple equality is measured to be unsafe (Section 8). Options
   worth a lead decision: (a) require `card1`–`card6` **and** a narrow
   co-occurrence window (e.g., same `addr1` and transactions within N
   days) before treating rows as the same synthetic customer; (b) cap
   accepted cluster size and treat oversized clusters as "unresolved
   customer" rather than merging them; (c) treat card-based customer
   linkage itself as a synthetic-overlay-dominant signal (similar
   treatment to `ip_address`) rather than a real-data-derived one. No
   option has been implemented — this is a design decision, not a bug
   fix.
2. **Should `DeviceInfo`/`id_30`/`id_31` feed *any* real signal into the
   graph, or should `device` stay 100% synthetic as Section 7 already
   states?** This audit's finding supports keeping Section 7's existing
   choice unchanged (no architecture change needed here) — flagged only
   so it's an explicit, evidence-backed decision rather than an
   unexamined default going into Phase 2.

`docs/GRAPH_FEASIBILITY.md` has been updated in place with these findings,
replacing its Phase 0 "preliminary, pending verification" numbers with
the measured ones above.
