import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import {
  tasks as initialBidTasks,
  materials as initialMaterials,
  qualifications as initialQualifications,
  fragments as initialFragments,
  users as initialUsers,
  notifications as initialBidNotifications,
} from '../mock/data'
import { evaluationTasks as initialEvaluationTasks, evalNotifications as initialEvaluationNotifications } from '../mock/evaluationData'
import { loginSession, logoutSession, type LoginValues } from '../api/authApi'
import { readAccessToken } from '../api/authStorage'
import { shouldUseMocks } from '../api/runtime'
import { platformApi, type User } from '../api/platformApi'

type DemoContextValue = {
  loggedIn: boolean
  authReady: boolean
  currentUser: User | null
  updateCurrentUser: (user: User) => void
  login: (values?: LoginValues) => Promise<void>
  logout: () => Promise<void>
  bidTasks: any[]
  addBidTask: (task: any, taskMaterials?: any[]) => void
  updateBidTask: (id: string, patch: Record<string, any>) => void
  getTaskMaterials: (id?: string) => any[]
  updateTaskMaterial: (taskId: string, materialId: string, patch: Record<string, any>) => void
  addTaskMaterial: (taskId: string, material: any) => void
  removeTaskMaterial: (taskId: string, materialId: string) => void
  evaluationTasks: any[]
  addEvaluationTask: (task: any) => void
  updateEvaluationTask: (id: string, patch: Record<string, any>) => void
  qualifications: any[]
  setQualifications: React.Dispatch<React.SetStateAction<any[]>>
  fragments: any[]
  setFragments: React.Dispatch<React.SetStateAction<any[]>>
  users: any[]
  setUsers: React.Dispatch<React.SetStateAction<any[]>>
  appNotifications: any[]
  markNotificationRead: (id: string) => void
  markAllNotificationsRead: () => void
  permissions: string[]
  resetDemoData: () => void
}

const DemoContext = createContext<DemoContextValue | null>(null)

const STORAGE_KEY = 'bid-platform-demo-state-v2'
const DEMO_PERMISSIONS = ['*', 'admin:read', 'admin:write', 'library:read', 'library:write', 'settings:write']
const MOCK_USER: User = {
  id: 'U001',
  tenantId: 'demo-tenant',
  name: '张明远',
  email: 'zhangmy@zhilian-tech.com',
  role: 'project_lead',
  department: '投标部',
  status: 'active',
  projectCount: 3,
  version: 1,
  createdAt: '2026-08-01T09:00:00Z',
  updatedAt: '2026-08-04T14:30:00Z',
}

const ROLE_PERMISSIONS: Record<User['role'], string[]> = {
  admin: ['*'],
  project_lead: ['projects:read', 'projects:write', 'bids:read', 'bids:write', 'bids:review', 'users:read', 'library:read', 'library:write'],
  reviewer: ['projects:read', 'bids:read', 'bids:review', 'library:read'],
  member: ['projects:read', 'bids:read', 'library:read'],
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value))
}

function buildInitialMaterials() {
  return Object.fromEntries(initialBidTasks.map(task => [task.id, clone(initialMaterials)]))
}

function buildInitialNotifications() {
  return [
    ...initialEvaluationNotifications.map(item => ({ ...clone(item), source: 'eval' as const })),
    ...initialBidNotifications.map(item => ({ ...clone(item), source: 'bid' as const })),
  ]
}

function readStoredState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function DemoProvider({ children }: { children: React.ReactNode }) {
  const mockMode = shouldUseMocks()
  const stored = mockMode && typeof window !== 'undefined' ? readStoredState() : null
  const [loggedIn, setLoggedIn] = useState(() => (
    mockMode ? sessionStorage.getItem('bid-demo-logged-in') === 'true' : Boolean(readAccessToken())
  ))
  const [authReady, setAuthReady] = useState(() => mockMode || !readAccessToken())
  const [currentUser, setCurrentUser] = useState<User | null>(() => mockMode ? MOCK_USER : null)
  const [permissions, setPermissions] = useState<string[]>(() => mockMode ? DEMO_PERMISSIONS : [])
  const [bidTasks, setBidTasks] = useState<any[]>(() => mockMode ? stored?.bidTasks || clone(initialBidTasks) : [])
  const [taskMaterials, setTaskMaterials] = useState<Record<string, any[]>>(() => mockMode ? stored?.taskMaterials || buildInitialMaterials() : {})
  const [evaluationTasks, setEvaluationTasks] = useState<any[]>(() => mockMode ? stored?.evaluationTasks || clone(initialEvaluationTasks) : [])
  const [qualifications, setQualifications] = useState<any[]>(() => mockMode ? stored?.qualifications || clone(initialQualifications) : [])
  const [fragments, setFragments] = useState<any[]>(() => mockMode ? stored?.fragments || clone(initialFragments) : [])
  const [users, setUsers] = useState<any[]>(() => mockMode ? stored?.users || clone(initialUsers) : [])
  const [appNotifications, setAppNotifications] = useState<any[]>(() => mockMode ? stored?.appNotifications || buildInitialNotifications() : [])

  useEffect(() => {
    if (!mockMode) return
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      bidTasks,
      taskMaterials,
      evaluationTasks,
      qualifications,
      fragments,
      users,
      appNotifications,
    }))
  }, [mockMode, bidTasks, taskMaterials, evaluationTasks, qualifications, fragments, users, appNotifications])

  useEffect(() => {
    if (mockMode || !readAccessToken()) return
    let active = true
    platformApi.getMe()
      .then(user => {
        if (!active) return
        setCurrentUser(user)
        setPermissions(ROLE_PERMISSIONS[user.role])
        setLoggedIn(true)
      })
      .catch(() => {
        if (!active) return
        setCurrentUser(null)
        setLoggedIn(false)
      })
      .finally(() => {
        if (active) setAuthReady(true)
      })
    return () => { active = false }
  }, [mockMode])

  const login = useCallback(async (values?: LoginValues) => {
    if (!mockMode) {
      if (!values) throw new Error('请输入登录凭证')
      const session = await loginSession(values)
      setPermissions(session.permissions)
      setCurrentUser(session.user)
    }
    if (mockMode) sessionStorage.setItem('bid-demo-logged-in', 'true')
    setLoggedIn(true)
  }, [mockMode])

  const logout = useCallback(async () => {
    if (!mockMode) {
      try {
        await logoutSession()
      } catch {
        // The local session must still be cleared when the API is unavailable.
      }
    }
    if (mockMode) sessionStorage.removeItem('bid-demo-logged-in')
    if (!mockMode) setCurrentUser(null)
    setLoggedIn(false)
  }, [mockMode])

  const addBidTask = useCallback((task: any, materials = clone(initialMaterials)) => {
    setBidTasks(prev => [task, ...prev])
    setTaskMaterials(prev => ({ ...prev, [task.id]: clone(materials) }))
  }, [])

  const updateBidTask = useCallback((id: string, patch: Record<string, any>) => {
    setBidTasks(prev => prev.map(task => task.id === id ? { ...task, ...patch } : task))
  }, [])

  const getTaskMaterials = useCallback((id?: string) => {
    if (!id) return mockMode ? clone(initialMaterials) : []
    return taskMaterials[id] || (mockMode ? clone(initialMaterials) : [])
  }, [mockMode, taskMaterials])

  const updateTaskMaterial = useCallback((taskId: string, materialId: string, patch: Record<string, any>) => {
    setTaskMaterials(prev => ({
      ...prev,
      [taskId]: (prev[taskId] || (mockMode ? clone(initialMaterials) : [])).map(item => item.id === materialId ? { ...item, ...patch } : item),
    }))
  }, [mockMode])

  const addTaskMaterial = useCallback((taskId: string, material: any) => {
    setTaskMaterials(prev => ({
      ...prev,
      [taskId]: [...(prev[taskId] || (mockMode ? clone(initialMaterials) : [])), material],
    }))
  }, [mockMode])

  const removeTaskMaterial = useCallback((taskId: string, materialId: string) => {
    setTaskMaterials(prev => ({
      ...prev,
      [taskId]: (prev[taskId] || (mockMode ? clone(initialMaterials) : [])).filter(item => item.id !== materialId),
    }))
  }, [mockMode])

  const addEvaluationTask = useCallback((task: any) => setEvaluationTasks(prev => [task, ...prev]), [])
  const updateEvaluationTask = useCallback((id: string, patch: Record<string, any>) => {
    setEvaluationTasks(prev => prev.map(task => task.id === id ? { ...task, ...patch } : task))
  }, [])

  const markNotificationRead = useCallback((id: string) => {
    setAppNotifications(prev => prev.map(item => item.id === id ? { ...item, isRead: true } : item))
  }, [])

  const markAllNotificationsRead = useCallback(() => {
    setAppNotifications(prev => prev.map(item => ({ ...item, isRead: true })))
  }, [])

  const resetDemoData = useCallback(() => {
    setBidTasks(mockMode ? clone(initialBidTasks) : [])
    setTaskMaterials(mockMode ? buildInitialMaterials() : {})
    setEvaluationTasks(mockMode ? clone(initialEvaluationTasks) : [])
    setQualifications(mockMode ? clone(initialQualifications) : [])
    setFragments(mockMode ? clone(initialFragments) : [])
    setUsers(mockMode ? clone(initialUsers) : [])
    setAppNotifications(mockMode ? buildInitialNotifications() : [])
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem('bid-platform-evaluation-draft-v2')
    for (const id of ['S01', 'S02', 'S03', 'S04']) localStorage.removeItem(`supplier-portal-draft-${id}`)
  }, [mockMode])

  const value = useMemo<DemoContextValue>(() => ({
    loggedIn,
    authReady,
    currentUser,
    updateCurrentUser: setCurrentUser,
    login,
    logout,
    bidTasks,
    addBidTask,
    updateBidTask,
    getTaskMaterials,
    updateTaskMaterial,
    addTaskMaterial,
    removeTaskMaterial,
    evaluationTasks,
    addEvaluationTask,
    updateEvaluationTask,
    qualifications,
    setQualifications,
    fragments,
    setFragments,
    users,
    setUsers,
    appNotifications,
    markNotificationRead,
    markAllNotificationsRead,
    permissions,
    resetDemoData,
  }), [
    loggedIn, authReady, currentUser, login, logout, bidTasks, addBidTask, updateBidTask,
    getTaskMaterials, updateTaskMaterial, addTaskMaterial, removeTaskMaterial,
    evaluationTasks, addEvaluationTask, updateEvaluationTask, qualifications, fragments,
    users, appNotifications, markNotificationRead, markAllNotificationsRead, permissions,
    resetDemoData,
  ])

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
}

// Provider and hook intentionally share this module to preserve the established import boundary.
// eslint-disable-next-line react-refresh/only-export-components
export function useDemo() {
  const context = useContext(DemoContext)
  if (!context) throw new Error('useDemo must be used inside DemoProvider')
  return context
}
