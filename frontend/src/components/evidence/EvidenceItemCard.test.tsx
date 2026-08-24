import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EvidenceItemCard, EvidenceList } from './EvidenceItemCard'
import type { EvidenceItem } from '../../types/api'

const item: EvidenceItem = {
  evidence_id: 'CUST-ABC12345',
  source_tool: 'get_customer_context',
  summary: 'Customer proxy has 3 known transactions.',
  is_retrospective: false,
}

describe('EvidenceItemCard', () => {
  it('renders the evidence id, summary, and source tool', () => {
    render(<EvidenceItemCard item={item} />)
    expect(screen.getByText('CUST-ABC12345')).toBeInTheDocument()
    expect(screen.getByText(item.summary)).toBeInTheDocument()
    expect(screen.getByText(/get_customer_context/)).toBeInTheDocument()
  })

  it('shows a retrospective indicator only when is_retrospective is true', () => {
    const { rerender } = render(<EvidenceItemCard item={item} />)
    expect(screen.queryByText('retrospective')).not.toBeInTheDocument()

    rerender(<EvidenceItemCard item={{ ...item, is_retrospective: true }} />)
    expect(screen.getByText('retrospective')).toBeInTheDocument()
  })
})

describe('EvidenceList', () => {
  it('renders an empty message when there is no evidence', () => {
    render(<EvidenceList items={[]} />)
    expect(screen.getByText(/No evidence recorded/)).toBeInTheDocument()
  })

  it('renders one card per evidence item', () => {
    render(<EvidenceList items={[item, { ...item, evidence_id: 'CUST-XYZ99999' }]} />)
    expect(screen.getByText('CUST-ABC12345')).toBeInTheDocument()
    expect(screen.getByText('CUST-XYZ99999')).toBeInTheDocument()
  })
})
