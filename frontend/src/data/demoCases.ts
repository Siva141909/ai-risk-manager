/**
 * Mirrors src/api/demo_data.py::DEMO_CASES exactly (case_id + label +
 * description) — this is display metadata only, not a data source.
 * Selecting one just navigates to the real Case Investigation page,
 * which fetches everything from the API like any other case
 * (Phase 5B.8: "demo mode must use the actual backend pipeline").
 */
export interface DemoCase {
  label: string
  caseId: string
  description: string
}

export const DEMO_CASES: DemoCase[] = [
  {
    label: 'Strong coordinated ring',
    caseId: 'CASE-3410549',
    description: '11-member community sharing both a device and an IP (multi-attribute overlap), MEDIUM ML tier.',
  },
  {
    label: 'Legitimate household',
    caseId: 'CASE-3452855',
    description: '5-member community linked by a single shared IP only, LOW ML tier — a false-positive-shaped case, not a ring.',
  },
  {
    label: 'ML-low / graph-high',
    caseId: 'CASE-3457202',
    description: '4-member community sharing a bank account — the quadrant ML scoring alone would miss.',
  },
  {
    label: 'Conflicting evidence',
    caseId: 'CASE-3416834',
    description: '3-member community sharing a device — structural and behavioral signals in tension.',
  },
  {
    label: 'Missing data',
    caseId: 'CASE-3400406',
    description: 'Singleton customer proxy, 1 known transaction, no graph evidence — almost nothing to investigate.',
  },
]
