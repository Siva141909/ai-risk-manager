# Synthetic Data Generation — Phase 1D–1H

Everything in this document describes **SYNTHETIC** data (Section 2's
terminology contract, `docs/ENTITY_MODEL.md`) layered on top of real,
unmodified IEEE-CIS transaction rows. No real column is ever altered —
verified directly by `tests/integration/test_reproducibility.py::test_real_columns_byte_identical_before_and_after_generation`.

---

## 1. Determinism

Every synthetic value is derived from `(canonical seed, stable ID,
generation context)` via SHA-256 (`src/generator/rng.py`) — never
Python's built-in `hash()`, which is salted per-process by default and
is not safe for cross-run reproducibility. `derive_seed(seed, *parts)`
produces a 64-bit integer that seeds a `numpy.random.Generator`; the same
`(seed, parts)` always produces the same generator state, on any machine,
in any process.

Verified in `tests/integration/test_reproducibility.py`: same seed →
byte-identical output (transactions, cluster records, ring records, graph
structure); different seed → different synthetic assignment and ring
composition.

---

## 2. Ambient (non-narrative) base assignment — Phase 1D

Before any legitimate-cluster or ring story is injected, every
`customer_proxy_id` gets one "home" `device_synthetic_id`,
`ip_synthetic_id`, `bank_account_synthetic_id`, and `address_synthetic_id`,
assigned via **pooled slot assignment** (`src/generator/pools.py`):
distinct customer_proxy entities are mapped into a pool sized
`round(n_distinct * pool_ratio)`, so a ratio below 1.0 guarantees some
ambient sharing purely from pool pressure — no household/office/campus
narrative required for this base layer. Configured in
`configs/generator.yaml`:

| Entity | pool_ratio | Rationale |
|---|---|---|
| `device` | 0.75 | Moderate sharing — a device is often used by ~1.3 people on average |
| `ip` | 0.55 | Heavier sharing — ISP/NAT pooling is common in the real world |
| `bank_account` | 0.95 | Mostly 1:1, but a small share of legitimate joint accounts |
| `address` | 0.65 | Household-level sharing |

**These ratios are illustrative, not empirically calibrated against any
real-world distribution** — IEEE-CIS provides no ground truth for "how
many people really share a residential IP." They were chosen to be
directionally realistic (device/IP shared more than bank accounts), not
validated. See `docs/GRAPH_DATA_MODEL.md` §4 for a significant
finding this produced: at dev-sample scale, this pooling model
percolates into a single giant connected component **regardless of how
close to 1.0 the ratios are pushed** — this is a mathematical property of
uniform random pooling across a large population with multiple
independent sharing channels, not a tunable bug. Flagged as an
architecture-level item for Phase 2, not silently patched here.

---

## 3. Legitimate shared-infrastructure clusters — Phase 1E (mandatory)

Four patterns, each restricted to `customer_proxy` entities with ≤3
transactions in the working dataframe (injecting a shared-infra story
onto an already-high-volume proxy wouldn't make behavioral sense).
**None of these get a `synthetic_ring_id` — they are explicitly not
fraud.**

| Pattern | Shares | Size | Count (config default) | Why legitimate |
|---|---|---|---|---|
| **Household** | device, IP, address (all three) | 2–5 | 15 | A family plausibly shares a phone/laptop, home WiFi, and mailing address — this is the design doc's own canonical false-positive scenario (Section 4, Judge Q&A #7) |
| **Office** | IP only | 5–15 | 6 | Employees share a corporate NAT egress IP but have distinct devices, addresses, and payment instruments — the design doc's Judge Q&A #8 scenario |
| **Campus** | IP *range* (not exact IP) | 20–60 | 2 | Members get distinct individual IPs but a shared `/16`-style subnet prefix — models a large shared-infrastructure population (a "whole city sharing an IP range" scenario, Section 14's own example of what must NOT become a false giant ring) |
| **Business** | address only | 3–8 | 5 | Multiple unrelated customers shipping to/associated with one shared business address (e.g. a corporate procurement account, a PO box) — a real e-commerce pattern uncorrelated with fraud |

**Temporal behavior — deliberately NOT engineered.** Unlike rings
(§4), legitimate clusters do not select participants by time proximity —
members keep whatever real `TransactionDT`/`TransactionAmt` their actual
transaction had, with no clustering preference. This is the point: a
legitimate cluster looks like shared infrastructure **without** the
burst-timing or amount-synchronization signal a ring has, which is
exactly what should let a well-designed detector tell them apart (per
the design doc's Section 4 abuse-pattern table, "high shared-attribute
degree in a short window" is the *ring* signature specifically because
legitimate clusters lack the "short window" part).

**Probability / expected size in the dev dataset (20,000 transactions,
seed 42, measured, not projected):** all 28 configured clusters (15
household + 6 office + 2 campus + 5 business) were successfully injected
— see `data/synthetic/dev/legitimate_clusters.json`. 287 of 20,000
transactions (1.4%) carry a `legitimate_cluster_id`.

---

## 4. Synthetic coordinated-abuse rings — Phase 1F

Three ring types (design doc Section 4/8), each constructed by
**selecting** real transactions that already exhibit the target
temporal/amount pattern as closely as the available data allows — **not**
by fabricating `TransactionDT` or `TransactionAmt`, which are real
columns and are never modified (verified by
`tests/unit/test_rings.py::test_real_columns_never_modified_by_ring_injection`).

| Ring type | Shares | Size | Amount pattern | Count (default) |
|---|---|---|---|---|
| `shared_device` | device | 3–8 | near-identical | 3 |
| `shared_bank_account` | bank_account | 3–8 | varied | 3 |
| `multi_attribute` | device + IP + bank_account | 4–8 | near-identical | 2 |

**Selection algorithm** (`src/generator/rings.py::_select_participants`):
pick a random anchor transaction from the eligible candidate pool
(customer_proxy entities with ≤3 transactions, not already used by a
legitimate cluster or another ring); search a burst window around the
anchor's real `TransactionDT` (default 180–360 minutes depending on ring
type), doubling the window up to a 48-hour cap if not enough candidates
are found; among in-window candidates, either take the `size` closest in
`TransactionAmt` to the window's median (`near_identical`) or sample
randomly (`varied`).

**Noise (`noise_ratio`, default 0.15–0.2):** this fraction of a ring's
selected members are still labeled as ring members in ground truth, but
are deliberately **not** given the shared synthetic attribute — modeling
an evasive participant who avoids infrastructure reuse (design doc Judge
Q&A #20: "what happens if fraudsters deliberately rotate
infrastructure?"). Verified in
`tests/unit/test_rings.py::test_noise_members_labeled_but_not_sharing_attribute`.

**Decoys (`decoy_attach_probability`, default 0.3):** with this
probability, 1–2 unrelated, non-ring `customer_proxy` entities are
attached to the ring's shared synthetic attribute value — innocent
bystanders who coincidentally share infrastructure with a ring, **not**
labeled as ring members (`synthetic_ring_role = "decoy_bystander"`,
`synthetic_ring_id` stays null). This is what makes "shares an attribute
with a flagged ring" insufficient evidence on its own — exactly the
property Phase 1F's brief asked for ("the graph should require actual
analysis").

**Measured in the dev dataset:** 8 of 8 configured rings successfully
injected (3 shared_device, 3 shared_bank_account, 2 multi_attribute),
sizes 3–6 (see `data/synthetic/dev/rings.json`). 45 of 20,000
transactions (0.225%) are ring members; 3 are decoy bystanders.

---

## 5. Ground truth — Phase 1G

`src/generator/ground_truth.py` adds, without ever touching `isFraud`:

| Column | Meaning |
|---|---|
| `original_isFraud` | Explicit copy of the real `isFraud` — a defensive alias so no future synthetic label can ever be confused with it, verified as a true copy (not a view) in `tests/unit/test_ground_truth_and_leakage.py` |
| `synthetic_ring_id` | Non-null only for ring core/noise members |
| `synthetic_abuse_type` | `shared_device` / `shared_bank_account` / `multi_attribute` |
| `synthetic_ring_role` | `core_member` / `noise_member` / `decoy_bystander` |
| `legitimate_cluster_id`, `legitimate_cluster_type` | Non-null only for household/office/campus/business members |
| `synthetic_entity_label` | Consolidated single-column label: `ring_member` > `decoy_bystander` > `legitimate_shared_infra` > `normal`, precedence in that order |

These columns must survive through every future evaluation stage
unmodified — they are the ONLY source of truth for whether ring/graph
detection (Phase 2+) actually works, since IEEE-CIS's real `isFraud`
label has zero relationship to these injected patterns.

---

## 6. Leakage protection — Phase 1H

`src/features/leakage_guard.py` denylists every ground-truth column
(`GROUND_TRUTH_COLUMNS` from `src/generator/ground_truth.py`) plus
`isFraud` itself and identifier/join-key columns
(`TransactionID`, `customer_proxy_id`, `payment_instrument_proxy_id`)
from ever entering a feature matrix:

```python
from src.features.leakage_guard import assert_no_leakage, filter_allowed_features

assert_no_leakage(feature_df)          # raises LeakageError if any denylisted column is present
clean_df = filter_allowed_features(df)  # drops every denylisted column
```

Tested in `tests/unit/test_ground_truth_and_leakage.py` — including a
simulated "naive pipeline that forgot to filter" case, confirming the
guard actually raises rather than silently passing.

---

## 7. Small development dataset

`scripts/generate_dev_dataset.py` samples 20,000 transactions via a
seeded uniform random draw (not a head-slice — chosen for temporal and
fraud-label diversity across the full 6-month window) from
`train_transaction.csv`, runs the full pipeline, and writes to
`data/synthetic/dev/`:

- `transactions.csv` — real + derived-proxy + synthetic + ground-truth columns
- `legitimate_clusters.json`, `rings.json` — structured records of every injected pattern
- `generation_metadata.json` — seed, counts, graph summary

Per Phase 1L's instruction, the full-scale benchmark (all 590,540 rows)
is **not** generated in this phase — only after this dev dataset's tests
pass and a lead reviews the findings in this document and
`docs/GRAPH_DATA_MODEL.md`.
