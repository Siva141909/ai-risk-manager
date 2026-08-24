import { Badge } from '../common/Badge'

export function CaseStatusBadge({ hasInvestigation, isRunning }: { hasInvestigation: boolean; isRunning?: boolean }) {
  if (isRunning) return <Badge variant="badge-status-running">Investigating…</Badge>
  return (
    <Badge variant={hasInvestigation ? 'badge-status-investigated' : 'badge-status-not-investigated'}>
      {hasInvestigation ? 'Investigated' : 'Not investigated'}
    </Badge>
  )
}
