import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { CaseInvestigationPage } from './CaseInvestigationPage'
import { apiClient, ApiError, InvestigationNotFoundError } from '../services/apiClient'
import type { CaseDetailResponse, CaseGraphResponse, InvestigationResponse } from '../types/api'

vi.mock('../services/apiClient', async () => {
  const actual = await vi.importActual<typeof import('../services/apiClient')>('../services/apiClient')
  return {
    ...actual,
    apiClient: { getCase: vi.fn(), getCaseGraph: vi.fn(), getCaseInvestigation: vi.fn(), investigate: vi.fn() },
  }
})

const mockedApiClient = vi.mocked(apiClient)

const caseDetail: CaseDetailResponse = {
  case_id: 'CASE-42',
  trigger_transaction_ids: [42],
  trigger_transaction_dt: 1000,
  ml_risk_score: 0.02,
  ml_risk_tier: 'MEDIUM',
  customer_proxy_id: 'proxy-1',
  customer_proxy_confidence: 'singleton',
  graph_lookup_keys: {},
  graph_evidence: null,
  has_investigation: false,
}

const emptyGraph: CaseGraphResponse = { case_id: 'CASE-42', graph_evidence: null, nodes: [], edges: [] }

function renderPage(caseId = 'CASE-42') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/cases/${caseId}`]}>
        <Routes>
          <Route path="/cases/:caseId" element={<CaseInvestigationPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  mockedApiClient.getCaseGraph.mockResolvedValue(emptyGraph)
})

describe('CaseInvestigationPage', () => {
  it('shows a case-not-found state for a 404', async () => {
    mockedApiClient.getCase.mockRejectedValue(new ApiError(404, { error_code: 'case_not_found', message: 'nope', request_id: 'r1' }))
    mockedApiClient.getCaseInvestigation.mockRejectedValue(
      new InvestigationNotFoundError(404, { error_code: 'investigation_not_found', message: 'none', request_id: 'r1' })
    )
    renderPage()
    expect(await screen.findByText('Case not found')).toBeInTheDocument()
  })

  it('renders risk summary fields from the case, never from an investigation report', async () => {
    mockedApiClient.getCase.mockResolvedValue(caseDetail)
    mockedApiClient.getCaseInvestigation.mockRejectedValue(
      new InvestigationNotFoundError(404, { error_code: 'investigation_not_found', message: 'none', request_id: 'r1' })
    )
    renderPage()
    expect(await screen.findByText('CASE-42')).toBeInTheDocument()
    expect(screen.getAllByText('Medium').length).toBeGreaterThan(0)
  })

  it('shows a "not investigated yet" state and a Start Investigation action when no report exists', async () => {
    mockedApiClient.getCase.mockResolvedValue(caseDetail)
    mockedApiClient.getCaseInvestigation.mockRejectedValue(
      new InvestigationNotFoundError(404, { error_code: 'investigation_not_found', message: 'none', request_id: 'r1' })
    )
    renderPage()
    expect(await screen.findByText('This case has not been investigated yet')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Start Investigation' }).length).toBeGreaterThan(0)
  })

  it('shows the investigating state while a mutation is pending, then the AI panel on success', async () => {
    mockedApiClient.getCase.mockResolvedValue(caseDetail)
    mockedApiClient.getCaseInvestigation.mockRejectedValue(
      new InvestigationNotFoundError(404, { error_code: 'investigation_not_found', message: 'none', request_id: 'r1' })
    )
    let resolveInvestigate!: (v: InvestigationResponse) => void
    mockedApiClient.investigate.mockReturnValue(new Promise((resolve) => (resolveInvestigate = resolve)))

    renderPage()
    const startButtons = await screen.findAllByRole('button', { name: 'Start Investigation' })
    await userEvent.click(startButtons[0])

    expect(await screen.findByText('Investigating…')).toBeInTheDocument()

    resolveInvestigate({
      case_id: 'CASE-42',
      transaction: { transaction_id: 42, transaction_dt: 1000 },
      ml_risk_score: 0.02,
      ml_risk_tier: 'MEDIUM',
      graph_summary: null,
      investigation_report: {
        case_id: 'CASE-42',
        summary: 'Done.',
        trigger: 'x',
        risk_tier: 'MEDIUM',
        graph_findings: 'x',
        behavioral_findings: 'x',
        legitimate_explanations: [],
        conflicting_evidence: false,
        conflict_description: null,
        policy_findings: [],
        recommendation: 'close',
        requires_human_review: false,
        human_approval_required_for_action: true,
        confidence: 0.5,
        evidence: [],
        retrospective_evidence_used: false,
        investigation_complete: true,
        validation_status: 'passed',
      },
      evidence: [],
      recommendation: 'close',
      confidence: 0.5,
      human_approval_required: true,
      processing: {
        request_id: 'r1', llm_backend: 'stub', cache_hit: false, investigation_mode: 'real_time',
        total_duration_ms: 10, case_lookup_duration_ms: 1, agent_duration_ms: 9,
      },
    })

    expect(await screen.findByText('AI INVESTIGATION')).toBeInTheDocument()
    expect(screen.getByText('HUMAN APPROVAL REQUIRED')).toBeInTheDocument()
  })
})
