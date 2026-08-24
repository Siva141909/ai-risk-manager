import { useQueries, useQuery } from '@tanstack/react-query'
import { apiClient } from '../services/apiClient'
import type { CaseSummaryResponse } from '../types/api'

/**
 * Risk Overview's tiles are built from a small, FIXED set of bounded
 * `limit=1` list calls (reading only the `total` field) rather than an
 * aggregate endpoint the backend doesn't have — docs/FRONTEND_UX.md §3.
 * Every call here is a single request, never a loop over unbounded data.
 */
export function useOverviewStats() {
  const tierQueries = useQueries({
    queries: (['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'] as const).map((tier) => ({
      queryKey: ['cases-count', 'risk_tier', tier],
      queryFn: () => apiClient.listCases({ risk_tier: tier, limit: 1 }),
      staleTime: 5 * 60 * 1000,
    })),
  })

  const graphFlaggedQuery = useQuery({
    queryKey: ['cases-count', 'graph_flagged'],
    queryFn: () => apiClient.listCases({ graph_flagged: true, limit: 1 }),
    staleTime: 5 * 60 * 1000,
  })

  const investigatedQuery = useQuery({
    queryKey: ['cases-count', 'investigated'],
    queryFn: () => apiClient.listCases({ investigation_status: 'investigated', limit: 1 }),
    staleTime: 30 * 1000, // shorter — this count changes as demos run investigations
  })

  const totalQuery = useQuery({
    queryKey: ['cases-count', 'total'],
    queryFn: () => apiClient.listCases({ limit: 1 }),
    staleTime: 5 * 60 * 1000,
  })

  const criticalCasesQuery = useQuery({
    queryKey: ['cases-recent-critical'],
    queryFn: async () => {
      const critical = await apiClient.listCases({ risk_tier: 'CRITICAL', limit: 50 })
      if (critical.items.length > 0) return critical.items
      const high = await apiClient.listCases({ risk_tier: 'HIGH', limit: 50 })
      return high.items
    },
    staleTime: 5 * 60 * 1000,
  })

  const recentHighPriority: CaseSummaryResponse[] = (criticalCasesQuery.data ?? [])
    .slice()
    .sort((a, b) => b.transaction_dt - a.transaction_dt)
    .slice(0, 5)

  const isLoading =
    tierQueries.some((q) => q.isLoading) ||
    graphFlaggedQuery.isLoading ||
    investigatedQuery.isLoading ||
    totalQuery.isLoading ||
    criticalCasesQuery.isLoading

  return {
    isLoading,
    tierCounts: {
      LOW: tierQueries[0]?.data?.total ?? 0,
      MEDIUM: tierQueries[1]?.data?.total ?? 0,
      HIGH: tierQueries[2]?.data?.total ?? 0,
      CRITICAL: tierQueries[3]?.data?.total ?? 0,
    },
    graphFlaggedCount: graphFlaggedQuery.data?.total ?? 0,
    investigatedCount: investigatedQuery.data?.total ?? 0,
    totalCount: totalQuery.data?.total ?? 0,
    recentHighPriority,
  }
}
