export const queryKeys = {
  health: () => ['health'] as const,
  info: () => ['info'] as const,
  settings: () => ['settings'] as const,
  watchlists: () => ['watchlists'] as const,
  latestRun: () => ['run', 'latest'] as const,
  history: {
    all: () => ['history'] as const,
    run: (runId: string) => ['history', runId] as const,
  },
}
