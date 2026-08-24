import { Badge } from '../common/Badge'
import { AlertOctagonIcon, AlertTriangleIcon, CheckCircleIcon } from '../common/Icons'
import { riskTierLabel } from '../../utils/format'
import type { RiskTier } from '../../types/api'

const CONFIG: Record<RiskTier, { variant: string; icon: React.ReactNode }> = {
  LOW: { variant: 'badge-risk-low', icon: <CheckCircleIcon /> },
  MEDIUM: { variant: 'badge-risk-medium', icon: <AlertTriangleIcon /> },
  HIGH: { variant: 'badge-risk-high', icon: <AlertTriangleIcon /> },
  CRITICAL: { variant: 'badge-risk-critical', icon: <AlertOctagonIcon /> },
}

/** Color is never the only signal — every badge pairs an icon with the
 * tier label (docs/DESIGN_SYSTEM.md §1/§6). */
export function RiskTierBadge({ tier }: { tier: RiskTier | string }) {
  const config = CONFIG[tier as RiskTier] ?? CONFIG.LOW
  return (
    <Badge variant={config.variant}>
      {config.icon}
      {riskTierLabel(tier)}
    </Badge>
  )
}
