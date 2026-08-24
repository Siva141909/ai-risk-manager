import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DemoPage } from './DemoPage'
import { DEMO_CASES } from '../data/demoCases'
import { renderWithProviders } from '../testUtils'

describe('DemoPage (demo-case selection)', () => {
  it('lists all 5 demo cases with a link to their real Case Investigation page', () => {
    renderWithProviders(<DemoPage />)
    expect(DEMO_CASES).toHaveLength(5)
    for (const demo of DEMO_CASES) {
      expect(screen.getByText(demo.label)).toBeInTheDocument()
      const link = screen.getByRole('link', { name: `Open ${demo.caseId}` })
      expect(link).toHaveAttribute('href', `/cases/${demo.caseId}`)
    }
  })

  it('labels every card as dev tooling, not a fabricated report', () => {
    renderWithProviders(<DemoPage />)
    expect(screen.getAllByText('DEMO / DEV TOOLING')).toHaveLength(5)
  })
})
