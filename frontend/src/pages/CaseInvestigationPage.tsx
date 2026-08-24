import { Link, useNavigate, useParams } from 'react-router-dom'
import { PageShell } from '../components/layout/PageShell'
import { Card } from '../components/common/Card'
import { Button } from '../components/common/Button'
import { Skeleton } from '../components/common/Skeleton'
import { StatePanel } from '../components/common/StatePanel'
import { XCircleIcon, ClockIcon } from '../components/common/Icons'
import { RiskTierBadge } from '../components/risk/RiskTierBadge'
import { GraphFlagBadge } from '../components/risk/GraphFlagBadge'
import { CaseGraph } from '../components/graph/CaseGraph'
import { AiInvestigationPanel } from '../components/investigation/AiInvestigationPanel'
import { InvestigatingState } from '../components/investigation/InvestigatingState'
import { HumanReviewPanel } from '../components/investigation/HumanReviewPanel'
import { EvidenceList } from '../components/evidence/EvidenceItemCard'
import { useCase, useCaseGraph, useCaseInvestigation, useInvestigate } from '../hooks/useCases'
import { formatConfidencePercent, formatScorePercent, formatTransactionDt, relationshipTypeLabel, timelineEvidence } from '../utils/format'
import { ApiError } from '../services/apiClient'
import './pages.css'

export function CaseInvestigationPage() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate = useNavigate()
  const caseQuery = useCase(caseId)
  const graphQuery = useCaseGraph(caseId)
  const investigationQuery = useCaseInvestigation(caseId)
  const investigateMutation = useInvestigate(caseId ?? '')

  if (caseQuery.isLoading) {
    return (
      <PageShell title="Loading case…">
        <Skeleton height={300} />
      </PageShell>
    )
  }

  if (caseQuery.isError) {
    const notFound = caseQuery.error instanceof ApiError && caseQuery.error.status === 404
    return (
      <PageShell title="Case Investigation">
        <StatePanel
          icon={<XCircleIcon />}
          variant="error"
          title={notFound ? 'Case not found' : 'Could not load this case'}
          description={notFound ? `No case exists with ID "${caseId}".` : (caseQuery.error as Error).message}
          actionLabel="Back to Case Queue"
          onAction={() => navigate('/cases')}
        />
      </PageShell>
    )
  }

  const c = caseQuery.data!
  const report = investigateMutation.data?.investigation_report ?? (investigationQuery.notFound ? undefined : investigationQuery.data)
  const hasReport = Boolean(report)

  return (
    <PageShell
      action={
        <Link to="/cases" className="btn btn-ghost btn-sm">
          ← Back to queue
        </Link>
      }
    >
      <div className="case-header">
        <h1 className="page-title case-header-id">{c.case_id}</h1>
        <RiskTierBadge tier={c.ml_risk_tier} />
        {hasReport ? <span className="badge badge-status-investigated">Investigated</span> : <span className="badge badge-status-not-investigated">Not investigated</span>}
      </div>
      <p className="page-subtitle">{formatTransactionDt(c.trigger_transaction_dt)}</p>

      <div className="investigation-layout">
        <div className="investigation-main">
          <Card title="Why This Case Was Flagged">
            <div className="two-col-signals">
              <div>
                <p className="signal-column-title">ML signals (deterministic)</p>
                <ul className="signal-list">
                  <li className="signal-row">
                    <span className="signal-row-label">Risk score</span>
                    <span className="signal-row-value">{formatScorePercent(c.ml_risk_score)}</span>
                  </li>
                  <li className="signal-row">
                    <span className="signal-row-label">Risk tier</span>
                    <span className="signal-row-value">{c.ml_risk_tier}</span>
                  </li>
                  <li className="signal-row">
                    <span className="signal-row-label">Customer proxy confidence</span>
                    <span className="signal-row-value">{c.customer_proxy_confidence}</span>
                  </li>
                </ul>
              </div>
              <div>
                <p className="signal-column-title">Graph signals (deterministic)</p>
                {c.graph_evidence ? (
                  <ul className="signal-list">
                    <li className="signal-row">
                      <span className="signal-row-label">Community size</span>
                      <span className="signal-row-value">{c.graph_evidence.community_size}</span>
                    </li>
                    <li className="signal-row">
                      <span className="signal-row-label">Relationship types</span>
                      <span className="signal-row-value">
                        {c.graph_evidence.detected_relationship_types.map(relationshipTypeLabel).join(', ')}
                      </span>
                    </li>
                    <li className="signal-row">
                      <span className="signal-row-label">Rarity score</span>
                      <span className="signal-row-value">{c.graph_evidence.relationship_rarity_score.toFixed(2)}</span>
                    </li>
                    <li className="signal-row">
                      <span className="signal-row-label">Multi-attribute overlap</span>
                      <span className="signal-row-value">{c.graph_evidence.multi_attribute_overlap ? 'Yes' : 'No'}</span>
                    </li>
                  </ul>
                ) : (
                  <StatePanel icon={<XCircleIcon />} title="No shared infrastructure detected" />
                )}
              </div>
            </div>
            {c.graph_evidence && <p style={{ marginTop: 12, color: 'var(--color-text-secondary)', fontSize: 'var(--text-small-size)' }}>{c.graph_evidence.narrative}</p>}
          </Card>

          <Card
            title="Network"
            action={
              c.graph_evidence && (
                <Link to={`/cases/${c.case_id}/graph`} className="btn btn-secondary btn-sm">
                  Open Graph Explorer
                </Link>
              )
            }
          >
            {graphQuery.isLoading ? (
              <Skeleton height={300} />
            ) : graphQuery.data ? (
              <CaseGraph graph={graphQuery.data} height={320} />
            ) : (
              <StatePanel icon={<XCircleIcon />} title="Graph unavailable" />
            )}
          </Card>

          <Card title="Investigation Timeline">
            {report && timelineEvidence(report.evidence).length > 0 ? (
              <EvidenceList items={timelineEvidence(report.evidence)} />
            ) : (
              <StatePanel
                icon={<ClockIcon />}
                title={hasReport ? 'No transaction-history evidence was retrieved for this case' : 'Timeline not yet available'}
                description={hasReport ? undefined : 'The timeline is built from evidence gathered during an investigation — start one below to populate it.'}
              />
            )}
          </Card>

          <Card title="AI Investigation">
            {investigateMutation.isRunning ? (
              <InvestigatingState />
            ) : investigateMutation.isError ? (
              <StatePanel
                icon={<XCircleIcon />}
                variant="error"
                title="Investigation failed"
                description={investigateMutation.error instanceof ApiError ? investigateMutation.error.message : 'Unknown error'}
                actionLabel="Try again"
                onAction={() => caseId && investigateMutation.mutate({ case_id: caseId })}
              />
            ) : report ? (
              <AiInvestigationPanel report={report} />
            ) : (
              <StatePanel
                icon={<ClockIcon />}
                title="This case has not been investigated yet"
                description="Start an investigation to see the agent's findings, evidence, and recommendation."
                actionLabel="Start Investigation"
                onAction={() => caseId && investigateMutation.mutate({ case_id: caseId })}
              />
            )}
          </Card>
        </div>

        <div className="investigation-rail">
          <Card title="Risk Summary">
            <div className="risk-summary-grid">
              <div className="signal-row">
                <span className="signal-row-label">ML score</span>
                <span className="signal-row-value">{formatScorePercent(c.ml_risk_score)}</span>
              </div>
              <div className="signal-row">
                <span className="signal-row-label">ML tier</span>
                <RiskTierBadge tier={c.ml_risk_tier} />
              </div>
              <div className="signal-row">
                <span className="signal-row-label">Graph coordination</span>
                <GraphFlagBadge flagged={Boolean(c.graph_evidence)} />
              </div>
              <div className="signal-row">
                <span className="signal-row-label">Investigation confidence</span>
                <span className="signal-row-value">{report ? formatConfidencePercent(report.confidence) : '—'}</span>
              </div>
            </div>
            {!hasReport && !investigateMutation.isRunning && (
              <Button variant="primary" style={{ marginTop: 16, width: '100%' }} onClick={() => caseId && investigateMutation.mutate({ case_id: caseId })}>
                Start Investigation
              </Button>
            )}
          </Card>

          {report && (
            <Card title="Human Review">
              <HumanReviewPanel recommendation={report.recommendation} humanApprovalRequired={report.human_approval_required_for_action} />
            </Card>
          )}

          {report && (
            <Link to={`/cases/${c.case_id}/report`} className="btn btn-secondary" style={{ textAlign: 'center' }}>
              Open Investigation Report
            </Link>
          )}
        </div>
      </div>
    </PageShell>
  )
}
