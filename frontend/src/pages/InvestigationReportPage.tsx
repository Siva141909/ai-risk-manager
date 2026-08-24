import { Link, useParams } from 'react-router-dom'
import { PageShell } from '../components/layout/PageShell'
import { Card } from '../components/common/Card'
import { Skeleton } from '../components/common/Skeleton'
import { StatePanel } from '../components/common/StatePanel'
import { ClockIcon } from '../components/common/Icons'
import { RiskTierBadge } from '../components/risk/RiskTierBadge'
import { RecommendationBadge } from '../components/investigation/RecommendationBadge'
import { EvidenceList } from '../components/evidence/EvidenceItemCard'
import { useCase, useCaseInvestigation } from '../hooks/useCases'
import { formatConfidencePercent, formatScorePercent } from '../utils/format'
import './pages.css'

/** Report-style, read-only rendering — every section maps 1:1 onto
 * fields already fetched, no new API call beyond what Case
 * Investigation already made (docs/FRONTEND_UX.md §3). */
export function InvestigationReportPage() {
  const { caseId } = useParams<{ caseId: string }>()
  const caseQuery = useCase(caseId)
  const investigationQuery = useCaseInvestigation(caseId)

  if (caseQuery.isLoading || investigationQuery.isLoading) {
    return (
      <PageShell title="Investigation Report">
        <Skeleton height={400} />
      </PageShell>
    )
  }

  if (investigationQuery.notFound || !investigationQuery.data) {
    return (
      <PageShell title="Investigation Report" action={<Link to={`/cases/${caseId}`} className="btn btn-ghost btn-sm">← Back to case</Link>}>
        <StatePanel icon={<ClockIcon />} title="This case has not been investigated yet" description="Start an investigation from the Case Investigation page first." />
      </PageShell>
    )
  }

  const c = caseQuery.data
  const report = investigationQuery.data

  return (
    <PageShell
      title={`Investigation Report — ${caseId}`}
      action={<Link to={`/cases/${caseId}`} className="btn btn-ghost btn-sm">← Back to case</Link>}
    >
      <div className="report-page">
        <Card>
          <section className="report-section">
            <h2 className="report-section-title">Executive Summary</h2>
            <p>{report.summary}</p>
          </section>

          <section className="report-section">
            <h2 className="report-section-title">Risk Context</h2>
            {c && (
              <p>
                <RiskTierBadge tier={c.ml_risk_tier} /> · ML score {formatScorePercent(c.ml_risk_score)} — {report.trigger}
              </p>
            )}
          </section>

          <section className="report-section">
            <h2 className="report-section-title">Graph Findings</h2>
            <p>{report.graph_findings}</p>
          </section>

          <section className="report-section">
            <h2 className="report-section-title">Behavioral Findings</h2>
            <p>{report.behavioral_findings}</p>
          </section>

          {report.legitimate_explanations.length > 0 && (
            <section className="report-section">
              <h2 className="report-section-title">Legitimate Explanations</h2>
              <ul>
                {report.legitimate_explanations.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            </section>
          )}

          {report.conflicting_evidence && (
            <section className="report-section">
              <h2 className="report-section-title">Conflicting Evidence</h2>
              <p>{report.conflict_description}</p>
            </section>
          )}

          {report.policy_findings.length > 0 && (
            <section className="report-section">
              <h2 className="report-section-title">Policy Findings</h2>
              <ul>
                {report.policy_findings.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </section>
          )}

          <section className="report-section">
            <h2 className="report-section-title">Recommendation</h2>
            <p>
              <RecommendationBadge recommendation={report.recommendation} /> · Confidence{' '}
              {formatConfidencePercent(report.confidence)}
            </p>
            <p style={{ fontWeight: 600 }}>{report.human_approval_required_for_action ? 'HUMAN APPROVAL REQUIRED' : ''}</p>
          </section>

          <section className="report-section">
            <h2 className="report-section-title">Evidence</h2>
            <EvidenceList items={report.evidence} />
          </section>
        </Card>
      </div>
    </PageShell>
  )
}
