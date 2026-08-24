import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RiskTierBadge } from './RiskTierBadge'

describe('RiskTierBadge', () => {
  it.each([
    ['LOW', 'badge-risk-low'],
    ['MEDIUM', 'badge-risk-medium'],
    ['HIGH', 'badge-risk-high'],
    ['CRITICAL', 'badge-risk-critical'],
  ] as const)('renders %s with the correct variant class and label', (tier, expectedClass) => {
    render(<RiskTierBadge tier={tier} />)
    const badge = screen.getByText(tier.charAt(0) + tier.slice(1).toLowerCase())
    expect(badge.closest('.badge')).toHaveClass(expectedClass)
  })

  it('always renders an icon alongside the label — color is never the only signal', () => {
    render(<RiskTierBadge tier="CRITICAL" />)
    const badge = screen.getByText('Critical').closest('.badge')
    expect(badge?.querySelector('svg')).toBeInTheDocument()
  })
})
