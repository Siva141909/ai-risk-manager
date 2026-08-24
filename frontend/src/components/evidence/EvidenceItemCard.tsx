import { ShieldCheckIcon, ClockIcon } from '../common/Icons'
import './evidence.css'
import type { EvidenceItem } from '../../types/api'

/** Deterministic evidence — solid border, shield icon
 * (docs/DESIGN_SYSTEM.md §7). Every EvidenceItem the API returns is,
 * by construction, traced to a real tool call (docs/SAFETY_MODEL.md
 * §3) — this component never renders anything else. */
export function EvidenceItemCard({ item }: { item: EvidenceItem }) {
  return (
    <div className="evidence-card">
      <div className="evidence-card-header">
        <ShieldCheckIcon />
        <span className="evidence-id">{item.evidence_id}</span>
        {item.is_retrospective && (
          <span className="evidence-retrospective" title="Includes information beyond the case's real-time cutoff">
            <ClockIcon /> retrospective
          </span>
        )}
      </div>
      <p className="evidence-summary">{item.summary}</p>
      <div className="evidence-source">Source: {item.source_tool}</div>
    </div>
  )
}

export function EvidenceList({ items }: { items: EvidenceItem[] }) {
  if (items.length === 0) {
    return <p className="evidence-empty">No evidence recorded for this investigation.</p>
  }
  return (
    <div className="evidence-list">
      {items.map((item) => (
        <EvidenceItemCard key={item.evidence_id} item={item} />
      ))}
    </div>
  )
}
