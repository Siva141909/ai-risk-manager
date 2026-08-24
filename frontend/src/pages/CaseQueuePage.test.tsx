import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CaseQueuePage } from './CaseQueuePage'
import { renderWithProviders } from '../testUtils'
import { apiClient, ApiError } from '../services/apiClient'
import type { CaseListResponse, CaseSummaryResponse } from '../types/api'

vi.mock('../services/apiClient', async () => {
  const actual = await vi.importActual<typeof import('../services/apiClient')>('../services/apiClient')
  return { ...actual, apiClient: { listCases: vi.fn(), getCaseInvestigation: vi.fn() } }
})

const mockedApiClient = vi.mocked(apiClient)

function makeCase(overrides: Partial<CaseSummaryResponse> = {}): CaseSummaryResponse {
  return {
    case_id: 'CASE-1',
    transaction_id: 1,
    transaction_dt: 1000,
    ml_risk_score: 0.5,
    ml_risk_tier: 'MEDIUM',
    graph_flagged: false,
    has_investigation: false,
    ...overrides,
  }
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('CaseQueuePage', () => {
  it('renders a loading skeleton before data arrives', () => {
    mockedApiClient.listCases.mockReturnValue(new Promise(() => {}))
    const { container } = renderWithProviders(<CaseQueuePage />)
    expect(container.querySelectorAll('.skeleton').length).toBeGreaterThan(0)
  })

  it('renders case rows once data loads', async () => {
    const response: CaseListResponse = { items: [makeCase()], total: 1, limit: 25, offset: 0 }
    mockedApiClient.listCases.mockResolvedValue(response)
    renderWithProviders(<CaseQueuePage />)
    expect(await screen.findByText('CASE-1')).toBeInTheDocument()
  })

  it('shows an empty state with a clear-filters action when no cases match', async () => {
    mockedApiClient.listCases.mockResolvedValue({ items: [], total: 0, limit: 25, offset: 0 })
    renderWithProviders(<CaseQueuePage />)
    expect(await screen.findByText('No cases match these filters')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Clear filters' })).toBeInTheDocument()
  })

  it('shows an error state with a retry action on API failure', async () => {
    mockedApiClient.listCases.mockRejectedValue(new ApiError(500, { error_code: 'internal_error', message: 'boom', request_id: 'r1' }))
    renderWithProviders(<CaseQueuePage />)
    expect(await screen.findByText('Could not load cases')).toBeInTheDocument()
    expect(screen.getByText('boom')).toBeInTheDocument()
  })

  it('re-queries the API with a risk_tier filter when a tier chip is clicked', async () => {
    mockedApiClient.listCases.mockResolvedValue({ items: [makeCase()], total: 1, limit: 25, offset: 0 })
    renderWithProviders(<CaseQueuePage />)
    await screen.findByText('CASE-1')

    await userEvent.click(screen.getByRole('button', { name: 'CRITICAL' }))

    await waitFor(() => {
      expect(mockedApiClient.listCases).toHaveBeenLastCalledWith(
        expect.objectContaining({ risk_tier: 'CRITICAL', offset: 0 })
      )
    })
  })

  it('renders the ML risk tier badge for each row', async () => {
    mockedApiClient.listCases.mockResolvedValue({
      items: [makeCase({ ml_risk_tier: 'CRITICAL' })],
      total: 1,
      limit: 25,
      offset: 0,
    })
    renderWithProviders(<CaseQueuePage />)
    expect(await screen.findByText('Critical')).toBeInTheDocument()
  })
})
