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

type DemoContextValue = {
  loggedIn: boolean
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
  const stored = typeof window === 'undefined' ? null : readStoredState()
  const mockMode = shouldUseMocks()
  const [loggedIn, setLoggedIn] = useState(() => (
    mockMode ? sessionStorage.getItem('bid-demo-logged-in') === 'true' : Boolean(readAccessToken())
  ))
  const [permissions, setPermissions] = useState<string[]>(DEMO_PERMISSIONS)
  const [bidTasks, setBidTasks] = useState<any[]>(stored?.bidTasks || clone(initialBidTasks))
  const [taskMaterials, setTaskMaterials] = useState<Record<string, any[]>>(stored?.taskMaterials || buildInitialMaterials())
  const [evaluationTasks, setEvaluationTasks] = useState<any[]>(stored?.evaluationTasks || clone(initialEvaluationTasks))
  const [qualifications, setQualifications] = useState<any[]>(stored?.qualifications || clone(initialQualifications))
  const [fragments, setFragments] = useState<any[]>(stored?.fragments || clone(initialFragments))
  const [users, setUsers] = useState<any[]>(stored?.users || clone(initialUsers))
  const [appNotifications, setAppNotifications] = useState<any[]>(stored?.appNotifications || buildInitialNotifications())

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      bidTasks,
      taskMaterials,
      evaluationTasks,
      qualifications,
      fragments,
      users,
      appNotifications,
    }))
  }, [bidTasks, taskMaterials, evaluationTasks, qualifications, fragments, users, appNotifications])

  const login = useCallback(async (values?: LoginValues) => {
    if (!mockMode) {
      if (!values) throw new Error('璇疯緭鍏ョ櫥褰曞嚟璇?')
      const session = await loginSession(values)
      setPermissions(session.permissions)
    }
    sessionStorage.setItem('bid-demo-logged-in', 'true')
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
    sessionStorage.removeItem('bid-demo-logged-in')
    setLoggedIn(false)
  }, [mockMode])

  const addBidTask = (task: any, materials = clone(initialMaterials)) => {
    setBidTasks(prev => [task, ...prev])
    setTaskMaterials(prev => ({ ...prev, [task.id]: clone(materials) }))
  }

  const updateBidTask = (id: string, patch: Record<string, any>) => {
    setBidTasks(prev => prev.map(task => task.id === id ? { ...task, ...patch } : task))
  }

  const getTaskMaterials = useCallback((id?: string) => {
    if (!id) return clone(initialMaterials)
    return taskMaterials[id] || clone(initialMaterials)
  }, [taskMaterials])

  const updateTaskMaterial = (taskId: string, materialId: string, patch: Record<string, any>) => {
    setTaskMaterials(prev => ({
      ...prev,
      [taskId]: (prev[taskId] || clone(initialMaterials)).map(item => item.id === materialId ? { ...item, ...patch } : item),
    }))
  }

  const addTaskMaterial = (taskId: string, material: any) => {
    setTaskMaterials(prev => ({
      ...prev,
      [taskId]: [...(prev[taskId] || clone(initialMaterials)), material],
    }))
  }

  const removeTaskMaterial = (taskId: string, materialId: string) => {
    setTaskMaterials(prev => ({
      ...prev,
      [taskId]: (prev[taskId] || clone(initialMaterials)).filter(item => item.id !== materialId),
    }))
  }

  const addEvaluationTask = (task: any) => setEvaluationTasks(prev => [task, ...prev])
  const updateEvaluationTask = (id: string, patch: Record<string, any>) => {
    setEvaluationTasks(prev => prev.map(task => task.id === id ? { ...task, ...patch } : task))
  }

  const markNotificationRead = (id: string) => {
    setAppNotifications(prev => prev.map(item => item.id === id ? { ...item, isRead: true } : item))
  }

  const markAllNotificationsRead = () => {
    setAppNotifications(prev => prev.map(item => ({ ...item, isRead: true })))
  }

  const resetDemoData = () => {
    setBidTasks(clone(initialBidTasks))
    setTaskMaterials(buildInitialMaterials())
    setEvaluationTasks(clone(initialEvaluationTasks))
    setQualifications(clone(initialQualifications))
    setFragments(clone(initialFragments))
    setUsers(clone(initialUsers))
    setAppNotifications(buildInitialNotifications())
    localStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem('bid-platform-evaluation-draft-v2')
    for (const id of ['S01', 'S02', 'S03', 'S04']) localStorage.removeItem(`supplier-portal-draft-${id}`)
  }

  const value = useMemo<DemoContextValue>(() => ({
    loggedIn,
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
  }), [loggedIn, login, logout, bidTasks, evaluationTasks, qualifications, fragments, users, appNotifications, getTaskMaterials, permissions])

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
}

// Provider and hook intentionally share this module to preserve the established import boundary.
// eslint-disable-next-line react-refresh/only-export-components
export function useDemo() {
  const context = useContext(DemoContext)
  if (!context) throw new Error('useDemo must be used inside DemoProvider')
  return context
}
