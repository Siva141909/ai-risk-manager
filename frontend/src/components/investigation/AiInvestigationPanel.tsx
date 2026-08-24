import { SparklesIcon } from '../common/Icons'
import { Badge } from '../common/Badge'
import { EvidenceList } from '../evidence/EvidenceItemCard'
import { RecommendationBadge } from './RecommendationBadge'
import { formatConfidencePercent, nonTimelineEvidence } from '../../utils/format'
import type { InvestigationReport } from '../../types/api'
import '../evidence/evidence.css'
import './investigation.css'

/**
 * Structured investigation display (Phase 5B.10) — never an "ask AI
 * anything" chat box. Every prose field is rendered inside an
 * `.ai-block` (dashed border, AI-tinted, docs/DESIGN_SYSTEM.md §7) so
 * it is visually distinct from the deterministic EvidenceList below it.
 */
export function AiInvestigationPanel({ report }: { report: InvestigationReport }) {
  const isFailSafe = report.validation_status === 'failed_human_review'

  return (
    <div className="ai-investigation-panel">
      <div className="ai-panel-heading">
        <SparklesIcon />
        <span>AI INVESTIGATION</span>
        <Badge variant="badge-ai">confidence {formatConfidencePercent(report.confidence)}</Badge>
      </div>

      {isFailSafe && (
        <div className="ai-fail-safe-note">
          This investigation could not be automatically validated and was routed directly to human
          review — no AI-generated findings are shown below because none were produced with sufficient
          confidence to display (docs/SAFETY_MODEL.md).
        </div>
      )}

      <AiBlock title="Summary">{report.summary}</AiBlock>

      {!isFailSafe && (
        <>
          <AiBlock title="Graph Findings">{report.graph_findings}</AiBlock>
          <AiBlock title="Behavioral Findings">{report.behavioral_findings}</AiBlock>

          {report.legitimate_explanations.length > 0 && (
            <AiBlock title="Legitimate Explanations">
              <ul className="ai-block-list">
                {report.legitimate_explanations.map((exp, i) => (
                  <li key={i}>{exp}</li>
                ))}
              </ul>
            </AiBlock>
          )}

          {report.conflicting_evidence && (
            <AiBlock title="Conflicting Evidence">{report.conflict_description ?? '—'}</AiBlock>
          )}

          {report.policy_findings.length > 0 && (
            <AiBlock title="Policy Findings">
              <ul className="ai-block-list">
                {report.policy_findings.map((p, i) => (
                  <li key={i}>{p}</li>
                ))}
              </ul>
            </AiBlock>
          )}
        </>
      )}

      <div className="ai-recommendation-row">
        <span className="ai-recommendation-label">Recommendation:</span>
        <RecommendationBadge recommendation={report.recommendation} />
      </div>

      <h3 className="evidence-section-title">Evidence</h3>
      <EvidenceList items={nonTimelineEvidence(report.evidence)} />
    </div>
  )
}

function AiBlock({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="ai-block">
      <div className="ai-block-header">
        <h4 className="ai-block-title">{title}</h4>
      </div>
      <div className="ai-block-body">{children}</div>
    </div>
  )
}
