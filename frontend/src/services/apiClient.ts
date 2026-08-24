/**
 * The ONLY place this app talks to the network. One typed function per
 * endpoint in docs/API.md — no generic "call any URL" escape hatch, so
 * there is no code path that could call something outside the
 * documented contract (docs/FRONTEND_ARCHITECTURE.md §4).
 */
import type {
  ApiErrorBody,
  CaseDetailResponse,
  CaseGraphResponse,
  CaseListParams,
  CaseListResponse,
  HealthResponse,
  InvestigateRequest,
  InvestigationResponse,
} from '../types/api'

export class ApiError extends Error {
  status: number
  errorCode: string
  requestId: string

  constructor(status: number, body: ApiErrorBody) {
    super(body.message)
    this.name = 'ApiError'
    this.status = status
    this.errorCode = body.error_code
    this.requestId = body.request_id
  }
}

/** 404 investigation_not_found is a normal, expected outcome (no
 * investigation has run yet) — callers use this to distinguish that
 * from a genuine failure without string-matching error codes. */
export class InvestigationNotFoundError extends ApiError {}

/** Shared React Query retry predicate: a 4xx (case not found, malformed
 * request, unsupported mode) will never succeed on retry — only retry
 * something that might be transient (network blip, 5xx, timeout).
 * Without this, a genuinely-nonexistent case sits in a "loading" state
 * for an extra retry round-trip before showing its error (found during
 * Phase 5B visual validation). */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false
  return failureCount < 2
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })

  if (!response.ok) {
    const body = (await response.json().catch(() => ({
      error_code: 'unknown_error',
      message: `request failed with status ${response.status}`,
      request_id: '',
    }))) as ApiErrorBody
    if (response.status === 404 && body.error_code === 'investigation_not_found') {
      throw new InvestigationNotFoundError(response.status, body)
    }
    throw new ApiError(response.status, body)
  }

  return (await response.json()) as T
}

function queryString(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value))
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

export const apiClient = {
  getHealth: () => request<HealthResponse>('/health'),

  listCases: (params: CaseListParams = {}) =>
    request<CaseListResponse>(`/api/v1/cases${queryString(params as Record<string, string | number | boolean | undefined>)}`),

  getCase: (caseId: string) => request<CaseDetailResponse>(`/api/v1/cases/${encodeURIComponent(caseId)}`),

  getCaseGraph: (caseId: string) => request<CaseGraphResponse>(`/api/v1/cases/${encodeURIComponent(caseId)}/graph`),

  getCaseInvestigation: (caseId: string) =>
    request<InvestigationResponse['investigation_report']>(`/api/v1/cases/${encodeURIComponent(caseId)}/investigation`),

  investigate: (body: InvestigateRequest) =>
    request<InvestigationResponse>('/api/v1/cases/investigate', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
}
