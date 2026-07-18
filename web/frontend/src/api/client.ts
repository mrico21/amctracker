import type {
  HealthResponse,
  HistoryResponse,
  InfoResponse,
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
  console.log('[DIAG] fetch start', url, options)
  let res: Response
  try {
    res = await fetch(url, options)
  } catch (err) {
    console.log('[DIAG] fetch threw exception', url, err)
    throw err
  }
  console.log('[DIAG] fetch response', url, 'status=', res.status, 'ok=', res.ok)
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
  const opts: RequestInit = {
    method: 'POST',
    headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  }
  console.log('[DIAG] post called', `${BASE}${path}`, opts)
  return request<T>(path, opts)
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
}
