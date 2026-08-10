type RuntimeEnvironment = {
  VITE_API_BASE_URL?: string
  VITE_USE_MOCKS?: string
}

function environment(): RuntimeEnvironment {
  return (import.meta as ImportMeta & { env?: RuntimeEnvironment }).env ?? {}
}

export function apiBaseUrl(): string {
  return (environment().VITE_API_BASE_URL || '/api/v1').replace(/\/$/, '')
}

export function shouldUseMocks(): boolean {
  const value = String(environment().VITE_USE_MOCKS ?? 'false').toLowerCase()
  return value === 'true' || value === '1' || value === 'yes'
}
