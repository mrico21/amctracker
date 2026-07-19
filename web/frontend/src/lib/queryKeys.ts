export const queryKeys = {
  health: () => ['health'] as const,
  info: () => ['info'] as const,
  settings: () => ['settings'] as const,
  watchlists: () => ['watchlists'] as const,
  watchlist: (id: string) => ['watchlists', id] as const,
  latestRun: () => ['run', 'latest'] as const,
  jobStatus: () => ['run', 'status'] as const,
  schedulerStatus: () => ['scheduler', 'status'] as const,
  events: () => ['events'] as const,
  history: {
    all: () => ['history'] as const,
    run: (runId: string) => ['history', runId] as const,
  },
}
