"""Phase 5C, Requirement 10 — automated defense-only structural checks.

Companion to docs/DEFENSE_ONLY_AUDIT.md. These are static/structural
checks (route registry, tool naming, schema defaults, source-code
scans) — the same category of evidence Phase 4/5A already relied on
(CaseGroundTruth isolation, "no SQL" checks in tests/api/test_security.py),
extended here to explicitly cover "this system cannot take an offensive
or irreversible action."
"""

from __future__ import annotations

from pathlib import Path

from src.agents.safety import validate_investigation_report
from src.agents.schemas import EvidenceItem, InvestigationReport
from src.api.main import create_app
from src.tools.registry import TOOL_REGISTRY

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"

FORBIDDEN_CALL_SUBSTRINGS = [
    ".charge(", ".refund(", ".transfer(", ".payout(", ".block_account(",
    ".freeze_account(", ".disable_account(", "requests.post(", "requests.put(",
    "requests.delete(", "httpx.post(", "httpx.put(", "httpx.delete(",
    "os.system(", "subprocess.Popen(", "subprocess.check_output(", "eval(", "exec(",
]
# subprocess.check_output is used exactly once, for a fixed, argument-list
# (no shell=True), read-only `git rev-parse HEAD` provenance call
# (src/evaluation/track02_manifest.py) — allowlisted explicitly rather
# than broadening the forbidden-substring list to miss it.
ALLOWED_SUBPROCESS_FILES = {"src/evaluation/track02_manifest.py"}


def test_only_one_mutating_route_exists_and_it_is_investigate():
    """The entire API surface has exactly one non-GET route, and it can
    only ever REQUEST an investigation — never write, freeze, block, or
    otherwise act on an account/transaction."""
    app = create_app()
    mutating_routes = [
        (route.path, method)
        for route in app.routes
        for method in getattr(route, "methods", set()) or set()
        if method not in ("GET", "HEAD", "OPTIONS")
    ]
    assert mutating_routes == [("/api/v1/cases/investigate", "POST")]


def test_every_registered_tool_is_read_only_by_name():
    """Every tool the agent can call is named get_* — no write/execute/
    freeze/block/delete verb exists anywhere in the allowlist."""
    assert len(TOOL_REGISTRY) > 0
    for name in TOOL_REGISTRY:
        assert name.startswith("get_"), f"tool {name!r} is not a read-only 'get_' tool"


def test_human_approval_required_for_action_cannot_be_false():
    """The deterministic validator rejects any report claiming no human
    approval is needed — the agent structurally cannot mark its own
    recommendation as self-executing."""
    report = InvestigationReport(
        case_id="CASE-1", summary="x", trigger="x", risk_tier="LOW", graph_findings="x",
        behavioral_findings="x", legitimate_explanations=[], conflicting_evidence=False,
        conflict_description=None, policy_findings=[], recommendation="close",
        requires_human_review=False, human_approval_required_for_action=False, confidence=0.5,
        evidence=[EvidenceItem(evidence_id="CUST-AAAA1111", source_tool="get_customer_context", summary="x", is_retrospective=False)],
        retrospective_evidence_used=False, investigation_complete=True,
    )
    result = validate_investigation_report(report, {"CUST-AAAA1111"}, "CASE-1")
    assert result.passed is False
    assert any("human_approval_required_for_action" in e for e in result.errors)


def test_no_offensive_or_write_capable_code_anywhere_in_src():
    """Static scan: no file under src/ contains a call shaped like a
    payment/account-mutation action, an arbitrary shell/eval escape
    hatch, or a raw outbound write HTTP call to an external service."""
    for path in SRC_DIR.rglob("*.py"):
        rel = str(path.relative_to(PROJECT_ROOT))
        text = path.read_text()
        for token in FORBIDDEN_CALL_SUBSTRINGS:
            if token.startswith("subprocess.") and rel in ALLOWED_SUBPROCESS_FILES:
                continue
            assert token not in text, f"{rel} contains forbidden pattern {token!r}"


def test_investigation_report_schema_has_no_action_execution_field():
    """The structured output schema has no field through which the agent
    could express "I did X" for any consequential action — only
    recommend/evidence/confidence fields exist."""
    fields = set(InvestigationReport.model_fields.keys())
    forbidden_field_name_fragments = ["executed", "action_taken", "frozen_account", "blocked", "transferred", "refunded"]
    for field in fields:
        for fragment in forbidden_field_name_fragments:
            assert fragment not in field, f"unexpected action-execution-shaped field: {field}"
