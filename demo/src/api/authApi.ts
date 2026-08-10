import type { components } from './generated/schema'
import { apiClient } from './client'
import { clearAccessToken, writeAccessToken } from './authStorage'

export type LoginValues = components['schemas']['LoginRequest'] & { remember: boolean }
export type AuthSession = components['schemas']['AuthSession']

type LegacyAuthSession = {
  access_token: string
  access_token_expires_at: string
  user: Record<string, unknown>
  permissions: string[]
}

function normalizeSession(value: AuthSession | LegacyAuthSession): AuthSession {
  if ('accessToken' in value) return value
  const legacyUser = value.user
  return {
    accessToken: value.access_token,
    accessTokenExpiresAt: value.access_token_expires_at,
    permissions: value.permissions,
    user: {
      id: String(legacyUser.id),
      tenantId: String(legacyUser.tenant_id),
      email: String(legacyUser.email),
      name: String(legacyUser.name),
      phone: legacyUser.phone ? String(legacyUser.phone) : undefined,
      role: legacyUser.role as AuthSession['user']['role'],
      department: String(legacyUser.department ?? ''),
      status: legacyUser.status as AuthSession['user']['status'],
      projectCount: Number(legacyUser.project_count ?? 0),
      lastLoginAt: legacyUser.last_login_at ? String(legacyUser.last_login_at) : undefined,
      version: Number(legacyUser.version ?? 1),
      createdAt: String(legacyUser.created_at),
      updatedAt: String(legacyUser.updated_at),
    },
  }
}

export async function loginSession(values: LoginValues): Promise<AuthSession> {
  const raw = await apiClient.post<AuthSession | LegacyAuthSession>('/auth/login', {
    email: values.email,
    password: values.password,
  })
  const session = normalizeSession(raw)
  writeAccessToken(session.accessToken, session.accessTokenExpiresAt, values.remember)
  return session
}

export async function logoutSession(): Promise<void> {
  try {
    await apiClient.post('/auth/logout')
  } finally {
    clearAccessToken()
  }
}

export async function requestPasswordReset(email: string): Promise<void> {
  await apiClient.post('/auth/password/forgot', { email })
}
