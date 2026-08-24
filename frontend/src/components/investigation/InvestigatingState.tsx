import { SparklesIcon } from '../common/Icons'
import './investigation.css'

/** No fake streaming/progress — the backend returns one atomic result
 * (docs/BACKEND_ARCHITECTURE.md §4), so this is a single honest
 * "in progress" state, not simulated step-by-step activity. */
export function InvestigatingState() {
  return (
    <div className="investigating-state">
      <div className="investigating-spinner" aria-hidden="true" />
      <div>
        <div className="investigating-title">
          <SparklesIcon /> Investigating…
        </div>
        <p className="investigating-note">
          The agent is gathering evidence and reasoning about this case. Real investigations typically
          take 20-60 seconds.
        </p>
      </div>
    </div>
  )
}
