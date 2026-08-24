import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PageShell } from '../components/layout/PageShell'
import { FilterBar } from '../components/cases/FilterBar'
import { CaseTable } from '../components/cases/CaseTable'
import { Button } from '../components/common/Button'
import { StatePanel } from '../components/common/StatePanel'
import { TableSkeleton } from '../components/common/Skeleton'
import { InboxIcon, XCircleIcon } from '../components/common/Icons'
import { useCaseList } from '../hooks/useCases'
import { useInvestigationEnrichment } from '../hooks/useInvestigationEnrichment'
import type { CaseListParams, RiskTier } from '../types/api'

const PAGE_SIZE = 25

export function CaseQueuePage() {
  const [searchParams] = useSearchParams()
  const [filters, setFilters] = useState<CaseListParams>({
    limit: PAGE_SIZE,
    offset: 0,
    risk_tier: (searchParams.get('risk_tier') as RiskTier) || undefined,
  })

  const { data, isLoading, isError, error, refetch } = useCaseList(filters)
  const investigatedIds = (data?.items ?? []).filter((c) => c.has_investigation).map((c) => c.case_id)
  const enrichment = useInvestigationEnrichment(investigatedIds)

  return (
    <PageShell title="Case Queue" subtitle="Prioritize and triage flagged cases">
      <FilterBar filters={filters} onChange={setFilters} />

      {isLoading && <TableSkeleton rows={8} cols={6} />}

      {isError && (
        <StatePanel
          icon={<XCircleIcon />}
          variant="error"
          title="Could not load cases"
          description={error instanceof Error ? error.message : 'Unknown error'}
          actionLabel="Retry"
          onAction={() => refetch()}
        />
      )}

      {!isLoading && !isError && data && data.items.length === 0 && (
        <StatePanel
          icon={<InboxIcon />}
          title="No cases match these filters"
          actionLabel="Clear filters"
          onAction={() => setFilters({ limit: PAGE_SIZE, offset: 0 })}
        />
      )}

      {!isLoading && !isError && data && data.items.length > 0 && (
        <>
          <CaseTable cases={data.items} enrichment={enrichment} />
          <div className="pagination-row">
            <span>
              Showing {(filters.offset ?? 0) + 1}–{(filters.offset ?? 0) + data.items.length} of {data.total}
            </span>
            <div style={{ display: 'flex', gap: 8 }}>
              <Button
                variant="ghost"
                size="sm"
                disabled={(filters.offset ?? 0) === 0}
                onClick={() => setFilters((f) => ({ ...f, offset: Math.max((f.offset ?? 0) - PAGE_SIZE, 0) }))}
              >
                Previous
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={(filters.offset ?? 0) + data.items.length >= data.total}
                onClick={() => setFilters((f) => ({ ...f, offset: (f.offset ?? 0) + PAGE_SIZE }))}
              >
                Next
              </Button>
            </div>
          </div>
        </>
      )}
    </PageShell>
  )
}
