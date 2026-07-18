import type {
  HealthResponse,
  HistoryResponse,
  InfoResponse,
  JobStatus,
  RunResult,
  RunTriggerResponse,
  SettingsResponse,
  WatchlistEntry,
} from './types'

const BASE = '/api/v1'

export class ApiError extends Error {
  readonly status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${BASE}${path}`
  const res = await fetch(url, options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText })) as { detail?: string }
    throw new ApiError(body.detail ?? `HTTP ${res.status}`, res.status)
  }
  return res.json() as Promise<T>
}

function get<T>(path: string): Promise<T> {
  return request<T>(path)
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
}

export const apiClient = {
  health: () => get<HealthResponse>('/health'),
  info: () => get<InfoResponse>('/info'),
  settings: () => get<SettingsResponse>('/settings'),
  watchlists: () => get<WatchlistEntry[]>('/watchlists'),
  history: () => get<HistoryResponse>('/history'),
  historyRun: (runId: string) => get<RunResult>(`/history/${runId}`),
  latestRun: () => get<RunResult>('/run/latest'),
  triggerRun: () => post<RunTriggerResponse>('/run'),
  runStatus: () => get<JobStatus>('/run/status'),
  cancelRun: () => post<{ status: string }>('/run/cancel'),
}
