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

## 2. Ambient (non-narrative) base assignment — corrected Phase 1.5 model

**Superseded (Phase 1):** every `customer_proxy_id` got a "home"
device/IP/bank_account/address via **uniform pooled slot assignment**
across the ENTIRE customer population (`pool_size = round(n_distinct *
pool_ratio)`). `docs/GRAPH_DATA_MODEL.md` Finding 1 showed this
percolates into one giant connected component regardless of how close
to 1.0 the ratio was pushed (a mathematical property of multi-channel
uniform pooling at this population size, not a tunable parameter) —
Phase 1.5, Decision 1 replaced this mechanism.

**Current model:** `src/generator/legitimate_clusters.py`
(household/office/campus/business, §3) is now the **primary** source of
deliberate sharing. The ambient layer
(`src/generator/entity_assignment.py`, `src/generator/pools.py`) is now
deliberately narrow: each customer gets a **unique** attribute value
with high probability, and only a small, **fixed-size** ("leakage pool")
accounts for rare cross-population coincidence:

| Entity | Target expected leaking customers | Leakage pool size | Rationale |
|---|---|---|---|
| `device` | 15 | 8 | A handful of coincidental device-model/hotspot overlaps regardless of population size |
| `ip` | 25 | 12 | IP is the most plausible channel for incidental overlap (public WiFi, ISP NAT) |
| `bank_account` | 8 | 5 | Rarest incidental overlap — bank accounts are the most individual attribute |
| `address` | 15 | 8 | Occasional coincidental address reuse (e.g. shared postal drop points) |

**Why an absolute target count, not a percentage — measured, not
assumed.** A first version of this fix used a flat leakage
*probability* (e.g. 3–5%). Tested directly: at the dev sample's
~11,500–20,000 customers, even 3–5% still meant hundreds of people
drawing from a small fixed pool, which itself birthday-paradox-collided
into a smaller — but still real — percolating clump (measured: a
~2,000-node component even after excluding every hub entity type, see
`docs/GRAPH_BENCHMARK.md` §3). Deriving `leakage_prob =
target_leak_count / n_customers` at call time
(`src/generator/entity_assignment.py::_leak_prob`) keeps the EXPECTED
number of leaking customers constant regardless of population size —
this is what actually prevents percolation, confirmed empirically after
the fix (`tests/integration/test_graph_percolation_fixed.py`).

---

## 3. Legitimate shared-infrastructure clusters — corrected Phase 1.5 model (mandatory, primary sharing mechanism)

Four patterns, each restricted to `customer_proxy` entities with ≤3
transactions in the working dataframe (injecting a shared-infra story
onto an already-high-volume proxy wouldn't make behavioral sense).
**None of these get a `synthetic_ring_id` — they are explicitly not
fraud.**

**Phase 1.5 correction (Decisions 1 and 6):** sharing is now
**probabilistic per attribute, rolled once per cluster instance** (not
an all-or-nothing category list, and not per member) — a given
household either shares its device this instance or it doesn't, exactly
matching "occasional," not "always," per Phase 1.5's "realism over
convenience" requirement. Counts are also substantially higher than
Phase 1 (15/6/2/5 → 60/20/5/15) so the false-positive evaluation has
enough hard negatives to be meaningful.

| Pattern | Share probability per attribute | Size | Count (default) | Why legitimate |
|---|---|---|---|---|
| **Household** | device 40%, IP 50%, address 85%, bank_account 15% | 2–5 | 60 | A family plausibly shares a phone/laptop, home WiFi, and mailing address *some but not all of the time* — the design doc's own canonical false-positive scenario (Section 4, Judge Q&A #7) |
| **Office** | device 15%, IP 80%, address 0%, bank_account 0% | 5–15 | 20 | Employees share a corporate NAT egress IP but have distinct devices, addresses, and payment instruments — the design doc's Judge Q&A #8 scenario |
| **Campus** | device 5%, IP-range 90% (exact IP still distinct) | 20–60 | 5 | Members get distinct individual IPs but a shared `/16`-style subnet prefix — models a large shared-infrastructure population (Section 14's "whole city sharing an IP range" example of what must NOT become a false giant ring) |
| **Business** | device 35%, IP 45%, address 55%, bank_account 10% | 3–8 | 15 | Multiple unrelated customers associated with one shared business context (a shared workstation, a procurement account, a common delivery address) — moderate overlap on several attributes without full coordination |

Every cluster record now carries a `reason` string (visible in
`data/synthetic/dev/legitimate_clusters.json`) and a `shared_attributes`
list recording which attributes THIS SPECIFIC instance actually shared —
since sharing is now probabilistic, two household instances can differ
in which attributes they ended up sharing.

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
seed 42, measured, not projected, Phase 1.5 numbers):** all 100
configured clusters (60 household + 20 office + 5 campus + 15 business)
were successfully injected — see
`data/synthetic/dev/legitimate_clusters.json`. 879 of 20,000
transactions (4.4%) carry a `legitimate_cluster_id` — up from Phase 1's
287 (1.4%), per Decision 6's "increase legitimate shared-infrastructure
cases."

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
probability, 1–2 non-ring `customer_proxy` entities are attached to the
ring's shared synthetic attribute value — innocent bystanders who
coincidentally share infrastructure with a ring, **not** labeled as ring
members (`synthetic_ring_role = "decoy_bystander"`, `synthetic_ring_id`
stays null). This is what makes "shares an attribute with a flagged
ring" insufficient evidence on its own — exactly the property Phase 1F's
brief asked for ("the graph should require actual analysis").

**Phase 1.5 correction (Decision 5):** decoys are now **preferentially
sourced from legitimate-cluster members** (household/office/campus/
business) rather than an arbitrary unaffiliated customer
(`src/generator/rings.py`, `decoy_preferred_pool`) — falling back to the
general unaffiliated pool only if no legitimate-cluster candidates
remain. A decoy sourced this way keeps their `legitimate_cluster_id`
(they still legitimately belong to their household/office/etc.) — a
bystander with their OWN independent legitimate context is a more
realistic "coincidental overlap" story than a customer with no structure
at all.

**Measured in the dev dataset (Phase 1.5 numbers):** 8 of 8 configured
rings successfully injected (3 shared_device, 3 shared_bank_account, 2
multi_attribute), sizes 3–6 (see `data/synthetic/dev/rings.json`). 43 of
20,000 transactions (0.215%) are ring members; 4 are decoy bystanders.

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
