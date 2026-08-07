import type { RouteObject } from 'react-router-dom'
import QualificationLibrary from '../../pages/QualificationLibrary'
import FragmentLibrary from '../../pages/FragmentLibrary'
import UserPermissions from '../../pages/UserPermissions'
import SystemSettings from '../../pages/SystemSettings'

export const adminRoutes: RouteObject[] = [
  { path: 'admin/qualifications', element: <QualificationLibrary /> },
  { path: 'admin/fragments', element: <FragmentLibrary /> },
  { path: 'admin/users', element: <UserPermissions /> },
  { path: 'admin/settings', element: <SystemSettings /> },
]

export default adminRoutes
