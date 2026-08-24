"""Phase 4E — the real-time / retrospective temporal boundary.

Every case carries three timestamps. `real_time_cutoff` governs what
tool calls may use to justify the ORIGINAL risk decision (the
`ml_risk_score`/`ml_risk_tier` already frozen by Phase 2/3 — this
boundary does not recompute them, it governs what the AGENT's
investigation may additionally treat as "known at decision time").
Anything queried without that cutoff is retrospective investigation
evidence and must be labeled as such — never silently treated as if it
justified the original decision.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InvestigationCutoff:
    case_event_time: int  # the trigger transaction's real TransactionDT
    real_time_cutoff: int  # == case_event_time; tool calls made in "real-time mode" must filter to TransactionDT < this
    retrospective_investigation_cutoff: int | None  # None == no upper bound (query everything known, including "future" data)

    @classmethod
    def for_case(cls, trigger_transaction_dt: int) -> "InvestigationCutoff":
        return cls(
            case_event_time=trigger_transaction_dt,
            real_time_cutoff=trigger_transaction_dt,
            retrospective_investigation_cutoff=None,
        )

    def cutoff_for_mode(self, mode: str) -> int | None:
        """Returns the cutoff_dt to pass to a tool call for the given mode."""
        if mode == "real_time":
            return self.real_time_cutoff
        if mode == "retrospective":
            return self.retrospective_investigation_cutoff
        raise ValueError(f"unknown investigation mode: {mode!r} (expected 'real_time' or 'retrospective')")
