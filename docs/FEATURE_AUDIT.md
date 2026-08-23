# Feature Audit — Phase 2A

**Method:** every number below is computed directly from
`train_transaction.csv` (+ `train_identity.csv` for the identity
summary) via `scripts/audit_features.py` — full machine-readable output
in `scratch_feature_audit_output.json` (git-ignored, regenerable). No
number here is fabricated or estimated from documentation. This
supersedes `docs/DATASET_AUDIT.md`'s missingness table with the
*predictive-usefulness* dimension that document didn't compute.

**Scope:** classification applies to `train_transaction.csv`'s 393
feature columns (+ a summary treatment of `train_identity.csv`'s 40).
`TransactionID` and `isFraud` are handled separately (identifier,
target).

---

## Classification

### A. SAFE NUMERIC FEATURES

Real-valued, low-to-moderate missingness, no leakage risk, usable
directly (after imputation where needed):

`TransactionAmt` (0% missing), `C1`–`C14` (0% missing each — count
features, genuinely complete), `D1` (0.22%), `D4` (28.6%), `D10`
(12.9%), `D15` (15.1%), `card2` (1.5%), `card3` (0.27%), `card5`
(0.72%).

`D2`, `D3`, `D5`, `D11` (28–52% missing) are borderline A/D — kept here
because their present-vs-missing fraud-rate gap is real but modest
(e.g. `D11`: 1.96% present vs 5.21% missing) compared to the D6–D14
block (§D); treated as safe numeric **with** a missingness indicator
(§Phase 2G strategy), not dropped and not treated as pure signal-only.

### B. SAFE CATEGORICAL FEATURES

Real, low-cardinality-enough to encode, genuinely predictive (measured
via fraud-rate spread across categories with ≥50 rows each — a category
column with near-zero spread carries no signal regardless of how "safe"
it looks):

| Column | Missing % | Cardinality | Fraud-rate spread across categories | Verdict |
|---|---|---|---|---|
| `ProductCD` | 0% | 5 | **9.65 pts** | Strong — keep |
| `card4` (network) | 0.27% | 4 | **4.86 pts** | Keep |
| `card6` (debit/credit) | 0.27% | 4 | **4.25 pts** | Keep |
| `M4` | 47.7% | 3 | **8.67 pts** | Keep + missingness indicator (§D) |
| `M6` | 28.7% | 2 | 0.66 pts | Keep, weak signal alone — useful mainly combined with others |
| `M2`, `M3`, `M9` | 45.9–58.6% | 2 | 1.2–1.7 pts | Keep + indicator, modest individual signal |
| `M1`, `M7`, `M8` | 45.9–58.6% | 2 | ~0.3–0.6 pts, but **missingness itself is the real signal** (§D) | Keep for the indicator, not the raw value |
| `card1` | 0% | 13,553 | linear corr −0.014 (weak) | High-cardinality real attribute — keep as a plain numeric/categorical code for tree models (do **not** treat as an identifier for row lookup; see §E for why it's excluded from that role but not from features) |

### C. TEMPORAL FEATURES

`TransactionDT` itself is **excluded from raw feature use** (§G) but is
the *source* for every derived temporal feature (hour-of-day,
day-of-week-ish cyclical position, time-since-last-transaction). The
`D1`–`D15` block is Vesta's own set of pre-computed time-delta features
(e.g., days-since-X) — genuinely temporal in nature, already
point-in-time by construction (Kaggle's documentation and this audit's
own evidence — see §D — are consistent with these being computed at
transaction time, not retroactively). Classified primarily by
missingness severity below since that's the more actionable property
for each one individually.

### D. HIGH-MISSINGNESS FEATURES — measured, not assumed

**Central finding: missingness is not noise here — for several
features it is a stronger fraud signal than the feature's own present
value.** This directly informed the answer to Phase 2A's explicit
instruction not to blindly drop these.

| Column | Missing % | Fraud rate **when present** | Fraud rate **when missing** | Ratio | Verdict |
|---|---|---|---|---|---|
| `D7` | 93.4% | **14.88%** | 2.70% | **5.5×** | Keep as missingness indicator; raw value nearly unusable (93% empty) but *presence* is one of the strongest single signals measured |
| `D12` | 89.0% | 11.74% | 2.49% | 4.7× | Same treatment |
| `D8` / `D9` | 87.3% | 10.45% | 2.49% | 4.2× | Same treatment |
| `D6` | 87.6% | 10.55% | 2.50% | 4.2× | Same treatment |
| `D13` | 89.5% | 11.04% | 2.62% | 4.2× | Same treatment |
| `D14` | 89.5% | 11.60% | 2.55% | 4.5× | Same treatment |
| `R_emaildomain` | 76.8% | 8.18% | 2.08% | 3.9× | Keep — indicator *and* the domain value (real categorical spread 37.7 pts, §B) |
| `addr1` / `addr2` | 11.1% | 2.46% | **11.78%** | **4.8× (inverted direction)** | Keep — missing address correlates with sharply *elevated* risk, opposite direction from the D-block; both signals matter |
| `dist2` | 93.6% | 9.92% | 3.06% | 3.2× | Keep as indicator only — raw value too sparse to impute meaningfully |
| `dist1` | 59.7% | 2.00% | 4.52% | 2.3× (inverted) | Keep, moderate missingness, real value usable too |
| `M1`/`M5`/`M7`/`M8`/`M9` | 45.9–59.4% | ~2.0% | ~4.6–5.3% | ~2.3–2.7× | Keep as indicators — the raw category values (§B) carry little spread alone, but missingness does |
| **`V1`–`V339` block (47 cols >80% missing)** | 80–86% | — | — | mean \|corr\| for the high-missingness subset (0.082) is *higher* than for the low-missingness subset (0.067) | High missingness in the V-block does **not** correlate with low predictive value — confirms the "don't blindly drop" instruction was well-founded here too. Kept, block-imputed with per-block indicators (§Phase 2G) |

**Conclusion for this bucket:** every high-missingness column tested
shows measurable present/absent fraud-rate divergence (2.3×–5.5×) — none
are dropped outright. The engineering implication (Phase 2E/2G): each of
these needs a **missingness indicator feature**, and several (D6–D14,
`dist2`) need the indicator to carry more of the modeling weight than
the sparse raw value itself.

### E. ID-LIKE FEATURES

| Column | Why excluded from feature use |
|---|---|
| `TransactionID` | Pure row identifier, `nunique == n_rows`; also corr 0.998 with `TransactionDT` (Phase 0 audit), so using it raw would smuggle in a temporal-order signal via the back door |
| `customer_proxy_id`, `payment_instrument_proxy_id` | **DERIVED PROXY** identifiers (Phase 1C/1.5 Decision 8) — already denylisted in `src/features/leakage_guard.py::NON_FEATURE_COLUMNS`. Their *confidence tier* and *aggregate behavioral features derived from history* are allowed (§Phase 2F); the raw ID string is not a feature |

`card1` is high-cardinality (13,553 distinct values) but is **not**
treated as ID-like — it's a real, reused payment attribute (many
transactions legitimately share a `card1` value), not a per-row unique
key. See §B.

### F. POTENTIAL LEAKAGE FEATURES

- **No column found with near-perfect target correlation** — max
  `|corr|` across all 391 numeric columns is 0.383 (`V257`), confirmed
  again in this pass (`scratch_feature_audit_output.json`). This is
  consistent with `docs/DATASET_AUDIT.md` §11's earlier scan.
- **`TransactionDT` as a raw magnitude feature** — not target leakage
  in the classic sense, but a *temporal-shift* leakage risk: using the
  absolute value would let the model memorize "late in the window =
  more/less fraud" in a way that won't generalize past the training
  window. Excluded from raw use (§G); only derived cyclical/relative
  features are allowed.
- **Historical/aggregated features (Phase 2E/2F)** — the actual leakage
  risk in this project is procedural, not a specific input column: any
  aggregate computed per `customer_proxy_id` or `card1` must use
  strictly-past rows only. This is enforced in
  `src/features/historical.py` and tested directly (Phase 2M).

### G. EXCLUDED FEATURES

| Column(s) | Reason |
|---|---|
| `TransactionID` | Identifier (§E) |
| Raw `TransactionDT` | Temporal-shift leakage risk (§F); used only as a derivation source |
| `customer_proxy_id`, `payment_instrument_proxy_id` (raw ID strings) | Identifiers (§E) |
| `isFraud` | Target, not a feature |
| `original_isFraud`, `synthetic_ring_id`, `synthetic_abuse_type`, `synthetic_ring_role`, `legitimate_cluster_id`, `legitimate_cluster_type`, `synthetic_entity_label` | Synthetic ground truth — **hard-denylisted**, `src/features/leakage_guard.py`, tested in `tests/unit/test_ground_truth_and_leakage.py` and re-verified for this phase in `tests/unit/test_no_synthetic_leakage_in_feature_matrix.py` |
| `device_synthetic_id`, `ip_synthetic_id`, `bank_account_synthetic_id`, `address_synthetic_id`, and their derived columns (`device_type_synthetic`, `ip_range_synthetic`, `ifsc_prefix_synthetic`, `pincode_synthetic`) | 100% synthetic overlay (Phase 1/1.5) — belongs to the graph layer only, never an ML feature. Real identity-table fields (`DeviceType`, `id_*`) are a *different*, real data source and ARE permitted (§ below) |

**Real identity-table fields — permitted, with caveats (Phase 2E point
7):** `train_identity.csv`'s `DeviceType` (2 categories) shows a real,
meaningful fraud-rate split — mobile 10.17% vs desktop 6.52% — but only
exists for the 24.4% of transactions with a matching identity row, and
that subset already has a 3.75× elevated base rate (7.85% vs 2.09%,
confirmed again this pass) versus the majority without identity data.
`DeviceType` and a `has_identity_data` indicator are both kept as
**SAFE CATEGORICAL** features; the 38 `id_01`–`id_38` columns are kept
as a block (mean missingness 36.5%, wide individual variance 0–96.7%)
with the same indicator-first treatment as the D-block, not
individually enumerated here for space.

---

## Summary table

| Bucket | Column count (approx.) | Treatment |
|---|---|---|
| A. Safe numeric | ~18 named + `C1`–`C14` | Direct use, minimal imputation |
| B. Safe categorical | ~10 named | Direct use (encoded) |
| C. Temporal | `TransactionDT` (derivation source only) + `D1`–`D15` (dual-classified into A/D by missingness) | Derived features only for `TransactionDT`; D-block per §D |
| D. High-missingness | `D6`–`D9`, `D12`–`D14`, `dist1`/`dist2`, `R_emaildomain`, `M1`/`M5`/`M7`–`M9`, 47 V-columns >80% missing | Kept, indicator-first |
| E. ID-like | `TransactionID`, `customer_proxy_id`, `payment_instrument_proxy_id` | Excluded as raw features |
| F. Potential leakage | Raw `TransactionDT`; procedural risk in historical aggregation | Excluded / mitigated by design |
| G. Excluded | Identifiers, target, all synthetic ground-truth and synthetic entity columns | Hard-denylisted, `src/features/leakage_guard.py` |
