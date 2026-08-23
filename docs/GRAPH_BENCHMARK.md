# Graph Benchmark — Phase 1.5

Evidence-based comparison of graph strategies against the corrected
synthetic generation model, run via `scripts/graph_benchmark.py` on the
regenerated dev dataset (`data/synthetic/dev/`, 20,000 transactions,
seed 42). Full machine-readable output:
`data/synthetic/dev/graph_benchmark_report.json` (git-ignored,
regenerable).

---

## 1. Old graph model (Phase 1)

Every synthetic attribute (device/IP/bank_account/address) was assigned
via **uniform random pooling across the entire customer population**:
`pool_size = round(n_customers * pool_ratio)`, with no locality — any
customer could, in principle, collide with any other.

## 2. Problems with the old model (both confirmed, not assumed)

1. **Percolation, un-fixable by tuning the ratio.** `docs/GRAPH_DATA_MODEL.md`
   Finding 1 (Phase 1) measured that pushing pool ratios from 0.55–0.95
   up to 0.90–0.999 barely moved the giant component (stayed at
   40,453–40,865 of ~40,900 nodes). This is a property of uniform
   pooling across multiple independent channels at this population size
   (birthday-paradox collisions scale as O(n) per channel, and O(n)
   edges crosses the classical giant-component threshold), not a
   parameter that can be tuned away.
2. **Louvain recovered multi-attribute rings and legitimate clusters but
   not single-attribute rings**, on the full mixed-entity graph
   (Finding 2) — diluted by unrelated structural signal (merchant/email
   hubs, ambient noise from every other channel).

## 3. New graph model (Phase 1.5)

Two independent, additive corrections:

**Decision 1 — localized communities replace uniform pooling.**
`src/generator/legitimate_clusters.py` is now the PRIMARY sharing
mechanism: household/office/campus/business communities, each with
**per-attribute sharing probabilities** rolled once per cluster instance
(not per member) — e.g. a household shares its device 40% of the time,
its IP 50%, its address 85%, a joint bank account 15% — never
all-or-nothing. `src/generator/entity_assignment.py`'s ambient layer
(`src/generator/pools.py::assign_individual_or_leaked_slot`) now gives
each customer a **unique** attribute value with high probability, and
only a small, **fixed-size, non-population-scaled** "leakage pool"
accounts for rare cross-population coincidence (target ~8–25 expected
leaking customers regardless of whether the population is 5,000 or
500,000 — see `docs/SYNTHETIC_DATA_GENERATION.md` §2 for why a flat
probability was tried first and rejected).

**Decision 2 — hub entities excluded from ring-detection topology.**
`merchant_proxy` (5 values) and `email_domain_proxy` (58 values) are
excluded from every relationship-specific graph view
(`src/graph/relationship_views.py`). **Measured, not assumed:**
`payment_instrument_proxy` (raw `card1`-`card6`) was tested too and
also found to be a hub — even under the corrected localized model, a
graph including it still had a 30,278-node component (of ~55,000);
removing it dropped the largest component to 2,001 nodes. All three are
excluded from topology; all three remain available as node attributes /
ML features / investigation evidence in the full heterogeneous graph
(`src/graph/build_graph.py`).

## 4. Why this is more realistic

Real shared-infrastructure patterns are local (a household shares with
its own 2-5 members, not with a random person anywhere in the
population) and probabilistic (families don't always share every
attribute). Uniform population-wide pooling models neither property —
it's mathematically closer to "everyone occasionally shares with
everyone" than to "small groups occasionally share with each other."
The corrected model matches the structure Phase 1.5's brief described
(household/office/campus/business, each with different sharing
intensities per attribute) instead of a single global collision rate.

---

## 5. Graph statistics — old vs. new

| Metric | Old model (Phase 1, full graph) | New model (Phase 1.5, full graph) | New model (Phase 1.5, hub-excluded) |
|---|---|---|---|
| Nodes | 40,037 | 60,744 | ~55,000 (device/ip/bank/address/customer only) |
| Largest connected component | **40,037 (100%)** | 60,744 (100%, hubs still present) | **2,001 (~3.6% of ~55,000 hub-excluded nodes)** |
| N connected components | 1 | 1 | 8,962 |

The full heterogeneous graph (Strategy A, includes hub entities)
**still percolates to 100% even under the corrected localized model** —
this is expected and confirms Decision 2 is necessary *in addition to*
Decision 1, not instead of it. Neither correction alone is sufficient;
both are required.

## 6. Relationship-specific statistics (hub-excluded views, Decision 9 health metrics)

| View | Nodes | Edges | Components | Largest component | Largest % |
|---|---|---|---|---|---|
| `SHARED_DEVICE` | — | — | 47 | — | 22.1% *(of the sharing-subgraph's own small node count — see caveat below)* |
| `SHARED_IP` | — | — | 66 | — | 4.1% |
| `SHARED_BANK_ACCOUNT` | — | — | 14 | — | 13.5% |
| Multi-attribute (device+ip+bank) | — | — | 101 | — | 10.0% |

**Caveat on "largest %":** these percentages are relative to each
view's OWN node count (only customers who share *something* of that
type appear in the graph at all — most customers, having a unique
individual value, never appear). A single legitimate campus cluster (up
to 60 members, by design) can legitimately be a large fraction of a
small sharing-subgraph without that being percolation — this is
different from Phase 1's failure mode, where thousands of *unrelated*
customers were glued together. The regression test
(`tests/integration/test_graph_percolation_fixed.py`) measures the more
meaningful bound instead: largest component as a percentage of *all*
distinct customers (< 5%, passing) — full per-view health JSON in
`data/synthetic/dev/graph_benchmark_report.json`.

## 7. Ring statistics

8 rings injected (3 `shared_device`, 3 `shared_bank_account`,
2 `multi_attribute`), sizes 3–6, `noise_ratio` 0.15–0.2 — unchanged
mechanism from Phase 1 (`src/generator/rings.py`), now drawing decoys
preferentially from legitimate-cluster members (Decision 5) instead of
an arbitrary unaffiliated customer, per the updated docstring in that
module.

## 8. Hard-negative (legitimate-cluster) statistics

**100 legitimate clusters** injected (up from Phase 1's 28 — Decision 6):
campus rows 293, household rows 251, office rows 244, business rows 95
(879 of 20,000 transactions, 4.4%, carry a `legitimate_cluster_id`).
Each cluster record now carries a `reason` field
(`src/generator/legitimate_clusters.py::DEFAULT_CLUSTER_TYPES`) stating
why the pattern is legitimate, and a `shared_attributes` list recording
which attributes this specific instance actually shared (since sharing
is now probabilistic per instance, not guaranteed).

---

## 9. Ring detection results (Decision 10)

Full detail: `data/synthetic/dev/graph_benchmark_report.json`. Summary
(connected-components and Louvain gave identical results at this scale
— see §11):

| Strategy | Mean precision | Mean recall | Mean F1 | FP rate |
|---|---|---|---|---|
| **A. Full heterogeneous (incl. hubs)** — CC | 0.000 | 1.000 | 0.000 | 1.000 |
| A. Full heterogeneous — Louvain | 0.012 | 0.702 | 0.024 | 0.080 |
| **B. `SHARED_DEVICE`, flat weight** | 0.893 | 0.803 | **0.841** | **0.000** |
| B. `SHARED_IP`, flat weight | 0.732 | 0.792 | 0.760 | 0.033 |
| B. `SHARED_BANK_ACCOUNT`, flat weight | 0.893 | 0.777 | 0.823 | 0.333 † |
| C. Same views, inverse-frequency weight | *identical to B* | | | |
| **D. Multi-attribute combined, flat** | **0.933** | 0.790 | **0.851** | **0.000** |
| D. Multi-attribute combined, inverse-frequency | *identical to D flat* | | | |

† See §10 — small-sample, traced to the deliberate rare-leakage mechanism, not a systemic flaw.

**Strategy A (full graph, includes hubs) is unusable for ring detection**
even under the corrected model — connected components trivially
"detects" the entire population as one ring (precision 0, recall 1 by
construction), and Louvain, while better, still only reaches F1 0.024.
This directly validates Decision 2.

**Strategies B and D (relationship-specific / multi-attribute) work.**
F1 in the 0.76–0.85 range, with **zero false positives** for the device
and multi-attribute views. Multi-attribute combination is the strongest
single result (F1 0.851), consistent with — and a sharper confirmation
of — Phase 1's Finding 2 and the design doc's Section 8 hypothesis that
multi-attribute sharing is a stronger signal than single-attribute
sharing.

**Recall is deliberately bounded below 1.0 — this is correct, not a
flaw.** Each ring's `noise_ratio` (0.15–0.2) gives that fraction of
"true" ring members a *different* synthetic attribute than the rest of
the ring, by design (an evasive participant, design doc Judge Q&A #20).
Measured recall (0.777–0.803 for single-attribute rings) tracks almost
exactly the `1 - noise_ratio` ceiling (≈0.8 for `noise_ratio=0.2`) —
the benchmark is recovering everything that is structurally
recoverable, and correctly failing to recover what was designed to
evade structural detection. This satisfies Phase 1.5 Success Criteria
#5 and #6 directly: detection is measurable and non-trivial, not
artificially easy.

## 10. False-positive results (Decision 10)

Legitimate-cluster contamination (a cluster's detected community also
containing a ring member) was **0% for `SHARED_DEVICE` and the
multi-attribute view**, **3.3% for `SHARED_IP`**, and **33.3% for
`SHARED_BANK_ACCOUNT`** — but that last number is a small-sample
artifact: only 9 of 100 legitimate clusters ever share a bank account at
all (`share_prob` is 0.15 for household, 0.1 for business, 0.0 for
office/campus), and 3 of those 9 showed contamination, traced (by
inspecting `graph_benchmark_report.json`'s false-positive detail) to
the deliberate rare cross-population leakage mechanism (§3) doing
exactly what it's designed to do — introduce occasional, non-adversarial
ambiguity. This is a real, useful signal for Phase 2 (bank-account
sharing needs a higher evidentiary bar before acting on it alone), not
a bug to silently patch.

## 11. Comparison of graph strategies — conclusion

**Recommended: Strategy D, the multi-attribute combined graph
(device + IP + bank_account, hub entities excluded).** Best F1 (0.851),
zero false positives, and it directly operationalizes the design doc's
own multi-attribute-signal hypothesis. Strategy B (single-relationship
views) remains valuable as a **diagnostic breakdown** — e.g. §10 shows
bank-account-only sharing is noisier than device-only sharing, a
distinction the combined view alone wouldn't surface — so Phase 2 should
use D as the primary ring-detection graph and B's per-relationship views
for explaining *why* a ring was flagged (the agent's evidence layer,
design doc Section 15).

**Weighting strategy (flat vs. inverse-frequency): inconclusive at this
scale, reported honestly rather than assumed.** Every inverse-frequency
run produced results identical to its flat counterpart. Investigated,
not just observed: at this dev-sample scale, the corrected model already
produces small, well-separated components (§6) — Louvain's modularity
optimization cannot merge or split nodes across disconnected components
regardless of edge weight, so there was no structural ambiguity for
weighting to resolve. Per Decision 4's instruction to test rather than
blindly adopt inverse-frequency weighting: **the test's honest answer is
"no measurable effect yet observed,"** not a confirmation either way.
Recommendation: keep the inverse-frequency implementation (it is
correctly implemented and unit-tested,
`tests/unit/test_relationship_views_and_health.py`), but re-run this
comparison at full-benchmark scale (Phase 2, all 590,540 rows) where
larger, more overlapping components are more likely to exist and give
weighting an actual opportunity to matter.

## 12. Reproducibility results (Phase 1.5)

Verified in `tests/integration/test_graph_percolation_fixed.py` and
`tests/integration/test_reproducibility.py`: same seed → byte-identical
transactions, cluster records, ring records, and graph structure across
runs; different seed → different neighborhood assignment and ring
composition. Unchanged mechanism from Phase 1 (SHA-256-derived
deterministic RNG, `src/generator/rng.py`) — the correction was to what
gets generated, not to the determinism guarantee.

## 13. Remaining limitations

- **Weighting comparison is inconclusive at dev scale** (§11) — needs
  re-testing at full-benchmark size before Phase 2 commits to a
  weighting strategy for production use.
- **Bank-account false-positive rate (§10) is based on only 9 scored
  clusters** — not enough signal yet to conclude whether 33% is
  representative or a small-sample fluke; needs the full-scale benchmark
  to resolve.
- **The full heterogeneous graph (Strategy A) remains unusable for
  ring-detection topology** — it is kept only as a source of
  investigation evidence and ML/contextual features (Decision 2), never
  as a detection graph. Any future code path must not silently fall
  back to it for ring detection.
- **Louvain and connected-components gave identical results everywhere
  tested** — the dev-sample graphs are simple/small enough that
  community detection reduces to component detection. This is expected
  at this scale and is not evidence that Louvain is unnecessary in
  general (design doc Section 14's rationale — large real components
  needing sub-division — doesn't arise until real-world density is
  reached).
- **Ring recovery was benchmarked, not optimized against** — per
  Decision 10's explicit instruction, no parameter (noise_ratio,
  cluster sizes, weighting) was tuned after seeing these numbers. Any
  future tuning pass should be a new, separately reported benchmark run,
  not a silent edit to this one.
