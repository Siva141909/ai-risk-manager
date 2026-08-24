import { UserCheckIcon } from '../common/Icons'
import { Badge } from '../common/Badge'
import { Button } from '../common/Button'
import { Tooltip } from '../common/Tooltip'
import { RecommendationBadge } from './RecommendationBadge'
import './investigation.css'

const UI_ONLY_ACTIONS = ['Approve recommendation', 'Request further investigation', 'Mark as legitimate', 'Escalate']

/**
 * "The client can only REQUEST an investigation" (Phase 5A.8) extends
 * here: none of these four actions have a backing API endpoint (no
 * PATCH /cases/{id} exists), so per the explicit instruction ("if the
 * backend does not support an action, do not fake it") every button is
 * visibly disabled with a tooltip explaining why — never hidden, never
 * wired to a fake success state (docs/FRONTEND_UX.md §4).
 */
export function HumanReviewPanel({
  recommendation,
  humanApprovalRequired,
}: {
  recommendation: string
  humanApprovalRequired: boolean
}) {
  return (
    <div className="human-review-panel">
      <div className="human-review-row">
        <span className="human-review-label">Recommended action</span>
        <RecommendationBadge recommendation={recommendation} />
      </div>
      <div className="human-review-approval">
        <UserCheckIcon />
        <strong>{humanApprovalRequired ? 'HUMAN APPROVAL REQUIRED' : 'No approval required'}</strong>
      </div>
      <p className="human-review-note">
        The agent never authorizes an action itself — every recommendation requires a human decision.
      </p>
      <div className="human-review-actions">
        {UI_ONLY_ACTIONS.map((label) => (
          <Tooltip key={label} label="Not yet supported by the backend — Phase 5B UI-only">
            <Button variant="secondary" size="sm" disabled>
              {label}
            </Button>
          </Tooltip>
        ))}
      </div>
      <Badge variant="badge-graph-off">UI-only actions — no backend write path exists yet</Badge>
    </div>
  )
}
