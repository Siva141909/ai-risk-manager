/**
 * 1:1 mirror of src/api/schemas.py / docs/API.md — field names and
 * shapes match the wire contract exactly, snake_case preserved
 * (docs/FRONTEND_ARCHITECTURE.md §4: no camelCase transform layer, so
 * this file can be diffed against the backend schema directly).
 */

export type RiskTier = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'
export type InvestigationMode = 'real_time'
export type InvestigationStatusFilter = 'investigated' | 'not_investigated'
export type RecommendationType = 'close' | 'monitor' | 'investigate_further' | 'escalate_to_human_analyst'
export type ValidationStatus = 'passed' | 'failed_repaired' | 'failed_human_review'

export interface ApiErrorBody {
  error_code: string
  message: string
  request_id: string
}

export interface HealthResponse {
  status: 'ok'
  app_version: string
  model_version: string
  graph_config_version: string
  environment: string
  llm_backend: string
}

export interface CaseSummaryResponse {
  case_id: string
  transaction_id: number
  transaction_dt: number
  ml_risk_score: number
  ml_risk_tier: RiskTier
  graph_flagged: boolean
  has_investigation: boolean
}

export interface CaseListResponse {
  items: CaseSummaryResponse[]
  total: number
  limit: number
  offset: number
}

export interface GraphEvidenceResponse {
  community_id: number
  community_size: number
  n_shared_devices: number
  n_shared_ips: number
  n_shared_bank_accounts: number
  multi_attribute_overlap: boolean
  relationship_rarity_score: number
  temporal_concentration_hours: number | null
  detected_relationship_types: string[]
  narrative: string
}

export interface CaseDetailResponse {
  case_id: string
  trigger_transaction_ids: number[]
  trigger_transaction_dt: number
  ml_risk_score: number
  ml_risk_tier: RiskTier
  customer_proxy_id: string
  customer_proxy_confidence: string
  graph_lookup_keys: Record<string, string | null>
  graph_evidence: GraphEvidenceResponse | null
  has_investigation: boolean
}

export interface GraphVizNode {
  customer_proxy_id: string
  is_center: boolean
}

export interface GraphVizEdge {
  source: string
  target: string
  relationship_type: string
  shared_entity_value: string
}

export interface CaseGraphResponse {
  case_id: string
  graph_evidence: GraphEvidenceResponse | null
  nodes: GraphVizNode[]
  edges: GraphVizEdge[]
}

export interface InvestigateRequest {
  transaction_id?: number
  case_id?: string
  investigation_mode?: InvestigationMode
  cutoff_dt?: number
}

export interface TransactionInfo {
  transaction_id: number
  transaction_dt: number
}

export interface ProcessingMetadata {
  request_id: string
  llm_backend: string
  cache_hit: boolean
  investigation_mode: InvestigationMode
  total_duration_ms: number
  case_lookup_duration_ms: number
  agent_duration_ms: number | null
}

export interface EvidenceItem {
  evidence_id: string
  source_tool: string
  summary: string
  is_retrospective: boolean
}

export interface InvestigationReport {
  case_id: string
  summary: string
  trigger: string
  risk_tier: RiskTier | string
  graph_findings: string
  behavioral_findings: string
  legitimate_explanations: string[]
  conflicting_evidence: boolean
  conflict_description: string | null
  policy_findings: string[]
  recommendation: RecommendationType
  requires_human_review: boolean
  human_approval_required_for_action: boolean
  confidence: number
  evidence: EvidenceItem[]
  retrospective_evidence_used: boolean
  investigation_complete: boolean
  validation_status: ValidationStatus
}

export interface InvestigationResponse {
  case_id: string
  transaction: TransactionInfo
  ml_risk_score: number
  ml_risk_tier: RiskTier
  graph_summary: GraphEvidenceResponse | null
  investigation_report: InvestigationReport
  evidence: EvidenceItem[]
  recommendation: string
  confidence: number
  human_approval_required: boolean
  processing: ProcessingMetadata
}

export interface CaseListParams {
  risk_tier?: RiskTier
  graph_flagged?: boolean
  investigation_status?: InvestigationStatusFilter
  start_dt?: number
  end_dt?: number
  limit?: number
  offset?: number
}
