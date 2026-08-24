<!--
DEMO / SYNTHETIC POLICY — authored for this hackathon project only.
This is NOT a real Razorpay policy document and must never be presented,
cited, or represented as one. It exists solely to give the investigation
agent (Phase 4) something real to retrieve and cite, so that a policy
citation in a generated report is traceable to an actual, inspectable
document rather than invented.
-->

# Risk Investigation Policy (DEMO / SYNTHETIC)

## Section 1: Scope

applies_to_pattern: general

This policy governs how a flagged transaction case should be
investigated before a recommendation is made to a human analyst. It
applies to every case regardless of which detection layer (rules, ML,
or graph) produced the flag.

## Section 2: Evidence standard

applies_to_pattern: general

A recommendation must be grounded in evidence returned by an approved
tool call, with a stable evidence ID. An investigation report that
references a fact without a corresponding evidence ID does not meet the
evidence standard and should not be finalized — it must be routed to
human review instead of being auto-approved.

## Section 3: Confidence and uncertainty

applies_to_pattern: general

Confidence should reflect how completely the case was investigated (how
much relevant evidence was found and how consistent it is), not how
convinced the model "feels." A case investigated with incomplete data
(a tool failure, or a limit reached on the number of evidence lookups)
must report a capped confidence and note the limitation explicitly,
never present incomplete evidence as if it were complete.
