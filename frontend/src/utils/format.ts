import type { EvidenceItem, RiskTier } from '../types/api'

export function formatScorePercent(score: number): string {
  return `${(score * 100).toFixed(1)}%`
}

export function formatConfidencePercent(confidence: number): string {
  return `${Math.round(confidence * 100)}%`
}

/** Thousands-separated integer display (docs/UX_IMPROVEMENT_PLAN.md Issue 2) —
 * StatTile/table counts otherwise render as unbroken digit strings. */
export function formatCount(n: number): string {
  return n.toLocaleString('en-IN')
}

/** TransactionDT is relative seconds, not a wall-clock timestamp — this
 * dataset has no real dates (docs/API.md). Shown as a labeled relative
 * value, never disguised as a calendar date. */
export function formatTransactionDt(dt: number): string {
  const days = Math.floor(dt / 86400)
  const hours = Math.floor((dt % 86400) / 3600)
  return `T+${days}d ${hours}h (dt=${dt})`
}

export function riskTierLabel(tier: RiskTier | string): string {
  return tier.charAt(0) + tier.slice(1).toLowerCase()
}

export function relationshipTypeLabel(type: string): string {
  const map: Record<string, string> = {
    SHARED_DEVICE: 'Shared Device',
    SHARED_IP: 'Shared IP',
    SHARED_BANK_ACCOUNT: 'Shared Bank Account',
  }
  return map[type] ?? type
}

/** Groups an InvestigationReport's evidence into "timeline-relevant"
 * items (from transaction/temporal-history tools) vs. everything else
 * — the Investigation Timeline section is a VIEW of already-fetched
 * evidence, not a new data source (docs/FRONTEND_UX.md §3, API GAP note). */
export function timelineEvidence(evidence: EvidenceItem[]): EvidenceItem[] {
  return evidence.filter((e) => e.source_tool === 'get_transaction_history' || e.source_tool === 'get_temporal_activity')
}

export function nonTimelineEvidence(evidence: EvidenceItem[]): EvidenceItem[] {
  return evidence.filter((e) => e.source_tool !== 'get_transaction_history' && e.source_tool !== 'get_temporal_activity')
}
