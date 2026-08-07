import type { ReactNode } from 'react'

export function PermissionGate({
  permissions,
  require,
  fallback = null,
  children,
}: {
  permissions: string[]
  require: string | string[]
  fallback?: ReactNode
  children: ReactNode
}) {
  const required = Array.isArray(require) ? require : [require]
  const allowed = required.every(permission => permissions.includes(permission) || permissions.includes('*'))
  return allowed ? children : fallback
}
