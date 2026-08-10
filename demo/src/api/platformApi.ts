import type { components } from './generated/schema'
import { apiClient, type ApiPage } from './client'

export type User = components['schemas']['User']
export type RoleDefinition = components['schemas']['RoleDefinition']
export type PermissionMatrix = components['schemas']['PermissionMatrix']
export type ProjectSummary = components['schemas']['ProjectSummary']
export type AuditEvent = components['schemas']['AuditEvent']
export type Notification = components['schemas']['Notification']
export type SearchResult = components['schemas']['SearchResult']
export type Qualification = components['schemas']['Qualification']
export type QualificationStats = components['schemas']['QualificationStats']
export type Fragment = components['schemas']['Fragment']
export type FragmentStats = components['schemas']['FragmentStats']
export type ModelProvider = components['schemas']['ModelProviderMasked']
export type ModelRoute = components['schemas']['ModelRoute']
export type GenerationSettings = components['schemas']['GenerationSettings']
export type DeploymentSettings = components['schemas']['DeploymentSettings']
export type DocumentTemplateSettings = components['schemas']['DocumentTemplateSettings']
export type NotificationSettings = components['schemas']['NotificationSettings']
export type AgentStatus = components['schemas']['AgentStatus']
export type JobRef = components['schemas']['JobRef']

export type UserQuery = {
  page?: number
  pageSize?: number
  keyword?: string
  role?: string
  department?: string
  status?: string
  sortBy?: 'createdAt' | 'name' | 'email'
  sortOrder?: 'asc' | 'desc'
}

export type LibraryQuery = {
  page?: number
  pageSize?: number
  keyword?: string
  category?: string
  status?: string
  expiresWithinDays?: number
  searchMode?: 'keyword' | 'semantic'
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

export type AuditQuery = {
  page?: number
  pageSize?: number
  actor?: string
  action?: string
  resource?: string
  dateFrom?: string
  dateTo?: string
  sortOrder?: 'asc' | 'desc'
}

export const platformApi = {
  getMe: () => apiClient.get<User>('/auth/me'),
  updateMe: (body: components['schemas']['UpdateProfileRequest']) => apiClient.patch<User>('/auth/me', body),

  listUsers: (query: UserQuery = {}) => apiClient.getPage<User[]>('/users', { query }),
  inviteUser: (body: components['schemas']['InviteUserRequest']) => apiClient.post<{ user: User; invitationExpiresAt: string }>('/users/invitations', body),
  updateUser: (id: string, version: number, body: components['schemas']['UpdateUserRequest']) => apiClient.patch<User>(`/users/${encodeURIComponent(id)}`, body, { ifMatch: version }),
  setUserStatus: (id: string, status: 'active' | 'disabled', reason: string) => apiClient.post<User>(`/users/${encodeURIComponent(id)}/status`, { status, reason }),
  resendInvitation: (id: string) => apiClient.post<{ sent: boolean }>(`/users/${encodeURIComponent(id)}/invitations/resend`),
  sendPasswordReset: (id: string) => apiClient.post<{ sent: boolean }>(`/users/${encodeURIComponent(id)}/password-reset-email`),
  getUserProjects: (id: string) => apiClient.getPage<ProjectSummary[]>(`/users/${encodeURIComponent(id)}/projects`, { query: { page: 1, pageSize: 100 } }),
  getUserActivity: (id: string) => apiClient.getPage<AuditEvent[]>(`/users/${encodeURIComponent(id)}/activity`, { query: { page: 1, pageSize: 100 } }),
  listRoles: () => apiClient.get<RoleDefinition[]>('/roles'),
  getPermissionMatrix: () => apiClient.get<PermissionMatrix>('/permissions/matrix'),

  listNotifications: () => apiClient.getPage<Notification[]>('/notifications', { query: { page: 1, pageSize: 100 } }),
  markNotificationRead: (id: string) => apiClient.patch<Notification>(`/notifications/${encodeURIComponent(id)}`, { isRead: true }, { ifMatch: 1 }),
  markAllNotificationsRead: () => apiClient.post<{ updatedCount: number }>('/notifications/read-all', undefined, { idempotencyKey: crypto.randomUUID() }),
  search: (keyword: string, limit = 20) => apiClient.get<SearchResult[]>('/global-search', { query: { keyword, limit } }),
  getJob: (id: string) => apiClient.get<JobRef>(`/jobs/${encodeURIComponent(id)}`),

  getQualificationStats: () => apiClient.get<QualificationStats>('/qualifications/stats'),
  listQualifications: (query: LibraryQuery = {}) => apiClient.getPage<Qualification[]>('/qualifications', { query }),
  createQualification: (body: components['schemas']['CreateQualificationRequest']) => apiClient.post<Qualification>('/qualifications', body),
  updateQualification: (id: string, version: number, body: components['schemas']['UpdateQualificationRequest']) => apiClient.patch<Qualification>(`/qualifications/${encodeURIComponent(id)}`, body, { ifMatch: version }),
  addQualificationVersion: (id: string, body: { fileId: string; documentVersion: string; changeNote: string }) => apiClient.post<Qualification>(`/qualifications/${encodeURIComponent(id)}/versions`, body),
  deleteQualification: (id: string, reason: string) => apiClient.delete<void>(`/qualifications/${encodeURIComponent(id)}`, { reason }),
  importQualifications: (fileId: string) => apiClient.post<JobRef>('/qualifications/imports', { fileId }),
  downloadQualificationTemplate: () => apiClient.get<Blob>('/qualifications/import-template', { responseType: 'blob' }),
  downloadQualification: (id: string) => apiClient.get<Blob>(`/qualifications/${encodeURIComponent(id)}/download`, { responseType: 'blob' }),

  getFragmentStats: () => apiClient.get<FragmentStats>('/fragments/stats'),
  listFragments: (query: LibraryQuery = {}) => apiClient.getPage<Fragment[]>('/fragments', { query }),
  semanticSearchFragments: (query: string, category?: string, limit = 100) => apiClient.post<Fragment[]>('/fragments/semantic-search', { query, category, limit }),
  createFragment: (body: components['schemas']['CreateFragmentRequest']) => apiClient.post<Fragment>('/fragments', body),
  updateFragment: (id: string, version: number, body: components['schemas']['UpdateFragmentRequest']) => apiClient.patch<Fragment>(`/fragments/${encodeURIComponent(id)}`, body, { ifMatch: version }),
  addFragmentVersion: (id: string, body: { content?: string; fileId?: string; changeNote: string }) => apiClient.post<Fragment>(`/fragments/${encodeURIComponent(id)}/versions`, body),
  addFragmentReference: (id: string, body: { bidTaskId: string; materialId?: string }) => apiClient.post<{ referenced: boolean; useCount: number }>(`/fragments/${encodeURIComponent(id)}/references`, body),
  deleteFragment: (id: string, reason: string) => apiClient.delete<void>(`/fragments/${encodeURIComponent(id)}`, { reason }),

  listModelProviders: () => apiClient.get<ModelProvider[]>('/settings/model-providers'),
  createModelProvider: (body: components['schemas']['CreateModelProviderRequest']) => apiClient.post<ModelProvider>('/settings/model-providers', body),
  updateModelProvider: (id: string, version: number, body: components['schemas']['UpdateModelProviderRequest']) => apiClient.patch<ModelProvider>(`/settings/model-providers/${encodeURIComponent(id)}`, body, { ifMatch: version }),
  testModelProvider: (id: string) => apiClient.post<JobRef>(`/settings/model-providers/${encodeURIComponent(id)}/test`),
  getModelRoutes: () => apiClient.get<ModelRoute[]>('/settings/model-routes'),
  updateModelRoutes: (routes: ModelRoute[]) => apiClient.put<ModelRoute[]>('/settings/model-routes', { routes }),
  getGenerationSettings: () => apiClient.get<GenerationSettings>('/settings/generation'),
  updateGenerationSettings: (body: GenerationSettings) => apiClient.put<GenerationSettings>('/settings/generation', body),
  getDeploymentSettings: () => apiClient.get<DeploymentSettings>('/settings/deployment'),
  updateDeploymentSettings: (body: Omit<DeploymentSettings, 'version'>) => apiClient.put<DeploymentSettings>('/settings/deployment', body),
  getDocumentTemplateSettings: () => apiClient.get<DocumentTemplateSettings>('/settings/document-template'),
  updateDocumentTemplateSettings: (body: Omit<DocumentTemplateSettings, 'version'>) => apiClient.put<DocumentTemplateSettings>('/settings/document-template', body),
  getNotificationSettings: () => apiClient.get<NotificationSettings>('/settings/notifications'),
  updateNotificationSettings: (body: Omit<NotificationSettings, 'version'>) => apiClient.put<NotificationSettings>('/settings/notifications', body),
  getAgentStatus: () => apiClient.get<AgentStatus[]>('/settings/agents/status'),

  listAuditEvents: (query: AuditQuery = {}) => apiClient.getPage<AuditEvent[]>('/audit-events', { query }),
  exportAuditEvents: (query: Omit<AuditQuery, 'page' | 'pageSize'> = {}) => apiClient.get<Blob>('/audit-events/export', { query, responseType: 'blob' }),
}

export function saveBlob(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  anchor.click()
  URL.revokeObjectURL(url)
}

export type PageResult<T> = ApiPage<T>
