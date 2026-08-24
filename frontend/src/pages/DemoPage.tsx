import { Link } from 'react-router-dom'
import { PageShell } from '../components/layout/PageShell'
import { Card } from '../components/common/Card'
import { Badge } from '../components/common/Badge'
import { DEMO_CASES } from '../data/demoCases'
import './pages.css'

/**
 * Development tooling, not part of the end-user product surface
 * (Phase 5B.8/5B.15) — a fast way to jump to the 5 backend demo cases
 * (src/api/demo_data.py) without hunting through the queue. Selecting
 * a case navigates to the real Case Investigation page; nothing here
 * fabricates data — it is five links plus the label/description
 * metadata that mirrors the backend's own demo_data module.
 */
export function DemoPage() {
  return (
    <PageShell title="Demo Mode" subtitle="Development tooling — jump directly to one of the 5 backend demo cases">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
        {DEMO_CASES.map((demo) => (
          <Card key={demo.caseId}>
            <Badge variant="badge-graph-off">DEMO / DEV TOOLING</Badge>
            <h3 style={{ margin: '12px 0 4px', fontSize: 'var(--text-h2-size)' }}>{demo.label}</h3>
            <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-small-size)', marginBottom: 12 }}>
              {demo.description}
            </p>
            <Link to={`/cases/${demo.caseId}`} className="btn btn-primary btn-sm">
              Open {demo.caseId}
            </Link>
          </Card>
        ))}
      </div>
    </PageShell>
  )
}
