# Graph Data Model — Phase 1I/1J

NetworkX only (`src/graph/build_graph.py`) — explicitly no Neo4j (design
doc Section 13: no algorithmic need at this data volume) and no GNN
(design doc Section 14). This document describes the graph schema and
reports **diagnostics only** from the dev dataset
(`data/synthetic/dev/`) — per Phase 1J's instruction, it does **not**
claim the graph detects fraud. Two of the findings below are material
and are flagged for an explicit Phase 2 decision, not silently resolved.

---

## 1. Schema

**Nodes** (8 types, each tagged `node_type`):
`customer_proxy`, `payment_instrument_proxy`, `merchant_proxy`,
`email_domain_proxy`, `synthetic_device`, `synthetic_ip`,
`synthetic_bank_account`, `synthetic_address`. Node ID format:
`"{node_type}:{value}"` (e.g. `"synthetic_device:DEV-66516299"`), so a
value shared by two transactions collapses to the same node rather than
being duplicated.

**Edges** — one per (transaction, entity the customer touched) pair,
directed `customer_proxy → other entity`, carrying:

| Attribute | Meaning |
|---|---|
| `relationship_type` | One of `CUSTOMER_USED_PAYMENT_INSTRUMENT`, `CUSTOMER_PAID_MERCHANT`, `CUSTOMER_USED_EMAIL_DOMAIN`, `CUSTOMER_USED_DEVICE`, `CUSTOMER_USED_IP`, `CUSTOMER_USED_BANK_ACCOUNT`, `CUSTOMER_USED_ADDRESS` |
| `timestamp` | Real `TransactionDT` |
| `transaction_id` | Real `TransactionID` — the traceability anchor back to the source row |

A `MultiDiGraph` (not a simple `Graph`) because two customers can be
connected via more than one relationship type, and each edge must keep
its own transaction provenance.

---

## 2. Dev-dataset graph statistics (measured, `scripts/graph_sanity_check.py`)

20,000 transactions → **40,037 nodes, 136,799 edges**.

| Node type | Count |
|---|---|
| `customer_proxy` | 11,523 |
| `payment_instrument_proxy` | 3,744 |
| `merchant_proxy` | 5 |
| `email_domain_proxy` | 58 |
| `synthetic_device` | 6,331 |
| `synthetic_ip` | 5,374 |
| `synthetic_bank_account` | 7,127 |
| `synthetic_address` | 5,875 |

Degree distribution: median 3, mean 6.8 (skewed by hub nodes — see §3).
Highest-degree nodes are `merchant_proxy:W` (14,837), `email_domain_proxy:gmail.com`
(7,602), `email_domain_proxy:yahoo.com` (3,408) — expected, since these
have only 5 / 58 distinct values respectively and are touched by nearly
every transaction.

---

## 3. Finding 1 (material): the full graph is one giant connected component

**Measured:** `nx.connected_components` on the full undirected graph
returns **1 component containing all 40,037 nodes.** Raw
connected-components is therefore **useless for ring detection on this
graph as constructed** — it cannot distinguish anything.

**Root cause, verified:** two contributing factors.

1. `merchant_proxy` (5 values) and `email_domain_proxy` (58 values) are
   universal hub nodes — nearly every transaction touches one of a
   handful of merchant/domain nodes, bridging otherwise-unrelated
   customers instantly. Removing these two node types from the graph
   reduces it to 7 components, but one component still contains 39,938
   of 39,939 remaining nodes (99.75%).
2. **The ambient base pool assignment (Phase 1D, `docs/SYNTHETIC_DATA_GENERATION.md`
   §2) percolates on its own, independent of the hub nodes.** Tested
   directly: pushing every pool ratio from the configured
   0.55–0.95 range up to 0.90–0.999 (i.e., far closer to "everyone gets
   a unique attribute") **does not shrink the giant component** — it
   stayed at 40,453–40,865 nodes out of ~40,900 total across the tested
   ratios, barely changing. This is not a tunable-away artifact: with
   ~11,500 customer_proxy entities and 4 independent pooled attribute
   channels, even near-1:1 pooling produces `O(n)` incidental collisions
   per channel (birthday-paradox scaling), and `O(n)` edges across
   multiple channels crosses the classical random-graph
   giant-component threshold (average degree > 1) regardless of how
   tight any single channel's ratio is.

**Why this matters:** the design doc's Section 14 already anticipated
exactly this class of problem for a single attribute ("everyone on one
shared IP is one giant false ring") and mandated Louvain community
detection specifically to prevent it. This finding shows the effect is
**stronger and more structural** than that framing suggests — it is not
one oversized IP-sharing component to split, it is the *entire* graph
collapsing into one component from the combination of hub nodes and
uniform ambient pooling across multiple channels simultaneously. Raw
connected components cannot be a usable first pass at all on a graph
built this way; some form of community detection (or a restricted
subgraph, §5) is mandatory, not optional, before any ring signal can be
extracted.

**Not fixed here — flagged for Phase 2 decision.** Two candidate
directions, not chosen unilaterally:
(a) replace uniform population-wide pooling with **localized/clustered**
ambient assignment (e.g., partition customers into disjoint
neighborhood groups first, then pool only within each group), which
would produce graph structure with real locality instead of guaranteed
percolation; or
(b) accept that the full mixed-entity graph will always be one component
at this data density and design ring detection entirely around
community detection / restricted-subgraph projections (§5) rather than
connected components. This needs a lead decision, not a default.

---

## 4. Finding 2 (material): Louvain recovers legitimate clusters far better than single-attribute rings

**Measured** (`scripts/graph_sanity_check.py` + a targeted check —
see below): running `networkx.algorithms.community.louvain_communities`
(seed 42) on the full graph produces **75 communities**, sizes ranging
11–3,359 (median 291). Checking whether each injected pattern's members
land in the same community:

| Pattern | Result |
|---|---|
| All 6 checked household clusters (device+IP+address, 3 attributes) | **100% — every member in the exact same community**, every time |
| `RING-MULTI_ATTRIBUTE-000/001` (device+IP+bank_account, 3 attributes) | **100% — every core member in the same community** |
| `RING-SHARED_DEVICE-000/001/002` (1 attribute) | **Scattered across 3–5 different communities each** — not recovered |
| `RING-SHARED_BANK_ACCOUNT-000/001/002` (1 attribute) | **Scattered across 2–4 different communities each** — not recovered |

**Interpretation:** Louvain's modularity optimization is dominated by
whichever structural signal is strongest for a given node, and a single
shared-attribute edge among a customer's other ~6 edges
(payment_instrument, merchant, email, and their 3 *other*,
non-shared ambient attributes) is often not enough to pull that customer
into the same community as their ring co-members. Multi-attribute
sharing (3 simultaneous bonds) is a much stronger pull and is reliably
recovered.

**This is not a contradiction of the design doc — it is a direct,
evidence-based confirmation of a hypothesis the design doc already
stated as a reason to test for it.** Section 8 explicitly designed the
`shared_attribute` parameter to allow "1 or 2 attributes — sharing 2+ is
a stronger signal, used to test whether the graph layer weights
multi-attribute sharing correctly." This dev-dataset run is exactly that
test, run for real, and the result is: **on the full mixed-entity graph,
single-attribute rings are not detectable via plain Louvain community
membership; multi-attribute rings are.** This has a direct implication
for Phase 2 that needs an explicit decision (§5), not a silent
assumption that "the graph layer" uniformly works across all three
threat patterns in Section 4 of the design doc — today it does not, for
the two single-attribute ring types, on this graph representation.

---

## 5. Ring / legitimate-cluster overlap (as designed)

`n_ring_customer_nodes=40`, `n_legitimate_customer_nodes=224`,
`n_decoy_customer_nodes=3`. One connected component contains a mix of
ring members and legitimate/decoy entities (expected and by design — the
whole graph is one component, per §3), confirming that **raw
connectivity alone cannot separate ring members from innocent
bystanders** — exactly the property Phase 1F's brief required
("the graph should require actual analysis"). This is working as
intended; it is Finding 1 (giant component) and Finding 2 (single-attribute
rings not Louvain-separable) that need a Phase 2 answer for how analysis
beyond raw connectivity should actually work.

---

## 6. Recommendation for Phase 2 (not implemented here)

Both findings point toward the same fix direction, offered as an option
set for the lead to decide, not a decision made here:

1. Build **restricted, single-relationship-type subgraphs** (e.g., a
   customer-customer projection using only `CUSTOMER_USED_DEVICE` edges)
   for ring detection, rather than running community detection on the
   full mixed-entity graph — this would isolate the exact signal Section
   4's abuse patterns describe (shared device, shared bank account)
   instead of diluting it with merchant/email/payment-instrument noise.
2. Revisit the ambient base-pooling model (§3) — localized/clustered
   assignment instead of uniform population-wide pooling — before
   scaling this generator to the full 590,540-row benchmark, since a
   permanently-one-giant-component graph provides no useful ablation
   signal for "does the graph layer help."
3. Re-run this same sanity check once either change is made, and compare
   against these baseline numbers (75 communities, 1 giant component,
   40/224/3 ring/legit/decoy node counts) to confirm the fix actually
   changes the structural picture, not just the parameters.

Full machine-readable diagnostics: `data/synthetic/dev/graph_sanity_report.json`.
