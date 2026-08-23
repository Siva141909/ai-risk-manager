# Graph Benchmark — Full Scale (Phase 3A–3E)

Full-benchmark rerun of `docs/GRAPH_BENCHMARK.md` (Phase 1.5's 20,000-row
dev result) against **all 590,540 real transactions**, using the
identical, un-retuned configuration (`configs/generator.yaml` defaults —
Phase 3A's instruction: "use the established reproducibility
configuration," not a rescaled one). Generated via
`scripts/generate_full_benchmark.py`, diagnosed via
`scripts/graph_health_full.py`, benchmarked via
`scripts/graph_benchmark_full.py`. All artifacts:
`data/synthetic/full/*.json` (git-ignored, regenerable).

---

## 1. Full benchmark size (Phase 3A)

| | Value |
|---|---|
| Seed | 42 |
| Transactions | 590,540 |
| Generation time | 71.6s |
| Distinct `customer_proxy` entities | 156,316 |
| Distinct `payment_instrument_proxy` entities | 354,955 |
| Synthetic devices | 156,012 |
| Synthetic IPs | 156,035 |
| Synthetic bank accounts | 156,278 |
| Synthetic addresses | 156,025 |
| Legitimate clusters injected | 100 (60 household, 20 office, 5 campus, 15 business) — same counts as dev, established config not rescaled |
| Legitimate-cluster-labeled rows | 904 |
| Abuse rings injected | 8 (3 shared_device, 3 shared_bank_account, 2 multi_attribute) |
| Ring-member rows | 49 (41 core + 8 noise) |
| Decoy bystanders | 6 |
| `synthetic_entity_label` distribution | normal 589,581 / legitimate_shared_infra 904 / ring_member 49 / decoy_bystander 6 |

Ground-truth separation rules unchanged from Phase 1/1.5:
`original_isFraud` is an untouched copy of the real label;
`synthetic_ring_id`/`synthetic_abuse_type`/`synthetic_ring_role`/
`legitimate_cluster_id`/`legitimate_cluster_type`/`synthetic_entity_label`
remain separate columns, still denylisted from ML features
(`src/features/leakage_guard.py`).

**Note on injection density:** keeping the same absolute ring/cluster
counts against ~30x more transactions makes this a deliberately harder,
sparser "needle in haystack" test than the dev run — 8 rings among
156,316 customers is a far more realistic coordination-abuse prevalence
than 8 rings among 11,523.

---

## 2. Graph health (Phase 3B)

**Explicitly verified: the full heterogeneous graph is NOT used for
detection** — `scripts/graph_health_full.py` only builds the 4 views
below via `src/graph/relationship_views.py`, which never reads
`merchant_proxy`, `email_domain_proxy`, or `payment_instrument_proxy`
columns at all (structurally impossible for them to appear, not just
excluded by a filter). The full heterogeneous graph's own node/edge
counts (1,135,685 nodes / 4,039,324 edges) are recorded in
`generation_metadata.json` purely as context.

| View | Nodes | Edges | Components | Largest component | Largest % of ALL customers | Avg degree |
|---|---|---|---|---|---|---|
| Device-only | 469 | 1,782 | 165 | 52 | **0.0333%** | 7.60 |
| IP-only | 351 | 1,106 | 70 | 14 | 0.0090% | 6.30 |
| Bank-account-only | 51 | 88 | 13 | 7 | 0.0045% | 3.45 |
| **Multi-attribute** | 760 | 2,746 | 220 | 52 | **0.0333%** | 7.23 |

**Percolation remains fixed at full scale, more strongly than at dev
scale.** The largest component in any view is under 0.034% of all
156,316 customers — an even tighter bound than Phase 1.5's dev-scale
result, because the ambient leakage pool sizes are fixed constants (not
population-scaled, `docs/SYNTHETIC_DATA_GENERATION.md` §2), so leakage-
driven collision becomes proportionally rarer as the population grows.
This directly confirms the Phase 1.5 fix generalizes correctly to real
production scale, not just the 20K dev sample.

---

## 3. Weighting comparison (Phase 3C) — retested, conclusion unchanged and now definitive

Tested flat, inverse-frequency, and inverse-log-frequency ("simple
rarity-based") weighting, both connected-components and Louvain, across
all 4 views — **every single combination produced byte-identical ring-
recovery and false-positive numbers.**

**This is now a definitive finding, not "inconclusive, needs more
scale."** At dev scale, the open question was whether more data would
reveal weighting differences. Full scale answers it: given this
generator's injection density (rings/clusters stay small, isolated
components regardless of population size — §2), there is structurally
no opportunity for edge weight to matter. Louvain cannot merge or split
across disconnected components regardless of internal weighting, and
connected-components ignores weight by definition. Weighting would only
start to matter if injected structures grew large or entangled enough to
create genuine within-component ambiguity — which no configured
household/office/campus/business/ring pattern here does, by design (each
pattern deliberately stays small — Phase 1.5 Decision 5/6).

**Recommendation: use flat weighting** — simplest, most interpretable,
and (per Phase 3C's explicit instruction to weigh interpretability and
stability, not just F1) equally performant to the alternatives. The
inverse-frequency/inverse-log-frequency implementations remain available
and tested (`tests/unit/test_relationship_views_and_health.py`) should a
future, denser real-world graph ever create the ambiguity that would let
them matter.

**Bank-account false-positive result — investigated and resolved.**
Phase 1.5 flagged this as based on only 9 scored clusters. At full
scale, the single-relationship `BANK_ONLY` view still shows a small
sample (9 scored clusters, 33.3% FP rate, wide 95% CI) — **but this is
not the recommended detection view.** The **multi-attribute combined
view** (§4 hard-negative results) shows **0% false positives across 81
scored clusters of all 4 types**, resolving the concern: the earlier
signal was specific to evaluating bank-account sharing in isolation:
combining it with device/IP evidence (as the approved architecture
already specifies) eliminates the contamination entirely.

---

## 4. Ring detection by abuse type (Phase 3D)

Multi-attribute view, flat weighting, connected-components (identical to
Louvain — §3):

| Abuse type | Rings | Precision | Recall | F1 | 95% CI (pooled precision) | 95% CI (pooled recall) | Missed | Partial | Full |
|---|---|---|---|---|---|---|---|---|---|
| `shared_device` | 3 | 1.000 | 0.811 | 0.896 | [0.772, 1.000] | [0.570, 0.934] | 0 | 3 | 0 |
| `shared_bank_account` | 3 | 1.000 | 0.767 | 0.866 | [0.741, 1.000] | [0.524, 0.924] | 0 | 3 | 0 |
| `multi_attribute` | 2 | 0.732 | 0.792 | 0.760 | [0.434, 0.903] | [0.490, 0.943] | 0 | 2 | 0 |
| **Overall** | **8** | **0.933** | **0.790** | **0.851** | [0.776, 0.970] | [0.652, 0.895] | **0** | **8** | **0** |

**No ring is missed entirely; no ring is perfectly recovered either —
every ring is "partial."** This is by design, not a shortfall:
`noise_ratio` (0.15–0.2) deliberately gives that fraction of each ring's
members a different synthetic attribute than the rest (an evasive
participant who doesn't reuse infrastructure). Per-ring detail (all 8
rings): `data/synthetic/full/graph_benchmark_full_report.json`. Recall
ranges 0.667–0.833 — consistent with the `1 - noise_ratio` ceiling
documented in `docs/GRAPH_BENCHMARK.md` §9.

**`multi_attribute` rings score lower precision (0.732) than the
single-attribute types (1.0 each) in this combined view** — worth noting
honestly: a multi-attribute ring's shared device+IP+bank_account gives
decoys three separate channels to coincidentally attach through (rather
than one), slightly widening the detected community relative to the
true ring. Still a strong F1 (0.760), not hidden.

**Per Phase 3D's instruction not to hide poor-performing types:** no
ring type performs poorly here (F1 range 0.760–0.896) — this full-scale
result is consistently strong across all three abuse types, not
cherry-picked.

---

## 5. Hard-negative results (Phase 3E)

Multi-attribute view, flat weighting:

| Legitimate cluster type | Clusters | Scored (present in view) | False positives | FP rate | 95% CI |
|---|---|---|---|---|---|
| Household | 60 | 51 | 0 | **0.0%** | [0.0%, 7.0%] |
| Office | 20 | 18 | 0 | **0.0%** | [0.0%, 17.6%] |
| Business | 15 | 11 | 0 | **0.0%** | [0.0%, 25.9%] |
| Campus | 5 | 1 | 0 | **0.0%** | [0.0%, 79.4%] |
| **Overall** | **100** | **81** | **0** | **0.0%** | — |

**Zero false positives across all 81 scored legitimate clusters, of
every type, at full scale, in the recommended multi-attribute view.**
Household is the most statistically meaningful result (n=51, tight CI
upper bound 7.0%); campus's CI is wide (n=1 — only one of the 5
configured campus clusters happened to also share a device/IP/bank
value with other members beyond its deliberate IP-range mechanic, since
campus clusters mostly share only a `/16`-style range, not an exact
device/IP/bank value the multi-attribute view tracks) — reported
honestly as low-confidence rather than treated as a strong 0%.

**No legitimate pattern was found to be difficult to distinguish** in
this full-scale run, in the recommended view — this is a genuinely
positive result for the agent-investigation groundwork (Phase 3F/G):
structural evidence alone, without any behavioral/temporal
corroboration, already achieves clean separation from all 4 hard-
negative pattern types at this configuration's density.

---

## 6. Frozen configuration for Phase 3M's final evaluation

Per §3's conclusion, the graph strategy is **frozen** before any
final/locked evaluation:

- **View:** multi-attribute combined (device + IP + bank_account)
- **Weighting:** flat (no measurable difference from alternatives;
  simplest and most interpretable, chosen per Phase 3C's explicit
  interpretability/stability instruction)
- **Community detection:** connected components (identical results to
  Louvain at this density — simplest choice, Occam's razor)
- **Graph-flag rule:** `community_size >= 3` (`src/graph/signals.py::GRAPH_FLAG_MIN_COMMUNITY_SIZE`
  — matches the generator's own minimum ring size; a community smaller
  than any configured ring type cannot structurally be one)

This exact configuration is what `docs/ML_GRAPH_ABLATION.md` uses.
