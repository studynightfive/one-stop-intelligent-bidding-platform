import { ClipboardCheck, FileStack, Settings, Users } from 'lucide-react'

export const adminNavigation = [
  { key: '/admin/qualifications', label: '资质库管理', icon: ClipboardCheck, section: 'main' as const, owner: 'M3' as const },
  { key: '/admin/fragments', label: '文档片段库', icon: FileStack, section: 'main' as const, owner: 'M3' as const },
  { key: '/admin/users', label: '用户与权限', icon: Users, section: 'admin' as const, owner: 'M3' as const },
  { key: '/admin/settings', label: '系统设置', icon: Settings, section: 'admin' as const, owner: 'M3' as const },
]

export default adminNavigation
