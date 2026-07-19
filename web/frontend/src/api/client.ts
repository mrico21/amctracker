import type {
  EventsResponse,
  HealthResponse,
  HistoryResponse,
  InfoResponse,
  JobStatus,
  RunResult,
  RunTriggerResponse,
  SchedulerStatus,
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

function put<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export const apiClient = {
  health: () => get<HealthResponse>('/health'),
  info: () => get<InfoResponse>('/info'),
  settings: () => get<SettingsResponse>('/settings'),
  updateSettings: (body: Partial<SettingsResponse>) => put<SettingsResponse>('/settings', body),
  watchlists: () => get<WatchlistEntry[]>('/watchlists'),
  watchlist: (id: string) => get<WatchlistEntry>(`/watchlists/${id}`),
  history: () => get<HistoryResponse>('/history'),
  historyRun: (runId: string) => get<RunResult>(`/history/${runId}`),
  latestRun: () => get<RunResult>('/run/latest'),
  triggerRun: () => post<RunTriggerResponse>('/run'),
  runStatus: () => get<JobStatus>('/run/status'),
  cancelRun: () => post<{ status: string }>('/run/cancel'),
  schedulerStatus: () => get<SchedulerStatus>('/scheduler/status'),
  events: () => get<EventsResponse>('/events'),
}
