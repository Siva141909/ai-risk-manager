# Graph Feasibility Check — PRELIMINARY (dataset not yet acquired)

**Status caveat:** IEEE-CIS is not present locally yet (see
`DATASET_ACQUISITION.md`). This document answers Section 13's feasibility
questions from the **publicly documented IEEE-CIS competition schema**
(column names and their known semantics), not from an actual inspection of
the data — no row counts, cardinalities, missingness rates, or co-occurrence
statistics are claimed here, because none have been measured. Every
quantitative claim below is deferred to a follow-up pass once the files are
downloaded and this document is re-verified against real data. Treat this
as "is the *shape* of the data plausible for a graph layer," not "here is
the graph."

## 1. Which real fields can anchor entities?

Candidates, by design-doc entity (Section 7):

| Target entity | Candidate anchor field(s) | Confidence this is a real anchor |
|---|---|---|
| `customer` | No direct customer/account ID exists in IEEE-CIS. `card1`–`card6` (anonymized card attributes) is the closest proxy for "the same payment instrument reused," which the design doc (Section 7) already names as the intended derivation: cluster by card/identity hash groupings to synthesize a `customer_id`. | Medium — plausible proxy, not a true customer ID |
| `device` | `DeviceInfo` + `DeviceType` (identity table) is the closest real device signal. `id_01`–`id_38` may contain additional device/browser fingerprint-like signals but their semantics are undocumented by Kaggle (deliberately obfuscated) beyond being anonymized numeric/categorical fields. | Medium — real field, but only ~24% of transactions have a matching identity row in the known public documentation of this competition, so device anchoring will be partial coverage, not universal |
| `payment_instrument` | `card1`–`card6` | Medium-high — same caveat as `customer`: a real field, but not a designed relational key, so "same card" is inferred from attribute equality, not an explicit ID |
| `merchant` | `ProductCD` only approximates a merchant category, not a merchant identity. There is no merchant ID field in IEEE-CIS. | Low — this is a category proxy, not a merchant anchor. The design doc (Section 7) already acknowledges `merchant_id` is synthetic/mapped from `ProductCD`, i.e., a many-to-one category label standing in for merchant identity, not a real 1:1 merchant anchor |
| `email/domain` | `P_emaildomain`, `R_emaildomain` | Medium-high — real, genuinely a domain-level identifier, though domain-level sharing (e.g., many unrelated users on `gmail.com`) is coarse and needs the multi-attribute weighting the design doc already calls for (Section 4, Q8) |
| `address` | `addr1`, `addr2` (anonymized, low-cardinality categorical, not real addresses) | Low — these are anonymized codes, not usable for anything address-shaped like pincode adjacency; the design doc already scopes address to synthetic overlay only (Section 7) |
| `ip_address` | **Not present.** IEEE-CIS contains no IP field. | None — must be fully synthetic, consistent with the design doc |
| `bank_account` | **Not present.** No settlement/bank account field. | None — must be fully synthetic, consistent with the design doc |

## 2. Which relationships are naturally available?

At most: "these transactions share the same `card1`–`card6` combination,"
"these transactions share the same `P_emaildomain`," and, for the subset of
transactions with a matching identity row, "these transactions share the
same `DeviceInfo`." These are **attribute co-occurrence relationships**,
not a designed relational graph — IEEE-CIS was built for row-level
classification, not entity resolution, so there is no ground-truth
"these two transactions belong to the same real person" label at all. The
design doc states this plainly (Section 5–6: "Weak/implicit... aren't
curated for ring analysis") and this preliminary check does not find
reason to disagree.

## 3. Which relationships must be synthetic?

Per Section 7 of the design doc, and confirmed by (1) above:
- `device` (beyond the partial real `DeviceInfo` signal)
- `ip_address` — entirely synthetic, no real field exists
- `bank_account` — entirely synthetic, no real field exists
- `upi_id` — entirely synthetic, no real field exists
- `address` (beyond the low-cardinality anonymized `addr1/addr2` codes)
- `settlement`, `refund` — entirely synthetic, no real field exists
- The `DEVICE_SHARED_WITH` ring-forming edges specifically (Section 13) —
  these are exactly what the ring generator (Section 8) injects on top of
  real transaction rows, not something discoverable from the raw data

## 4. How much of the graph will be synthetic?

Structurally, most of it. Two of the six node types in Section 13
(`customer`, `payment_instrument`) have a real but weak/proxy anchor;
`merchant` has a coarse category proxy; `device` has partial real coverage;
`ip_address` and `bank_account` have zero real signal. The edges that
actually *form rings* (`DEVICE_SHARED_WITH`, shared bank account, shared IP)
are overwhelmingly synthetic by construction, because the real dataset
supplies no bank/IP data at all and only partial, coarse device/card
co-occurrence. This matches the design doc's own framing (Section 2, Q4:
"Ring ground truth is entirely synthetic") — this check does not surface a
contradiction, it confirms the premise the design doc already states
explicitly.

## 5. Can we inject ring structures without modifying the original fraud labels?

Yes, in principle, and this is a hard requirement to preserve. The design
doc's leakage-check plan (Section 24) already specifies injecting synthetic
entities *after* the temporal split is fixed and never touching `isFraud`.
Practically: the ring generator should only ever *add* new columns/rows
(synthetic entity IDs, `ring_id`, `legitimate_shared_infra`) and join them
onto the real transaction rows by `TransactionID` — it must never overwrite
`isFraud`, `TransactionAmt`, `TransactionDT`, or any other real column.
This is an implementation discipline to enforce in Phase 2 (a unit test
should assert the real columns are byte-identical before/after the
generator runs), not something verifiable from schema alone — flagged here
as a requirement to carry into the generator's test suite.

## 6. Can we construct legitimate shared-infrastructure clusters?

Yes, structurally — nothing about the schema prevents it, because these
clusters are synthetic overlays by construction regardless (Section 8's
"legitimate-but-suspicious clusters" mode). The one dependency worth
flagging: if the negative-class generator wants to anchor a "family sharing
a device" scenario in *some* real signal (e.g., picking real transactions
that already share a `card1`/`DeviceInfo` combination and only adding
non-clustered timing/refund behavior on top), that depends on there being
enough real co-occurrence in the data to sample from — an empirical
question this check cannot answer without the actual files. If real
co-occurrence turns out to be too sparse, the fallback (fully synthetic
negative clusters, same as the positive-ring generator) still works and is
already the design's default construction method.

## 7. What limitations does this create?

- **No true entity resolution.** "Same `card1`–`card6`" is a proxy for
  "same payment instrument," not a verified identity link — two different
  real cards could coincidentally collide on all six anonymized attributes,
  and the design's own synthetic `customer_id` derivation (Section 7)
  inherits this imprecision. This should be stated as a limitation in the
  submission, consistent with the design doc's Section 2 Q5 commitment to
  not overstate what the synthetic layer proves.
- **Device coverage is partial.** Only transactions with a matching
  identity-table row have any device signal at all (real coverage is a
  known limitation of this competition's data — worth confirming the exact
  join rate once the files are read, rather than asserting a specific
  percentage now).
- **No real merchant, IP, or bank-account signal whatsoever** — the graph's
  most rung-forming edge types (shared IP, shared bank account) are 100%
  synthetic, meaning ring detection accuracy numbers measure "can we find
  the patterns we wrote a generator for," not "can we find real collusion."
  This is exactly the limitation the design doc requires be stated
  up front (Section 2, Q5; Section 9; Judge Q&A 6, 27) — this check finds
  no basis to soften that framing.
- **Address data is unusable as a real signal** — `addr1`/`addr2` are
  anonymized low-cardinality codes, not real geography; any
  pincode-adjacency-style reasoning must be purely synthetic (already
  scoped this way in Section 7 — "not a primary signal").

## Re-verification required

This document must be re-run/re-checked once `data/raw/*.csv` exist and
`docs/DATASET_AUDIT.md` has real cardinality, join-rate, and missingness
numbers for `card1`–`card6`, `DeviceInfo`, `P_emaildomain`, and `addr1/addr2`
— those numbers will either confirm or sharpen the "medium confidence"
anchors marked above, and may change the practical (not structural)
answer to "how much of the graph is synthetic."
