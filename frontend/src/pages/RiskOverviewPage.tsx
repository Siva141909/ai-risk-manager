import { useNavigate } from 'react-router-dom'
import { PageShell } from '../components/layout/PageShell'
import { Card } from '../components/common/Card'
import { StatTile } from '../components/risk/StatTile'
import { RiskTierBadge } from '../components/risk/RiskTierBadge'
import { GraphFlagBadge } from '../components/risk/GraphFlagBadge'
import { Skeleton } from '../components/common/Skeleton'
import { StatePanel } from '../components/common/StatePanel'
import { InboxIcon } from '../components/common/Icons'
import { formatScorePercent, formatTransactionDt } from '../utils/format'
import { useOverviewStats } from '../hooks/useOverviewStats'
import '../components/risk/risk.css'

export function RiskOverviewPage() {
  const navigate = useNavigate()
  const stats = useOverviewStats()

  return (
    <PageShell title="Risk Overview" subtitle="Operational summary of the case pipeline">
      <Card title="Cases by risk tier" className="overview-section">
        {stats.isLoading ? (
          <div className="stat-tile-grid">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} height={72} />
            ))}
          </div>
        ) : (
          <div className="stat-tile-grid">
            <StatTile label="Low" value={stats.tierCounts.LOW} accentColor="var(--color-risk-low-border)" />
            <StatTile label="Medium" value={stats.tierCounts.MEDIUM} accentColor="var(--color-risk-medium-border)" />
            <StatTile label="High" value={stats.tierCounts.HIGH} accentColor="var(--color-risk-high-border)" />
            <StatTile label="Critical" value={stats.tierCounts.CRITICAL} accentColor="var(--color-risk-critical-border)" />
          </div>
        )}
      </Card>

      <div className="overview-row">
        <Card title="Coordination detection">
          {stats.isLoading ? (
            <Skeleton height={72} />
          ) : (
            <StatTile label="Graph-flagged cases (of the servable dataset)" value={stats.graphFlaggedCount} accentColor="var(--color-graph-border)" />
          )}
        </Card>
        <Card title="Investigation status">
          {stats.isLoading ? (
            <Skeleton height={72} />
          ) : (
            <div className="stat-tile-grid">
              <StatTile label="Investigated" value={stats.investigatedCount} />
              <StatTile label="Not yet investigated" value={Math.max(stats.totalCount - stats.investigatedCount, 0)} />
            </div>
          )}
        </Card>
      </div>

      <Card
        title="Recent critical cases"
        action={
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/cases?risk_tier=CRITICAL')}>
            View all →
          </button>
        }
      >
        {stats.isLoading ? (
          <Skeleton height={140} />
        ) : stats.recentHighPriority.length === 0 ? (
          <StatePanel icon={<InboxIcon />} title="No critical or high-tier cases in the current dataset" />
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Case ID</th>
                <th>Time</th>
                <th>ML Risk</th>
                <th>Graph</th>
              </tr>
            </thead>
            <tbody>
              {stats.recentHighPriority.map((c) => (
                <tr key={c.case_id} onClick={() => navigate(`/cases/${c.case_id}`)}>
                  <td style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{c.case_id}</td>
                  <td style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-small-size)' }}>
                    {formatTransactionDt(c.transaction_dt)}
                  </td>
                  <td>
                    <RiskTierBadge tier={c.ml_risk_tier} />{' '}
                    <span style={{ color: 'var(--color-text-tertiary)' }}>{formatScorePercent(c.ml_risk_score)}</span>
                  </td>
                  <td>
                    <GraphFlagBadge flagged={c.graph_flagged} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </PageShell>
  )
}
