# Graph Data Model — Phase 1I/1J (Phase 1.5: Findings 1 & 2 resolved)

NetworkX only (`src/graph/build_graph.py`,
`src/graph/relationship_views.py`) — explicitly no Neo4j (design doc
Section 13) and no GNN (design doc Section 14). This document describes
the graph schema; **the current ring-detection performance numbers now
live in `docs/GRAPH_BENCHMARK.md`**, which supersedes this document's
old §3/§4 diagnostics-only findings with a resolved, measured
comparison. §3/§4 below are kept as history — both findings they
describe are now **resolved** in Phase 1.5, not still-open decisions.

---

## 1. Schema

### 1a. Full heterogeneous graph (`src/graph/build_graph.py`) — evidence/context graph

**Nodes** (8 types, each tagged `node_type`): `customer_proxy`,
`payment_instrument_proxy`, `merchant_proxy`, `email_domain_proxy`,
`synthetic_device`, `synthetic_ip`, `synthetic_bank_account`,
`synthetic_address`. Node ID format: `"{node_type}:{value}"`.

**Edges** — one per (transaction, entity touched) pair, directed
`customer_proxy → other entity`, carrying `relationship_type`,
`timestamp` (real `TransactionDT`), `transaction_id` (real
`TransactionID`, the traceability anchor).

**Phase 1.5 status change: this graph is investigation/ML-feature
evidence only — it is explicitly NOT used for ring-detection topology.**
`merchant_proxy`, `email_domain_proxy`, and (newly confirmed,
`docs/GRAPH_BENCHMARK.md` §3) `payment_instrument_proxy` all act as hub
nodes that percolate the graph into one giant component regardless of
the ambient-assignment fix (§3 below). Ring detection now runs on the
relationship-specific views instead (1b).

### 1b. Relationship-specific projections (`src/graph/relationship_views.py`) — ring-detection graphs

Customer-customer projections, one per relationship type
(`SHARED_DEVICE`, `SHARED_IP`, `SHARED_BANK_ACCOUNT`), plus a combined
multi-attribute view. Nodes are bare `customer_proxy_id` values (no
prefix). An edge exists only if two customers share the same
`device_synthetic_id` / `ip_synthetic_id` / `bank_account_synthetic_id`
value; edge attributes: `weight` (see §5), `relationship_type` (or
`relationship_types` list for the combined view), and `evidence` (the
shared value(s) and how many customers share each — traceability, same
principle as the full graph's `transaction_id`).

---

## 2. Dev-dataset graph statistics (Phase 1.5 model, `data/synthetic/dev/`)

20,000 transactions → **60,744 nodes, 136,799 edges** (full
heterogeneous graph — node count rose from Phase 1's 40,037 because the
corrected ambient model now gives most customers their own unique
device/IP/bank_account/address instead of pooling them into fewer
shared nodes; see `docs/SYNTHETIC_DATA_GENERATION.md` §2).

| Node type | Count |
|---|---|
| `customer_proxy` | 11,523 |
| `payment_instrument_proxy` | 3,744 |
| `merchant_proxy` | 5 |
| `email_domain_proxy` | 58 |
| `synthetic_device` | 11,336 |
| `synthetic_ip` | 11,244 |
| `synthetic_bank_account` | 11,485 |
| `synthetic_address` | 11,349 |

Full relationship-specific and multi-attribute view statistics (node/edge
counts, component counts, degree distributions) are in
`docs/GRAPH_BENCHMARK.md` §6 and `data/synthetic/dev/graph_benchmark_report.json`.

---

## 3. Finding 1 (Phase 1, RESOLVED in Phase 1.5): the full graph was one giant connected component

**Original finding (Phase 1):** `nx.connected_components` on the full
graph returned 1 component containing all 40,037 nodes — driven by hub
nodes (merchant/email) AND independently by uniform ambient pooling
across the whole customer population (confirmed by testing pool ratios
up to 0.999 with no improvement).

**Resolution (Phase 1.5, Decisions 1 and 2), verified:**
- Decision 1 replaced uniform pooling with mostly-individual assignment
  plus a small, population-size-independent leakage pool
  (`docs/SYNTHETIC_DATA_GENERATION.md` §2) and localized
  household/office/campus/business communities as the primary sharing
  mechanism (§3 of the same doc).
- Decision 2 excludes hub entity types from ring-detection topology
  (§1a above).
- **Both were necessary — neither alone was sufficient.** Measured: the
  full heterogeneous graph (hubs included) STILL percolates to 100%
  even under the corrected Decision-1 ambient model
  (`docs/GRAPH_BENCHMARK.md` §5). Only once hub entities were also
  excluded did the largest component drop to ~2,000 of ~55,000 hub-excluded
  nodes, and the per-relationship views (§1b) show largest components at
  4–22% of their own (much smaller) sharing-subgraphs, or under 5% of
  ALL distinct customers (the regression-tested bound,
  `tests/integration/test_graph_percolation_fixed.py`).

**Status: RESOLVED.** Full numbers: `docs/GRAPH_BENCHMARK.md` §5–6.

---

## 4. Finding 2 (Phase 1, RESOLVED in Phase 1.5): Louvain didn't recover single-attribute rings on the full graph

**Original finding (Phase 1):** on the full mixed-entity graph, Louvain
recovered multi-attribute rings and legitimate clusters (100% of members
in the same community) but scattered single-attribute ring members
across 2–5 different communities each — diluted by unrelated structural
signal (merchant/email/payment-instrument edges, and every OTHER
ambient attribute a customer had).

**Resolution (Phase 1.5, Decision 3), verified:** running ring detection
on the relationship-specific views instead of the full graph — where the
signal isn't diluted by unrelated edge types — recovers single-attribute
rings directly: mean F1 0.760–0.841 across `SHARED_DEVICE`,
`SHARED_IP`, `SHARED_BANK_ACCOUNT` (`docs/GRAPH_BENCHMARK.md` §9). The
original hypothesis this finding tested — "multi-attribute sharing is a
stronger signal than single-attribute sharing" (design doc Section 8) —
is now confirmed even more sharply: the multi-attribute combined view
scores highest (F1 0.851, zero false positives).

**Status: RESOLVED**, with a nuance carried forward: recall for
single-attribute rings is bounded below 1.0 by the ring generator's own
`noise_ratio` (deliberately evasive members) — this is correct behavior,
not a remaining gap. See `docs/GRAPH_BENCHMARK.md` §9.

---

## 5. Edge weighting (Decision 4) — see `docs/GRAPH_BENCHMARK.md` §11

Two strategies implemented in `src/graph/relationship_views.py`: `flat`
(a fixed prior per relationship type — device/bank_account high,
IP moderate, address moderate/low) and `inverse_frequency` (prior scaled
by `1/n_sharing`, so a pair sharing an attribute with only 1 other
customer counts more than a pair sharing it with hundreds). Tested, not
assumed: at dev-sample scale, both strategies produced identical ring
recovery results everywhere measured — investigated and explained in
`docs/GRAPH_BENCHMARK.md` §11 (the corrected model already produces
small, disconnected components, giving weighting no structural ambiguity
to resolve). Re-test at full-benchmark scale before Phase 2 commits to
either strategy for production use.

---

## 6. Recommendation for Phase 2

Superseded by `docs/GRAPH_BENCHMARK.md` §11's evidence-based
recommendation: use the multi-attribute combined view (Strategy D) as
the primary ring-detection graph, keep the single-relationship views for
per-attribute evidence/explanation, and never fall back to the full
heterogeneous graph for detection topology. Remaining open items before
Phase 2 commits further: re-run the weighting comparison and the
bank-account false-positive rate at full-benchmark scale
(`docs/GRAPH_BENCHMARK.md` §13).
