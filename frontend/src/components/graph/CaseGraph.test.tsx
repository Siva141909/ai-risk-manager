import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CaseGraph } from './CaseGraph'
import type { CaseGraphResponse } from '../../types/api'

const graph: CaseGraphResponse = {
  case_id: 'CASE-1',
  graph_evidence: null,
  nodes: [
    { customer_proxy_id: 'center', is_center: true },
    { customer_proxy_id: 'neighbor-1', is_center: false },
    { customer_proxy_id: 'neighbor-2', is_center: false },
  ],
  edges: [
    { source: 'center', target: 'neighbor-1', relationship_type: 'SHARED_DEVICE', shared_entity_value: 'DEV-1' },
    { source: 'center', target: 'neighbor-1', relationship_type: 'SHARED_IP', shared_entity_value: 'IP-1' },
    { source: 'center', target: 'neighbor-2', relationship_type: 'SHARED_BANK_ACCOUNT', shared_entity_value: 'BANK-1' },
  ],
}

describe('CaseGraph', () => {
  it('shows an empty-state message when there are no nodes', () => {
    render(<CaseGraph graph={{ ...graph, nodes: [], edges: [] }} />)
    expect(screen.getByText(/No shared infrastructure detected/)).toBeInTheDocument()
  })

  it('renders one node circle per graph node and a legend entry per relationship type', () => {
    const { container } = render(<CaseGraph graph={graph} />)
    expect(container.querySelectorAll('circle').length).toBe(graph.nodes.length)
    expect(screen.getByText('Shared Device')).toBeInTheDocument()
    expect(screen.getByText('Shared IP')).toBeInTheDocument()
    expect(screen.getByText('Shared Bank Account')).toBeInTheDocument()
  })

  it('renders a separate path per edge, including both edges between the same overlapping node pair', () => {
    const { container } = render(<CaseGraph graph={graph} />)
    expect(container.querySelectorAll('path').length).toBe(graph.edges.length)
  })

  it('resets pan/zoom on "Reset view" click', async () => {
    const { container } = render(<CaseGraph graph={graph} />)
    const resetButton = screen.getByRole('button', { name: 'Reset view' })
    expect(resetButton).toBeInTheDocument()
    const svgGroup = container.querySelector('svg > g')
    expect(svgGroup).toHaveAttribute('transform', expect.stringContaining('scale(1)'))
  })
})
