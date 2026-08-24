<!--
DEMO / SYNTHETIC POLICY — authored for this hackathon project only.
NOT a real Razorpay policy document. See 01_risk_investigation_policy.md
for the disclosure this applies to every document in this corpus.
-->

# False-Positive Guidance (DEMO / SYNTHETIC)

## Section 1: Household context

applies_to_pattern: shared_device

Multiple customer accounts sharing a device and address, with normal
(not tightly clustered) transaction timing and no concentration of
high-risk categories, is the canonical legitimate false positive for
shared-device detection. Do not recommend escalation on this pattern
alone; note it explicitly as a plausible household explanation in the
investigation report.

## Section 2: Office / campus context

applies_to_pattern: shared_ip

A large number of otherwise-unrelated customers sharing only an IP
address or IP range, with distinct devices, bank accounts, and normal
transaction timing, is consistent with an office or campus network.
This should be labeled a likely legitimate explanation, not treated as
inconclusive.

## Section 3: When NOT to assume false positive

applies_to_pattern: general

A plausible legitimate explanation does not, by itself, close a case
that also carries elevated ML risk or multi-attribute overlap. A
legitimate-looking shared-infrastructure pattern and an elevated
individual-transaction risk score can both be true at once — report
both and let a human analyst weigh them, rather than letting one
explanation silently override the other.
