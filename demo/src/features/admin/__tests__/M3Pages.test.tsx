import { beforeEach, describe, expect, it } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import './testEnvironment'
import { MemoryRouter } from 'react-router-dom'
import Login from '../../../pages/Login'
import QualificationLibrary from '../../../pages/QualificationLibrary'
import FragmentLibrary from '../../../pages/FragmentLibrary'
import UserPermissions from '../../../pages/UserPermissions'
import SystemSettings from '../../../pages/SystemSettings'
import { ForbiddenPage, NotFoundPage, ServerErrorPage } from '../../../components/common'
import { DemoProvider } from '../../../context/DemoContext'

function renderWithDemo(node: React.ReactNode) {
  return render(<MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><DemoProvider>{node}</DemoProvider></MemoryRouter>)
}

describe('M3 page smoke and accessibility', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  it('provides labelled login controls and password recovery', () => {
    render(<Login onLogin={() => undefined} />)
    expect(screen.getByLabelText('邮箱')).toBeTruthy()
    expect(screen.getByLabelText('密码')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '忘记密码？' }))
    expect(screen.getByRole('dialog', { name: '找回密码' })).toBeTruthy()
  })

  it('renders dynamic qualification management controls', () => {
    renderWithDemo(<QualificationLibrary />)
    expect(screen.getByRole('heading', { name: '资质库管理' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '添加资质' }))
    expect(screen.getByRole('button', { name: /选择文件/ })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /取\s*消/ }))
    expect(screen.getAllByTestId('qualification-row').length).toBeGreaterThan(0)
  })

  it('switches the fragment library to semantic search', () => {
    renderWithDemo(<FragmentLibrary />)
    fireEvent.click(screen.getByText('AI 语义检索'))
    const input = screen.getByPlaceholderText(/描述需要生成的内容/)
    fireEvent.change(input, { target: { value: '政务云安全方案' } })
    expect(screen.getAllByTestId('fragment-card').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/推荐理由/).length).toBeGreaterThan(0)
  })

  it('exposes invitation and RBAC entry points', () => {
    renderWithDemo(<UserPermissions />)
    expect(screen.getByRole('heading', { name: '用户与权限' })).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '邀请用户' }))
    expect(screen.getByText(/待接受邀请/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /取\s*消/ }))
    fireEvent.click(screen.getByText('角色权限'))
    expect(screen.getByText('角色权限矩阵')).toBeTruthy()
  })

  it('tracks unsaved system settings before saving', () => {
    renderWithDemo(<SystemSettings />)
    expect(screen.getByRole('heading', { name: '系统设置' })).toBeTruthy()
    fireEvent.click(screen.getByText('部署与存储'))
    fireEvent.click(screen.getByText('私有化部署'))
    expect(screen.getByText('存在未保存配置')).toBeTruthy()
    expect((screen.getByRole('button', { name: /保存配置/ }) as HTMLButtonElement).disabled).toBe(false)
  })

  it('provides recoverable global error pages', () => {
    const routerFuture = { v7_startTransition: true, v7_relativeSplatPath: true } as const
    const forbidden = render(<MemoryRouter future={routerFuture}><ForbiddenPage /></MemoryRouter>)
    expect(screen.getByText('没有访问权限')).toBeTruthy()
    forbidden.unmount()

    const notFound = render(<MemoryRouter future={routerFuture}><NotFoundPage /></MemoryRouter>)
    expect(screen.getByText('页面不存在')).toBeTruthy()
    expect(screen.getByRole('button', { name: '返回工作台' })).toBeTruthy()
    notFound.unmount()

    render(<MemoryRouter future={routerFuture}><ServerErrorPage /></MemoryRouter>)
    expect(screen.getByText('服务暂时不可用')).toBeTruthy()
    expect(screen.getByRole('button', { name: '重新加载' })).toBeTruthy()
  })
})
