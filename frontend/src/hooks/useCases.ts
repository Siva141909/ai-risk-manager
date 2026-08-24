import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient, InvestigationNotFoundError } from '../services/apiClient'
import type { CaseListParams, InvestigateRequest } from '../types/api'

// The underlying dataset is frozen for the lifetime of the server
// process (docs/BACKEND_ARCHITECTURE.md §2) — a long staleTime avoids
// re-fetching case/graph data that cannot have changed, per Phase
// 5B.17's "avoid unnecessary API calls."
const STATIC_DATA_STALE_TIME_MS = 5 * 60 * 1000

export function useCaseList(params: CaseListParams) {
  return useQuery({
    queryKey: ['cases', params],
    queryFn: () => apiClient.listCases(params),
    staleTime: STATIC_DATA_STALE_TIME_MS,
  })
}

export function useCase(caseId: string | undefined) {
  return useQuery({
    queryKey: ['case', caseId],
    queryFn: () => apiClient.getCase(caseId as string),
    enabled: Boolean(caseId),
    staleTime: STATIC_DATA_STALE_TIME_MS,
  })
}

export function useCaseGraph(caseId: string | undefined) {
  return useQuery({
    queryKey: ['case-graph', caseId],
    queryFn: () => apiClient.getCaseGraph(caseId as string),
    enabled: Boolean(caseId),
    staleTime: STATIC_DATA_STALE_TIME_MS,
  })
}

/** 404 (no investigation yet) is a normal outcome, not an error — this
 * hook surfaces it as `notFound: true` rather than `isError`, so pages
 * render the "not investigated yet" empty state instead of an error
 * banner (docs/FRONTEND_UX.md §5). */
export function useCaseInvestigation(caseId: string | undefined) {
  const query = useQuery({
    queryKey: ['investigation', caseId],
    queryFn: () => apiClient.getCaseInvestigation(caseId as string),
    enabled: Boolean(caseId),
    // no per-query retry override needed: the global retry predicate
    // (shouldRetryQuery, App.tsx) already never retries a 404.
  })
  const notFound = query.error instanceof InvestigationNotFoundError
  return { ...query, notFound }
}

export function useInvestigate(caseId: string) {
  const queryClient = useQueryClient()
  const mutation = useMutation({
    mutationFn: (body: InvestigateRequest) => apiClient.investigate(body),
    onSuccess: (data) => {
      queryClient.setQueryData(['investigation', caseId], data.investigation_report)
      queryClient.invalidateQueries({ queryKey: ['case', caseId] })
      queryClient.invalidateQueries({ queryKey: ['cases'] })
    },
  })
  return { ...mutation, isRunning: mutation.isPending }
}
