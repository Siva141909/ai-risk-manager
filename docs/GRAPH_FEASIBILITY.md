# Graph Feasibility Check — VERIFIED AGAINST REAL DATA

**Status:** the Phase 0 preliminary version of this document was based on
publicly documented IEEE-CIS schema, not actual inspection. That version
is superseded — every claim below is now backed by numbers measured
directly from `data/raw/*.csv` (see `docs/DATASET_AUDIT.md` for the full
audit and `scripts/audit_dataset.py` for the exact computation). Two
conclusions changed materially from the Phase 0 pass, both downgrades in
confidence, both flagged explicitly below rather than silently folded in.

## 1. Which real fields can anchor entities?

| Target entity | Candidate anchor field(s) | Confidence — Phase 0 (documented schema) | Confidence — NOW (measured) |
|---|---|---|---|
| `customer` | `card1`–`card6` tuple | Medium | **Downgraded to Low-Medium.** 14,893 unique combinations across 590,540 rows, but 72.5% of combinations repeat, covering 99.3% of rows; the single largest combination has **14,112 rows** with a fraud rate (3.73%) statistically indistinguishable from the dataset base rate (3.50%) — i.e., it is not a coordinated cluster, it is a coarse card-issuer bucket. See §4 below. |
| `device` | `DeviceInfo` + `DeviceType` | Medium | **Downgraded to Low.** `DeviceInfo`'s top value (`Windows`, 47,722 rows) is an OS family label, not a device fingerprint. Only a long tail of specific Android build strings has any device-model specificity, and even those identify a phone *model*, not one physical device. Confirms the design doc's existing choice (Section 7) to keep `device` fully synthetic — this is now evidence, not caution. |
| `payment_instrument` | `card1`–`card6` | Medium-high | **Downgraded to Medium**, same basis as `customer` above — attribute-equality is real but coarse; needs narrowing before use as a ring-forming edge. |
| `merchant` | `ProductCD` | Low | **Unchanged — confirmed Low.** Measured cardinality: exactly 5 distinct values. A 5-way category cannot function as merchant identity. |
| `email/domain` | `P_emaildomain`, `R_emaildomain` | Medium-high | **Unchanged — confirmed Medium-high.** Measured cardinality: 59 / 60 distinct domains — genuinely domain-level, coarse in the way documented (e.g. `gmail.com` will span many unrelated users), consistent with the Phase 0 expectation. |
| `address` | `addr1`, `addr2` | Low | **Unchanged — confirmed Low.** Measured cardinality: 332 / 74 — anonymized codes, not real geography. |
| `ip_address` | Not present | None | **Unchanged — confirmed absent.** No IP-shaped field exists anywhere in either transaction or identity files. |
| `bank_account` | Not present | None | **Unchanged — confirmed absent.** No settlement/bank-account field exists in either file. |

## 2. Which relationships are naturally available?

Confirmed by direct measurement: "same `card1`–`card6` combination," "same
`P_emaildomain`/`R_emaildomain`," and — for the 24.42% (train) /
28.01% (test) of transactions with a matching identity row — "same
`DeviceInfo`." These remain **attribute co-occurrence relationships, not a
designed relational graph**, exactly as the Phase 0 pass expected. What's
new: the co-occurrence on `card1`–`card6` is measurably **too coarse to
use directly** (§4) — this wasn't knowable without the real data, and the
Phase 0 "medium confidence" rating undersold that risk.

## 3. Which relationships must be synthetic?

Per Section 7 of the design doc, confirmed and (for `device`) reinforced
by measurement:
- `device` as a uniqueness anchor — confirmed synthetic-only is correct
  (§1); real `DeviceInfo` cannot serve this role at the needed resolution.
- `ip_address` — entirely synthetic, zero real field, confirmed by
  column-level inspection of both transaction and identity files.
- `bank_account` — entirely synthetic, zero real field, confirmed.
- `upi_id`, `settlement`, `refund` — entirely synthetic, zero real field
  in either file (unchanged from Phase 0, now confirmed by direct
  column inspection rather than assumption).
- `address` beyond the low-cardinality anonymized `addr1`/`addr2` codes.
- The `DEVICE_SHARED_WITH` ring-forming edges (Section 13) — entirely
  generator-injected, not discoverable from raw data.
- **New finding, not anticipated at Phase 0:** naive `card1`–`card6`
  tuple-equality edges must ALSO be treated as unsafe-to-use-directly —
  not because the field is absent (it's real and present), but because
  using it without narrowing produces false mega-clusters indistinguishable
  from base-rate legitimate traffic (§4). This sits between "real" and
  "synthetic" — it's a real field that needs a synthetic-overlay-grade
  narrowing rule before being trusted, which Phase 0 could not have
  surfaced from documentation alone.

## 4. Card1–card6 mega-cluster finding (new — measured, not anticipated at Phase 0)

Direct measurement (`scripts/audit_dataset.py`, full detail in
`docs/DATASET_AUDIT.md` §8):

- 14,893 unique `card1`–`card6` combinations in 590,540 train rows.
- 10,790 combinations (72.5%) repeat; those repeats cover 586,437 rows
  (99.3% of the dataset).
- Largest single combination: **14,112 rows**, fraud rate **3.73%**
  (dataset base rate: 3.50%) — no elevated fraud signal, i.e., this is
  not a ring, it's a large legitimate cohort sharing a coarse card
  attribute bucket (most likely a common BIN/issuer/network/type
  combination, not a shared physical card).

**Implication:** if Phase 2's ring generator or entity-resolution logic
treats `card1`–`card6` tuple equality as "same customer" without
additional narrowing (e.g. requiring co-occurrence within a bounded time
window, or requiring agreement on `addr1`/`P_emaildomain` too), the very
first entity graph built from real data will already contain a
14,112-node false ring before any synthetic ring or legitimate-cluster
generator even runs. This is the same class of failure Section 14
designed Louvain sub-community detection to catch for oversized shared-IP
components — but Section 14's mitigation was scoped to the graph-analysis
stage, not to the upstream `customer_id` derivation rule itself. **This
needs an explicit narrowing rule decided before Phase 2 implements entity
resolution** — see `docs/DATASET_AUDIT.md`'s "Architecture changes"
section for the specific options; this document does not pick one.

## 5. How much of the graph will be synthetic?

**Unchanged conclusion, now on firmer footing.** Most of the graph's
ring-forming structure remains synthetic: `ip_address` and `bank_account`
contribute zero real signal (confirmed absent, not just undocumented);
`merchant` is a 5-value category proxy (confirmed, not assumed);
`device` needed for `DEVICE_SHARED_WITH` is confirmed unsuitable from real
`DeviceInfo` and must stay synthetic. What's new is a *sharper* picture of
`customer`/`payment_instrument`: not just "weak proxy" but "measurably
unsafe without a narrowing rule" — meaning the fraction of the graph that
can lean on real data is smaller in practice than the Phase 0 "medium
confidence" rating implied, even though the field itself is real.

## 6. Can we inject ring structures without modifying the original fraud labels?

Unchanged from Phase 0: yes, in principle, verified now to be practically
enforceable — `TransactionID` is confirmed unique in both train (590,540)
and test (506,691), so joining synthetic columns onto real rows by
`TransactionID` is a safe, unambiguous operation. The Phase 0
recommendation stands: a unit test should assert real columns are
byte-identical before/after the generator runs (still not implemented —
this is a Phase 2 requirement, not something this audit builds).

## 7. Can we construct legitimate shared-infrastructure clusters?

Unchanged from Phase 0, with one added data point: real co-occurrence on
`card1`–`card6` is now known to be *abundant* (72.5% of combinations
repeat) — if the negative-class generator wants to anchor "legitimate
shared attribute" scenarios in real co-occurrence rather than fully
synthetic data, there is plenty of real repeat structure to sample from
(e.g., the very mega-clusters flagged as unsafe for positive-ring
purposes in §4 are, by the same evidence, good raw material for the
*legitimate*-cluster generator — a large low-fraud-rate shared-attribute
group is exactly what "looks coordinated but isn't" should look like).

## 8. What limitations does this create?

- **`card1`–`card6` cannot be used as a naive customer/payment-instrument
  key** (§4) — confirmed limitation, stronger than the Phase 0 "imprecise
  proxy" framing suggested. Needs a documented narrowing rule (see
  `DATASET_AUDIT.md`).
- **Device coverage is partial and biased, not just partial.** Measured:
  24.42% (train) / 28.01% (test) of transactions have any identity/device
  data at all, and that subset has a 7.847% fraud rate vs. 2.094% for the
  uncovered majority (3.75x difference) — any device-based feature or
  graph signal describes a biased quarter of transactions, not a random
  sample. This is stronger and more specific than the Phase 0 "partial
  coverage" note.
- **No real merchant, IP, or bank-account signal whatsoever** — confirmed
  by direct column inspection (not assumption). Ring-forming edge types
  (shared IP, shared bank account) remain 100% synthetic; ring-detection
  numbers measure "can we find the patterns we wrote a generator for."
  Unchanged from Phase 0 — this check finds no basis to soften that
  framing, and now has zero ambiguity behind it.
- **Address data is unusable as a real signal** — confirmed cardinality
  (332 / 74) is consistent with anonymized low-cardinality codes, not
  real geography. Unchanged from Phase 0.

## Status: no longer preliminary

This document is now backed by measured statistics from the actual
dataset and does not require further re-verification unless the raw
files change. Any Phase 2 implementation decision about `customer_id`
derivation (§4) should be made explicitly and referenced back to this
document, not re-derived from scratch.
