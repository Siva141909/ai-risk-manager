import { useNavigate } from 'react-router-dom'
import { RiskTierBadge } from '../risk/RiskTierBadge'
import { GraphFlagBadge } from '../risk/GraphFlagBadge'
import { CaseStatusBadge } from './CaseStatusBadge'
import { RecommendationBadge } from '../investigation/RecommendationBadge'
import { formatScorePercent, formatTransactionDt } from '../../utils/format'
import type { CaseSummaryResponse, InvestigationReport } from '../../types/api'
import '../common/common.css'

export function CaseTable({
  cases,
  enrichment,
}: {
  cases: CaseSummaryResponse[]
  enrichment: Record<string, InvestigationReport | undefined>
}) {
  const navigate = useNavigate()

  return (
    <table className="data-table" aria-label="Case queue">
      <thead>
        <tr>
          <th>Case ID</th>
          <th>Time</th>
          <th>ML Risk</th>
          <th>Graph</th>
          <th>Status</th>
          <th>Recommended action</th>
        </tr>
      </thead>
      <tbody>
        {cases.map((c) => {
          const report = enrichment[c.case_id]
          return (
            <tr key={c.case_id} onClick={() => navigate(`/cases/${c.case_id}`)} tabIndex={0}
              onKeyDown={(e) => e.key === 'Enter' && navigate(`/cases/${c.case_id}`)}>
              <td>
                <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>{c.case_id}</span>
              </td>
              <td style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-small-size)' }}>
                {formatTransactionDt(c.transaction_dt)}
              </td>
              <td>
                <RiskTierBadge tier={c.ml_risk_tier} /> <span style={{ marginLeft: 6, color: 'var(--color-text-tertiary)' }}>{formatScorePercent(c.ml_risk_score)}</span>
              </td>
              <td>
                <GraphFlagBadge flagged={c.graph_flagged} />
              </td>
              <td>
                <CaseStatusBadge hasInvestigation={c.has_investigation} />
              </td>
              <td>{report ? <RecommendationBadge recommendation={report.recommendation} /> : '—'}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}
