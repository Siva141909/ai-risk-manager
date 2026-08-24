import { Badge } from '../common/Badge'
import { ShareIcon } from '../common/Icons'

export function GraphFlagBadge({ flagged }: { flagged: boolean }) {
  return (
    <Badge variant={flagged ? 'badge-graph-on' : 'badge-graph-off'}>
      <ShareIcon />
      {flagged ? 'Graph Flagged' : 'No Graph Evidence'}
    </Badge>
  )
}
