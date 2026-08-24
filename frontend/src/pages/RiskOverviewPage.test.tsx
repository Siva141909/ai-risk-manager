import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RiskOverviewPage } from './RiskOverviewPage'
import { renderWithProviders } from '../testUtils'
import { apiClient } from '../services/apiClient'
import type { CaseListParams, CaseListResponse, CaseSummaryResponse } from '../types/api'

vi.mock('../services/apiClient', async () => {
  const actual = await vi.importActual<typeof import('../services/apiClient')>('../services/apiClient')
  return { ...actual, apiClient: { listCases: vi.fn() } }
})

const mockedApiClient = vi.mocked(apiClient)

function makeCase(overrides: Partial<CaseSummaryResponse> = {}): CaseSummaryResponse {
  return {
    case_id: 'CASE-1', transaction_id: 1, transaction_dt: 5000, ml_risk_score: 0.9,
    ml_risk_tier: 'CRITICAL', graph_flagged: false, has_investigation: false, ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
  mockedApiClient.listCases.mockImplementation(async (params: CaseListParams = {}): Promise<CaseListResponse> => {
    if (params.risk_tier === 'CRITICAL' && params.limit === 50) {
      return { items: [makeCase()], total: 1, limit: 50, offset: 0 }
    }
    const totals: Record<string, number> = { LOW: 100, MEDIUM: 50, HIGH: 10, CRITICAL: 5 }
    if (params.risk_tier) return { items: [], total: totals[params.risk_tier], limit: 1, offset: 0 }
    if (params.graph_flagged) return { items: [], total: 7, limit: 1, offset: 0 }
    if (params.investigation_status === 'investigated') return { items: [], total: 2, limit: 1, offset: 0 }
    return { items: [], total: 165, limit: 1, offset: 0 }
  })
})

describe('RiskOverviewPage', () => {
  it('renders tier counts from the bounded summary queries', async () => {
    renderWithProviders(<RiskOverviewPage />)
    expect(await screen.findByText('100')).toBeInTheDocument()
    expect(screen.getByText('50')).toBeInTheDocument()
    expect(screen.getByText('10')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()
  })

  it('renders the graph-flagged and investigated counts', async () => {
    renderWithProviders(<RiskOverviewPage />)
    expect(await screen.findByText('7')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('renders recent critical cases from the bounded critical-tier query', async () => {
    renderWithProviders(<RiskOverviewPage />)
    expect(await screen.findByText('CASE-1')).toBeInTheDocument()
  })
})
