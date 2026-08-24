import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AiInvestigationPanel } from './AiInvestigationPanel'
import type { InvestigationReport } from '../../types/api'

const baseReport: InvestigationReport = {
  case_id: 'CASE-1',
  summary: 'A test investigation summary.',
  trigger: 'ML risk tier LOW',
  risk_tier: 'LOW',
  graph_findings: 'No graph evidence.',
  behavioral_findings: 'Normal activity.',
  legitimate_explanations: ['Could be a household.'],
  conflicting_evidence: true,
  conflict_description: 'ML says low, graph says high.',
  policy_findings: ['[POLICY:doc#1]'],
  recommendation: 'investigate_further',
  requires_human_review: true,
  human_approval_required_for_action: true,
  confidence: 0.55,
  evidence: [
    { evidence_id: 'CUST-1', source_tool: 'get_customer_context', summary: 'x', is_retrospective: false },
  ],
  retrospective_evidence_used: false,
  investigation_complete: true,
  validation_status: 'passed',
}

describe('AiInvestigationPanel', () => {
  it('labels the section AI INVESTIGATION and shows confidence', () => {
    render(<AiInvestigationPanel report={baseReport} />)
    expect(screen.getByText('AI INVESTIGATION')).toBeInTheDocument()
    expect(screen.getByText('confidence 55%')).toBeInTheDocument()
  })

  it('renders every structured section: summary, findings, legitimate explanations, conflicts, policy, recommendation', () => {
    render(<AiInvestigationPanel report={baseReport} />)
    expect(screen.getByText(baseReport.summary)).toBeInTheDocument()
    expect(screen.getByText(baseReport.graph_findings)).toBeInTheDocument()
    expect(screen.getByText(baseReport.behavioral_findings)).toBeInTheDocument()
    expect(screen.getByText('Could be a household.')).toBeInTheDocument()
    expect(screen.getByText(baseReport.conflict_description as string)).toBeInTheDocument()
    expect(screen.getByText('[POLICY:doc#1]')).toBeInTheDocument()
    expect(screen.getByText('Investigate Further')).toBeInTheDocument()
  })

  it('omits the Conflicting Evidence section when conflicting_evidence is false', () => {
    render(<AiInvestigationPanel report={{ ...baseReport, conflicting_evidence: false, conflict_description: null }} />)
    expect(screen.queryByText('Conflicting Evidence')).not.toBeInTheDocument()
  })

  it('renders a fail-safe note and hides synthesized findings when validation_status is failed_human_review', () => {
    const failSafe: InvestigationReport = {
      ...baseReport,
      validation_status: 'failed_human_review',
      recommendation: 'escalate_to_human_analyst',
      evidence: [],
      graph_findings: '',
      behavioral_findings: '',
      legitimate_explanations: [],
      conflicting_evidence: false,
      conflict_description: null,
      policy_findings: [],
    }
    render(<AiInvestigationPanel report={failSafe} />)
    expect(screen.getByText(/could not be automatically validated/)).toBeInTheDocument()
    expect(screen.queryByText('Behavioral Findings')).not.toBeInTheDocument()
  })

  it('renders deterministic evidence via EvidenceList, distinct from the AI prose blocks', () => {
    const { container } = render(<AiInvestigationPanel report={baseReport} />)
    expect(screen.getByText('CUST-1')).toBeInTheDocument()
    // AI prose blocks use the dashed .ai-block style; evidence cards use .evidence-card
    expect(container.querySelectorAll('.ai-block').length).toBeGreaterThan(0)
    expect(container.querySelectorAll('.evidence-card').length).toBeGreaterThan(0)
  })
})
