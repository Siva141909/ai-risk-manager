import { useQueries } from '@tanstack/react-query'
import { apiClient } from '../services/apiClient'
import type { InvestigationReport } from '../types/api'

/**
 * Bounded, cache-only enrichment (docs/FRONTEND_UX.md §3): fetches the
 * already-cached investigation report ONLY for case_ids that are
 * already known to have one (has_investigation=true) — never triggers
 * a new agent run (GET /investigation never does), and never fetches
 * for a page's un-investigated rows. Bounded by how many of the
 * *already-fetched* case_ids are investigated, not by page size.
 */
export function useInvestigationEnrichment(caseIds: string[]): Record<string, InvestigationReport | undefined> {
  const results = useQueries({
    queries: caseIds.map((caseId) => ({
      queryKey: ['investigation', caseId],
      queryFn: () => apiClient.getCaseInvestigation(caseId),
      staleTime: 5 * 60 * 1000,
      retry: false,
    })),
  })

  const byId: Record<string, InvestigationReport | undefined> = {}
  caseIds.forEach((caseId, i) => {
    byId[caseId] = results[i]?.data
  })
  return byId
}
