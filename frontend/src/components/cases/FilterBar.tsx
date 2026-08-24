import { Button } from '../common/Button'
import type { CaseListParams, RiskTier } from '../../types/api'
import './cases.css'

const RISK_TIERS: RiskTier[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

export function FilterBar({
  filters,
  onChange,
}: {
  filters: CaseListParams
  onChange: (next: CaseListParams) => void
}) {
  const hasActiveFilters = Boolean(
    filters.risk_tier || filters.graph_flagged !== undefined || filters.investigation_status || filters.start_dt || filters.end_dt
  )

  return (
    <div className="filter-bar">
      <div className="filter-chip-group">
        {RISK_TIERS.map((tier) => (
          <button
            key={tier}
            type="button"
            className={`filter-chip ${filters.risk_tier === tier ? 'active' : ''}`}
            onClick={() => onChange({ ...filters, risk_tier: filters.risk_tier === tier ? undefined : tier, offset: 0 })}
          >
            {tier}
          </button>
        ))}
      </div>

      <select
        value={filters.graph_flagged === undefined ? '' : String(filters.graph_flagged)}
        onChange={(e) =>
          onChange({ ...filters, graph_flagged: e.target.value === '' ? undefined : e.target.value === 'true', offset: 0 })
        }
        aria-label="Graph flag filter"
      >
        <option value="">Graph: any</option>
        <option value="true">Graph flagged</option>
        <option value="false">No graph evidence</option>
      </select>

      <select
        value={filters.investigation_status ?? ''}
        onChange={(e) => onChange({ ...filters, investigation_status: (e.target.value || undefined) as CaseListParams['investigation_status'], offset: 0 })}
        aria-label="Investigation status filter"
      >
        <option value="">Status: any</option>
        <option value="investigated">Investigated</option>
        <option value="not_investigated">Not investigated</option>
      </select>

      <input
        type="number"
        placeholder="Start dt"
        value={filters.start_dt ?? ''}
        onChange={(e) => onChange({ ...filters, start_dt: e.target.value ? Number(e.target.value) : undefined, offset: 0 })}
        aria-label="Start TransactionDT"
      />
      <input
        type="number"
        placeholder="End dt"
        value={filters.end_dt ?? ''}
        onChange={(e) => onChange({ ...filters, end_dt: e.target.value ? Number(e.target.value) : undefined, offset: 0 })}
        aria-label="End TransactionDT"
      />

      {hasActiveFilters && (
        <Button variant="ghost" size="sm" onClick={() => onChange({ limit: filters.limit, offset: 0 })}>
          Clear filters
        </Button>
      )}
    </div>
  )
}
