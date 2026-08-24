import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { HumanReviewPanel } from './HumanReviewPanel'

describe('HumanReviewPanel', () => {
  it('shows HUMAN APPROVAL REQUIRED when humanApprovalRequired is true', () => {
    render(<HumanReviewPanel recommendation="escalate_to_human_analyst" humanApprovalRequired />)
    expect(screen.getByText('HUMAN APPROVAL REQUIRED')).toBeInTheDocument()
  })

  it('every UI-only action button is disabled (no backend write path exists)', () => {
    render(<HumanReviewPanel recommendation="close" humanApprovalRequired />)
    const buttons = ['Approve recommendation', 'Request further investigation', 'Mark as legitimate', 'Escalate']
    for (const label of buttons) {
      expect(screen.getByRole('button', { name: label })).toBeDisabled()
    }
  })

  it('renders the recommendation badge', () => {
    render(<HumanReviewPanel recommendation="monitor" humanApprovalRequired />)
    expect(screen.getByText('Monitor')).toBeInTheDocument()
  })
})
