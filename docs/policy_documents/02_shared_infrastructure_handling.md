<!--
DEMO / SYNTHETIC POLICY — authored for this hackathon project only.
NOT a real Razorpay policy document. See 01_risk_investigation_policy.md
for the disclosure this applies to every document in this corpus.
-->

# Shared Infrastructure Handling (DEMO / SYNTHETIC)

## Section 1: Shared device

applies_to_pattern: shared_device

A shared device alone is not sufficient grounds to recommend escalation.
Households, and to a lesser extent offices, commonly share a phone,
tablet, or shared workstation across multiple customer accounts. A
shared-device finding should be escalated only when it co-occurs with
temporal concentration (multiple accounts transacting within a short
window) or with another shared attribute (IP or bank account) — a single
shared device with normal, spread-out transaction timing across the
group is more consistent with a household or office context than with
coordinated abuse.

## Section 2: Shared IP

applies_to_pattern: shared_ip

Shared IP addresses are the least discriminative shared-infrastructure
signal on their own — corporate NAT egress, campus WiFi, and public
hotspots routinely place many unrelated customers behind the same
address. A shared-IP finding should never, by itself, drive an
escalation recommendation. It should be treated as weak corroborating
context alongside stronger signals (shared device, shared bank account,
or temporal concentration).

## Section 3: Shared bank account

applies_to_pattern: shared_bank_account

A shared bank-account proxy is a stronger signal than a shared device or
IP, since legitimate reasons for multiple unrelated customer accounts
settling to the same bank account are comparatively rare (joint family
accounts, small businesses with a shared collections account). A
shared-bank-account finding involving three or more otherwise-unrelated
customer proxies, especially with temporal concentration, is grounds for
escalation to human review.

## Section 4: Multi-attribute overlap

applies_to_pattern: multi_attribute

When a group of customers shares more than one type of infrastructure
(for example, both a device and a bank account, or a device and an IP),
treat this as a materially stronger signal than any single shared
attribute — legitimate explanations for one shared attribute rarely
extend cleanly to a second, independent one. Multi-attribute overlap
combined with temporal concentration should be escalated.
