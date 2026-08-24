<!--
DEMO / SYNTHETIC POLICY — authored for this hackathon project only.
NOT a real Razorpay policy document. See 01_risk_investigation_policy.md
for the disclosure this applies to every document in this corpus.
-->

# Escalation and Analyst Policy (DEMO / SYNTHETIC)

## Section 1: Recommendation categories

applies_to_pattern: general

An investigation report may recommend exactly one of: close, monitor,
investigate further, or escalate to human analyst. No recommendation
category authorizes an automated account freeze, payment block, fund
seizure, or any other irreversible action — those actions require
explicit human approval regardless of the recommendation category or
confidence level.

## Section 2: Escalate to human analyst

applies_to_pattern: general

Escalate when: (a) ML risk tier is HIGH or CRITICAL and graph evidence
corroborates it, (b) a multi-attribute shared-infrastructure group shows
temporal concentration, or (c) evidence is conflicting and the
conflict itself is material enough that a human should adjudicate it.

## Section 3: Conflicting evidence

applies_to_pattern: general

When structural evidence (for example, shared infrastructure) and
behavioral evidence (for example, normal individual transaction
history) point in different directions, do not force a single
conclusion. State plainly that the evidence is conflicting, present
both sides with their supporting evidence IDs, and recommend at least
"investigate further" — never "close" when a live, unexplained conflict
remains in the evidence.

## Section 4: Human approval boundary

applies_to_pattern: general

The system's autonomous authority is limited to producing an
investigation report and a recommendation. It never executes an
irreversible action. Any recommendation carrying real account or
financial consequence must be labeled "HUMAN APPROVAL REQUIRED" in the
output.
