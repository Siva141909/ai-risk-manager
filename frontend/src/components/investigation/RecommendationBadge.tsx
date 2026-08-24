import { Badge } from '../common/Badge'
import type { RecommendationType } from '../../types/api'

const LABELS: Record<RecommendationType, string> = {
  close: 'Close',
  monitor: 'Monitor',
  investigate_further: 'Investigate Further',
  escalate_to_human_analyst: 'Escalate to Human Analyst',
}

const VARIANTS: Record<RecommendationType, string> = {
  close: 'badge-risk-low',
  monitor: 'badge-risk-medium',
  investigate_further: 'badge-risk-medium',
  escalate_to_human_analyst: 'badge-risk-critical',
}

export function RecommendationBadge({ recommendation }: { recommendation: string }) {
  const rec = recommendation as RecommendationType
  return <Badge variant={VARIANTS[rec] ?? 'badge-graph-off'}>{LABELS[rec] ?? recommendation}</Badge>
}
