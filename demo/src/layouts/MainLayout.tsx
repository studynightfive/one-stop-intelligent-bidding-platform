import { useEffect, useMemo, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { Avatar, Badge, Button, Dropdown, Input, Layout, Modal, Segmented, Tooltip, message } from 'antd'
import {
  Bell, CheckCircle2, CheckSquare, ChevronRight,
  Menu, PenLine, Search, Zap,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { currentUser } from '../mock/data'
import { useDemo } from '../context/DemoContext'
import { bidNavigation } from '../features/bids/navigation'
import { adminNavigation } from '../features/admin/navigation'
import { evaluationNavigation } from '../features/admin/evaluationBridge'

const { Sider, Header, Content } = Layout

type Mode = 'bid' | 'evaluation'

const bidNavItems = [...bidNavigation.filter(item => !item.hiddenInSidebar), ...adminNavigation]
const evalNavItems = [...evaluationNavigation, ...adminNavigation.filter(item => item.section === 'admin')]

export default function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const {
    logout,
    bidTasks,
    evaluationTasks,
    resetDemoData,
    appNotifications,
    markNotificationRead,
    markAllNotificationsRead,
  } = useDemo()
  const [collapsed, setCollapsed] = useState(false)
  const [mobile, setMobile] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [search, setSearch] = useState('')

  const mode: Mode = location.pathname.startsWith('/evaluation') ? 'evaluation' : 'bid'
  const navItems = mode === 'bid' ? bidNavItems : evalNavItems
  const mainNav = navItems.filter(item => item.section === 'main')
  const adminNav = navItems.filter(item => item.section === 'admin')
  const isEvaluationWorkPath = location.pathname === '/evaluation' || /^\/evaluation\/(?!create|portal)[^/]+$/.test(location.pathname)

  const currentNav = [...mainNav, ...adminNav].find(item => {
    if (item.key === '/evaluation/create') return location.pathname === item.key
    if (item.key.startsWith('/evaluation/portal')) return location.pathname.startsWith('/evaluation/portal')
    if (item.key === '/evaluation') return isEvaluationWorkPath
    if (item.key === '/dashboard') return location.pathname === '/dashboard' || location.pathname.startsWith('/tasks')
    return location.pathname.startsWith(item.key)
  })

  const unreadCount = appNotifications.filter(item => !item.isRead).length

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setSearchOpen(true)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const searchResults = useMemo(() => {
    const keyword = search.trim().toLowerCase()
    if (!keyword) return []
    const pages = [...bidNavItems, ...evalNavItems].map(item => ({ title: item.label, subtitle: '功能页面', path: item.key }))
    const bids = bidTasks.map(task => ({ title: task.projectName, subtitle: task.tenderNo, path: `/tasks/${task.id}` }))
    const evaluations = evaluationTasks.map(task => ({ title: task.projectName, subtitle: task.tenderNo, path: `/evaluation/${task.id}` }))
    return [...pages, ...bids, ...evaluations]
      .filter(item => `${item.title} ${item.subtitle}`.toLowerCase().includes(keyword))
      .filter((item, index, items) => items.findIndex(candidate => candidate.path === item.path) === index)
      .slice(0, 8)
  }, [search, bidTasks, evaluationTasks])

  const goTo = (path: string) => {
    navigate(path)
    setSearchOpen(false)
    setSearch('')
    if (mobile) setCollapsed(true)
  }

  const handleModeChange = (value: string) => goTo(value === 'bid' ? '/dashboard' : '/evaluation')

  const userMenu = {
    items: [
      { key: 'profile', label: '个人资料' },
      { key: 'settings', label: '账号设置' },
      { key: 'reset', label: '重置演示数据' },
      { type: 'divider' as const },
      { key: 'logout', label: '退出登录', danger: true },
    ],
    onClick: ({ key }: { key: string }) => {
      if (key === 'logout') {
        void logout()
        message.success('已退出演示账号')
      } else if (key === 'settings') {
        goTo('/admin/settings')
      } else if (key === 'reset') {
        Modal.confirm({
          title: '重置演示数据？',
          content: '将清除本浏览器中新增的任务、资质、片段和用户，恢复初始演示状态。',
          okText: '确认重置',
          okButtonProps: { danger: true },
          onOk: () => {
            resetDemoData()
            goTo('/dashboard')
            message.success('演示数据已恢复初始状态')
          },
        })
      } else {
        message.info('Demo 当前使用项目负责人示例账号')
      }
    },
  }

  const notificationMenu = {
    onClick: ({ key }: { key: string }) => {
      if (key === 'mark-all') markAllNotificationsRead()
      else markNotificationRead(key)
    },
    items: [
      ...appNotifications.slice(0, 6).map(item => ({
        key: item.id,
        label: (
          <div className="py-1 max-w-xs">
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className={`w-1.5 h-1.5 rounded-full ${item.isRead ? 'bg-[#CBD5E1]' : 'bg-[#DC2626]'}`} />
              <span className="text-xs font-medium text-[#1E293B]">{item.title}</span>
              <span className={`text-xs px-1 rounded ${item.source === 'eval' ? 'bg-[#F5F3FF] text-[#7C3AED]' : 'bg-[#EFF6FF] text-[#2563EB]'}`}>
                {item.source === 'eval' ? '评标' : '投标'}
              </span>
            </div>
            <div className="text-xs text-[#64748B]">{item.content}</div>
            <div className="text-xs text-[#94A3B8] mt-0.5">{item.time}</div>
          </div>
        ),
      })),
      { type: 'divider' as const },
      { key: 'mark-all', label: <span className="text-xs text-[#2563EB] flex items-center gap-1"><CheckCircle2 size={12} />全部标为已读</span> },
    ],
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={220}
        collapsedWidth={mobile ? 0 : 64}
        collapsed={collapsed}
        onCollapse={setCollapsed}
        breakpoint="lg"
        onBreakpoint={broken => {
          setMobile(broken)
          setCollapsed(broken)
        }}
        style={{
          background: '#fff',
          borderRight: '1px solid #E2E8F0',
          ...(mobile ? { position: 'fixed', height: '100vh', zIndex: 30, left: 0, top: 0 } : {}),
        }}
        trigger={null}
      >
        <div className="flex items-center gap-2.5 h-14 px-4 border-b border-[#E2E8F0]">
          <div className="w-8 h-8 rounded-lg bg-[#2563EB] flex items-center justify-center flex-shrink-0">
            <Zap size={18} color="#fff" />
          </div>
          {!collapsed && <span className="text-[15px] font-semibold text-[#1E293B] whitespace-nowrap">一站式智能招投标平台</span>}
        </div>

        {!collapsed && (
          <div className="px-3 pt-3 pb-1">
            <Segmented
              block
              value={mode}
              onChange={handleModeChange}
              options={[
                { label: <span className="flex items-center gap-1.5 text-xs"><PenLine size={13} />投标中心</span>, value: 'bid' },
                { label: <span className="flex items-center gap-1.5 text-xs"><CheckSquare size={13} />评标中心</span>, value: 'evaluation' },
              ]}
            />
          </div>
        )}

        <nav className="py-2" aria-label="主导航">
          {mainNav.map(item => (
            <NavButton
              key={item.key}
              icon={item.icon}
              label={item.label}
              active={currentNav?.key === item.key}
              collapsed={collapsed}
              onClick={() => goTo(item.key)}
            />
          ))}
          {adminNav.length > 0 && !collapsed && <div className="px-6 pt-4 pb-1 text-xs text-[#94A3B8] font-medium">管理后台</div>}
          {adminNav.map(item => (
            <NavButton
              key={item.key}
              icon={item.icon}
              label={item.label}
              active={currentNav?.key === item.key}
              collapsed={collapsed}
              onClick={() => goTo(item.key)}
            />
          ))}
        </nav>

        {!collapsed && (
          <div className="absolute bottom-4 left-3 right-3 bg-[#FFFBEB] border border-[#FDE68A] rounded-lg p-3 text-xs text-[#92400E]">
            <div className="font-medium mb-0.5">Demo 演示模式</div>
            <div className="text-[#D97706]">操作会保存在当前浏览器</div>
          </div>
        )}
      </Sider>

      {mobile && !collapsed && (
        <button
          type="button"
          aria-label="关闭导航遮罩"
          className="fixed inset-0 z-20 bg-slate-950/30 lg:hidden"
          onClick={() => setCollapsed(true)}
        />
      )}

      <Layout>
        <Header
          style={{
            background: '#fff', borderBottom: '1px solid #E2E8F0', padding: mobile ? '0 12px' : '0 24px',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between', height: 56,
          }}
        >
          <div className="flex items-center gap-1.5 text-sm text-[#64748B] min-w-0">
            <Button type="text" size="small" icon={<Menu size={18} />} aria-label="展开或收起导航" onClick={() => setCollapsed(value => !value)} />
            <span className="hidden xl:inline">一站式智能招投标平台</span>
            <ChevronRight size={14} className="hidden xl:block" />
            <span className="text-[#1E293B] font-medium">{mode === 'bid' ? '投标中心' : '评标中心'}</span>
            <ChevronRight size={14} />
            <span className="text-[#1E293B] font-medium truncate">{currentNav?.label || '任务详情'}</span>
            <span className="hidden sm:inline-flex rounded-full bg-[#FFFBEB] px-2 py-0.5 text-xs font-medium text-[#92400E] border border-[#FDE68A]">演示环境</span>
          </div>

          <div className="flex items-center gap-2 md:gap-4">
            <Tooltip title="搜索 (Ctrl+K)">
              <Button type="text" size="small" aria-label="全局搜索" icon={<Search size={18} />} onClick={() => setSearchOpen(true)} />
            </Tooltip>
            <Dropdown trigger={['click']} menu={notificationMenu}>
              <Badge count={unreadCount} size="small" color="#DC2626">
                <Button type="text" size="small" aria-label="通知" icon={<Bell size={18} />} />
              </Badge>
            </Dropdown>
            <Dropdown menu={userMenu} trigger={['click']}>
              <button type="button" className="flex items-center gap-2 cursor-pointer">
                <Avatar size={28} style={{ background: '#2563EB', fontSize: 12 }}>{currentUser.avatar}</Avatar>
                <span className="hidden md:block text-left">
                  <span className="block text-xs font-medium text-[#1E293B] leading-tight">{currentUser.name}</span>
                  <span className="block text-xs text-[#64748B] leading-tight">{currentUser.role}</span>
                </span>
              </button>
            </Dropdown>
          </div>
        </Header>

        <Content style={{ background: '#F8FAFC', overflow: 'auto' }}><Outlet /></Content>
      </Layout>

      <Modal title="全局搜索" open={searchOpen} onCancel={() => setSearchOpen(false)} footer={null} width={620}>
        <Input
          autoFocus
          size="large"
          prefix={<Search size={16} className="text-[#94A3B8]" />}
          placeholder="搜索页面、投标任务或评标任务"
          value={search}
          onChange={event => setSearch(event.target.value)}
        />
        <div className="mt-3 max-h-[360px] overflow-y-auto">
          {!search && <div className="py-8 text-center text-sm text-[#94A3B8]">输入关键词开始搜索</div>}
          {search && searchResults.length === 0 && <div className="py-8 text-center text-sm text-[#94A3B8]">未找到匹配结果</div>}
          {searchResults.map(result => (
            <button
              key={result.path}
              type="button"
              onClick={() => goTo(result.path)}
              className="w-full text-left px-3 py-2.5 rounded-lg hover:bg-[#F8FAFC] flex items-center justify-between"
            >
              <span>
                <span className="block text-sm font-medium text-[#1E293B]">{result.title}</span>
                <span className="block text-xs text-[#94A3B8] mt-0.5">{result.subtitle}</span>
              </span>
              <ChevronRight size={14} className="text-[#CBD5E1]" />
            </button>
          ))}
        </div>
      </Modal>
    </Layout>
  )
}

function NavButton({ icon: Icon, label, active, collapsed, onClick }: {
  icon: LucideIcon
  label: string
  active: boolean
  collapsed: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={collapsed ? label : undefined}
      aria-current={active ? 'page' : undefined}
      className={`flex items-center gap-3 mx-3 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors mb-0.5 ${
        active ? 'bg-[#EFF6FF] text-[#2563EB] font-medium' : 'text-[#64748B] hover:bg-[#F8FAFC] hover:text-[#1E293B]'
      }`}
      style={{ width: 'calc(100% - 24px)' }}
    >
      <Icon size={18} className="flex-shrink-0" />
      {!collapsed && <span>{label}</span>}
    </button>
  )
}
