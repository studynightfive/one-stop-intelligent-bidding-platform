import { useState } from 'react'
import { Table, Tag, Avatar, Button, Input, Segmented, Card, Modal, Select, Tooltip, Form, message, Dropdown, Empty, Drawer, Descriptions, Timeline } from 'antd'
import { UserPlus, Search, ShieldCheck, Users as UsersIcon, UserCheck, MoreHorizontal, Mail, Ban, History, Building2, Send, FolderKanban, KeyRound } from 'lucide-react'
import { roleMap, permissionMatrix } from '../mock/data'
import type { ColumnsType } from 'antd/es/table'
import { useDemo } from '../context/DemoContext'

const statusMap: Record<string, { label: string; color: string; bg: string }> = {
  active: { label: '活跃', color: '#16A34A', bg: '#F0FDF4' },
  inactive: { label: '未激活/停用', color: '#64748B', bg: '#F8FAFC' },
}

export default function UserPermissions() {
  const { users, setUsers } = useDemo()
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [departmentFilter, setDepartmentFilter] = useState<string>('all')
  const [showAddModal, setShowAddModal] = useState(false)
  const [activeTab, setActiveTab] = useState<'users' | 'roles'>('users')
  const [editingUser, setEditingUser] = useState<any>(null)
  const [drawerUser, setDrawerUser] = useState<any>(null)
  const [drawerTab, setDrawerTab] = useState<'projects' | 'activity'>('projects')
  const [form] = Form.useForm()

  const stats = [
    { label: '总用户数', value: users.length, icon: UsersIcon, color: '#2563EB', bg: '#EFF6FF' },
    { label: '活跃用户', value: users.filter(u => u.status === 'active').length, icon: UserCheck, color: '#16A34A', bg: '#F0FDF4' },
    { label: '未激活/停用', value: users.filter(u => u.status === 'inactive').length, icon: Ban, color: '#D97706', bg: '#FFFBEB' },
    { label: '部门数', value: new Set(users.map(u => u.department)).size, icon: Building2, color: '#7C3AED', bg: '#F5F3FF' },
  ]

  const filteredUsers = users.filter(u => {
    const matchSearch = u.name.includes(search) || u.email.includes(search)
    const matchRole = roleFilter === 'all' || u.role === roleFilter
    const matchStatus = statusFilter === 'all' || u.status === statusFilter
    const matchDepartment = departmentFilter === 'all' || u.department === departmentFilter
    return matchSearch && matchRole && matchStatus && matchDepartment
  })
  const departments = Array.from(new Set(users.map(user => user.department)))

  const openUserForm = (user?: any) => {
    setEditingUser(user || null)
    form.setFieldsValue(user || { role: 'member', department: '投标部', status: 'inactive' })
    setShowAddModal(true)
  }

  const saveUser = async () => {
    const values = await form.validateFields()
    if (users.some(item => item.email === values.email && item.id !== editingUser?.id)) {
      message.error('该邮箱已存在，请检查后重试')
      return
    }
    const user = {
      ...editingUser,
      ...values,
      id: editingUser?.id || `U${Date.now()}`,
      avatar: values.name.slice(0, 2).toUpperCase(),
      projects: editingUser?.projects || 0,
      lastLogin: editingUser?.lastLogin || '尚未登录',
      status: editingUser ? values.status : 'inactive',
      invitationStatus: editingUser ? editingUser.invitationStatus || 'accepted' : 'pending',
      invitedAt: editingUser?.invitedAt || new Date().toLocaleString('zh-CN', { hour12: false }),
    }
    setUsers(prev => editingUser ? prev.map(item => item.id === editingUser.id ? user : item) : [user, ...prev])
    setShowAddModal(false)
    setEditingUser(null)
    form.resetFields()
    message.success(editingUser ? '用户信息已更新' : '用户已添加并发送邀请')
  }

  const toggleUserStatus = (record: any) => {
    const nextStatus = record.status === 'active' ? 'inactive' : 'active'
    Modal.confirm({
      title: `${nextStatus === 'active' ? '启用' : '停用'}用户 ${record.name}？`,
      content: nextStatus === 'inactive' ? '停用后该用户将无法继续进入系统，已有项目记录不会删除。' : '启用后该用户可恢复访问其授权范围内的功能。',
      okText: nextStatus === 'active' ? '确认启用' : '确认停用',
      okButtonProps: { danger: nextStatus === 'inactive' },
      onOk: () => {
        setUsers(prev => prev.map(item => item.id === record.id ? { ...item, status: nextStatus } : item))
        message.success(`用户已${nextStatus === 'active' ? '启用' : '停用'}`)
      },
    })
  }

  const openUserDrawer = (record: any, tab: 'projects' | 'activity') => {
    setDrawerUser(record)
    setDrawerTab(tab)
  }

  const resendInvitation = (record: any) => {
    setUsers(previous => previous.map(item => item.id === record.id ? { ...item, invitationStatus: item.invitationStatus || 'accepted', invitationResentAt: new Date().toLocaleString('zh-CN', { hour12: false }) } : item))
    message.success(`邀请邮件已重新发送至 ${record.email}`)
  }

  const columns: ColumnsType<any> = [
    {
      title: '用户',
      dataIndex: 'name',
      key: 'name',
      render: (_, record) => (
        <div className="flex items-center gap-3">
          <Avatar style={{ background: roleMap[record.role].color, fontSize: 13 }}>{record.avatar}</Avatar>
          <div>
            <div className="text-sm font-medium text-[#1E293B]">{record.name}</div>
            <div className="flex items-center gap-1.5 text-xs text-[#94A3B8]">{record.email}{record.invitationStatus === 'pending' && <Tag color="gold" className="!m-0 !text-[10px]">待接受邀请</Tag>}</div>
          </div>
        </div>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => {
        const r = roleMap[role]
        return (
          <Tag style={{ color: r.color, background: r.bg, border: 'none' }} className="!text-xs !font-medium">
            {r.label}
          </Tag>
        )
      },
    },
    {
      title: '部门',
      dataIndex: 'department',
      key: 'department',
      render: (dept: string) => <span className="text-sm text-[#475569]">{dept}</span>,
    },
    {
      title: '参与项目',
      dataIndex: 'projects',
      key: 'projects',
      render: (count: number, record) => (
        <button type="button" onClick={() => openUserDrawer(record, 'projects')} className="flex items-center gap-1.5 hover:text-[#2563EB]" aria-label={`查看 ${record.name} 参与的项目`}>
          <span className="text-sm font-medium text-[#1E293B]">{count}</span>
          <span className="text-xs text-[#94A3B8]">个</span>
        </button>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const s = statusMap[status]
        return (
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full" style={{ background: s.color }} />
            <span className="text-xs" style={{ color: s.color }}>{s.label}</span>
          </div>
        )
      },
    },
    {
      title: '最后登录',
      dataIndex: 'lastLogin',
      key: 'lastLogin',
      render: (time: string) => <span className="text-xs text-[#94A3B8]">{time}</span>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <div className="flex items-center gap-1">
          <Button onClick={() => openUserForm(record)} type="text" size="small" className="!text-xs !text-[#2563EB]">编辑</Button>
          <Dropdown
            trigger={['click']}
            menu={{ items: [
              { key: 'resend', label: '重发邀请邮件', icon: <Send size={14} /> },
              { key: 'reset', label: '发送密码重置邮件', icon: <Mail size={14} /> },
              { key: 'status', label: record.status === 'active' ? '停用用户' : '启用用户', icon: <Ban size={14} />, danger: record.status === 'active' },
              { key: 'logs', label: '查看活动记录', icon: <History size={14} /> },
            ], onClick: ({ key }) => {
              if (key === 'resend') resendInvitation(record)
              if (key === 'reset') Modal.confirm({ title: `向 ${record.name} 发送密码重置邮件？`, content: `重置链接将发送至 ${record.email}，不会在页面生成或展示临时密码。`, okText: '发送邮件', onOk: () => message.success('密码重置邮件已发送（Demo）') })
              if (key === 'status') toggleUserStatus(record)
              if (key === 'logs') openUserDrawer(record, 'activity')
            } }}
          >
            <Button type="text" size="small" icon={<MoreHorizontal size={16} />} aria-label="更多用户操作" />
          </Dropdown>
        </div>
      ),
    },
  ]

  return (
    <main className="p-4 sm:p-6" data-testid="user-permissions-page">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[#1E293B]">用户与权限</h1>
        <p className="mt-1 text-sm text-[#64748B]">邀请成员、管理账号状态，并查看项目与活动审计记录</p>
      </div>
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {stats.map(stat => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} className="!border-[#E2E8F0] !shadow-none">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-[#64748B] mb-1">{stat.label}</div>
                  <div className="text-2xl font-semibold text-[#1E293B]">{stat.value}</div>
                </div>
                <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: stat.bg }}>
                  <Icon size={20} color={stat.color} />
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* Tab switch */}
      <div className="mb-4">
        <Segmented
          value={activeTab}
          onChange={(v) => setActiveTab(v as 'users' | 'roles')}
          options={[
            { label: '用户列表', value: 'users' },
            { label: '角色权限', value: 'roles' },
          ]}
        />
      </div>

      {activeTab === 'users' ? (
        <>
          {/* Toolbar */}
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 mb-4">
            <div className="flex items-center gap-3 flex-wrap">
              <Input
                allowClear
                prefix={<Search size={16} className="text-[#94A3B8]" />}
                placeholder="搜索用户名或邮箱"
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{ width: 260 }}
                className="!rounded-lg"
              />
              <Select
                value={roleFilter}
                onChange={setRoleFilter}
                style={{ width: 140 }}
                options={[
                  { value: 'all', label: '全部角色' },
                  { value: 'admin', label: '管理员' },
                  { value: 'project_lead', label: '项目负责人' },
                  { value: 'member', label: '成员' },
                  { value: 'reviewer', label: '审核人' },
                ]}
              />
              <Select
                value={departmentFilter}
                onChange={setDepartmentFilter}
                style={{ width: 140 }}
                options={[{ value: 'all', label: '全部部门' }, ...departments.map(department => ({ value: department, label: department }))]}
              />
              <Select
                value={statusFilter}
                onChange={setStatusFilter}
                style={{ width: 140 }}
                options={[{ value: 'all', label: '全部状态' }, { value: 'active', label: '活跃' }, { value: 'inactive', label: '未激活/停用' }]}
              />
              <Button onClick={() => { setSearch(''); setRoleFilter('all'); setDepartmentFilter('all'); setStatusFilter('all') }}>重置</Button>
            </div>
            <Button
              type="primary"
              icon={<UserPlus size={16} />}
              onClick={() => openUserForm()}
              className="!flex !items-center"
            >
              邀请用户
            </Button>
          </div>

          {/* Table */}
          <Card className="!border-[#E2E8F0] !shadow-none overflow-x-auto" styles={{ body: { padding: 0 } }}>
            <Table
              columns={columns}
              dataSource={filteredUsers}
              rowKey="id"
              pagination={{ pageSize: 8, showSizeChanger: false }}
              locale={{ emptyText: <Empty description="当前筛选条件下没有用户" /> }}
              className="!text-sm"
            />
          </Card>
        </>
      ) : (
        /* Role permission matrix */
        <Card className="!border-[#E2E8F0] !shadow-none">
          <div className="mb-4">
            <h3 className="text-base font-semibold text-[#1E293B] mb-1">角色权限矩阵</h3>
            <p className="text-xs text-[#64748B]">系统采用 RBAC 模型，共 4 个角色，权限按模块划分</p>
          </div>

          {/* Role cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 mb-6">
            {Object.entries(roleMap).map(([key, role]) => (
              <div key={key} className="rounded-xl border border-[#E2E8F0] p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{ background: role.bg }}>
                    <ShieldCheck size={15} color={role.color} />
                  </div>
                  <Tag style={{ color: role.color, background: role.bg, border: 'none' }} className="!text-xs !font-medium">
                    {role.label}
                  </Tag>
                </div>
                <div className="text-xs text-[#64748B]">
                  {key === 'admin' && '系统全局管理，拥有所有权限'}
                  {key === 'project_lead' && '创建管理投标任务，协调团队成员'}
                  {key === 'member' && '上传材料和下载文档，参与协作'}
                  {key === 'reviewer' && '审核投标文件质量，把控风险'}
                </div>
                <div className="mt-2 text-xs font-medium" style={{ color: role.color }}>
                  {users.filter(u => u.role === key).length} 人
                </div>
              </div>
            ))}
          </div>

          {/* Permission table */}
          <Table
            dataSource={permissionMatrix}
            rowKey="module"
            pagination={false}
            size="middle"
            columns={[
              {
                title: '功能模块',
                dataIndex: 'module',
                key: 'module',
                render: (m: string) => <span className="text-sm font-medium text-[#1E293B]">{m}</span>,
              },
              {
                title: '管理员',
                render: (_, record) => <PermissionCell text={record.actions.admin} role="admin" />,
              },
              {
                title: '项目负责人',
                render: (_, record) => <PermissionCell text={record.actions.project_lead} role="project_lead" />,
              },
              {
                title: '成员',
                render: (_, record) => <PermissionCell text={record.actions.member} role="member" />,
              },
              {
                title: '审核人',
                render: (_, record) => <PermissionCell text={record.actions.reviewer} role="reviewer" />,
              },
            ]}
          />
        </Card>
      )}

      {/* Add user modal */}
      <Modal
        title={editingUser ? '编辑用户' : '邀请用户'}
        open={showAddModal}
        onCancel={() => { setShowAddModal(false); setEditingUser(null); form.resetFields() }}
        onOk={saveUser}
        okText={editingUser ? '保存' : '发送邀请'}
        cancelText="取消"
      >
        <Form form={form} layout="vertical" className="py-4">
          <Form.Item name="name" label="姓名" rules={[{ required: true, message: '请输入用户姓名' }]}><Input placeholder="请输入用户姓名" /></Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email', message: '请输入有效邮箱地址' }]}><Input placeholder="请输入邮箱地址" /></Form.Item>
          <Form.Item name="phone" label="联系电话" rules={[{ pattern: /^1\d{10}$|^1\d{2}\*{4}\d{4}$/, message: '请输入有效手机号' }]}><Input placeholder="请输入手机号" /></Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}><Select
              className="w-full"
              placeholder="请选择角色"
              options={Object.entries(roleMap).map(([key, val]) => ({
                value: key,
                label: val.label,
              }))}
            /></Form.Item>
          <Form.Item name="department" label="部门" rules={[{ required: true }]}><Input placeholder="请输入所属部门" /></Form.Item>
          {editingUser
            ? <Form.Item name="status" label="状态"><Select options={[{ value: 'active', label: '活跃' }, { value: 'inactive', label: '未激活/停用' }]} /></Form.Item>
            : <div className="rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] p-3 text-xs leading-5 text-[#1D4ED8]">邀请发送后账号处于“待接受邀请 / 未激活”状态，成员完成邀请流程后再启用。</div>}
        </Form>
      </Modal>

      <Drawer title={drawerUser ? `${drawerUser.name} · 用户详情` : '用户详情'} open={Boolean(drawerUser)} onClose={() => setDrawerUser(null)} width={620}>
        {drawerUser && (
          <div>
            <Descriptions bordered size="small" column={2} className="mb-5">
              <Descriptions.Item label="邮箱" span={2}>{drawerUser.email}</Descriptions.Item>
              <Descriptions.Item label="部门">{drawerUser.department}</Descriptions.Item>
              <Descriptions.Item label="角色">{roleMap[drawerUser.role]?.label}</Descriptions.Item>
              <Descriptions.Item label="状态">{statusMap[drawerUser.status]?.label}</Descriptions.Item>
              <Descriptions.Item label="最后登录">{drawerUser.lastLogin}</Descriptions.Item>
            </Descriptions>
            <Segmented
              block
              value={drawerTab}
              onChange={value => setDrawerTab(value as 'projects' | 'activity')}
              options={[{ value: 'projects', label: '参与项目', icon: <FolderKanban size={13} /> }, { value: 'activity', label: '活动记录', icon: <History size={13} /> }]}
              className="mb-5"
            />
            {drawerTab === 'projects' ? (
              drawerUser.projects ? <div className="space-y-3">{[
                ['2026年深圳市政务云平台采购项目', '投标任务', '项目负责人'],
                ['智慧城市数据中台建设项目', '投标任务', '协作成员'],
                ['华南数字化转型服务评标', '评标任务', '评审人'],
              ].slice(0, Math.min(drawerUser.projects, 3)).map(([name, type, role]) => <div key={name} className="rounded-xl border border-[#E2E8F0] p-4"><div className="font-medium text-[#1E293B]">{name}</div><div className="mt-2 flex gap-2"><Tag>{type}</Tag><Tag color="blue">{role}</Tag></div></div>)}</div> : <Empty description="当前未参与任何项目" />
            ) : (
              <Timeline items={[
                { color: 'blue', children: `${drawerUser.lastLogin} · 登录系统` },
                { color: 'green', children: '2026-08-03 16:20 · 查看项目材料' },
                { color: 'gray', children: '2026-08-02 10:08 · 更新个人资料' },
                { color: 'gray', children: `${drawerUser.invitedAt || '2026-08-01 09:00'} · 账号邀请已创建` },
              ]} />
            )}
            <div className="mt-5 flex gap-2">
              <Button icon={<Send size={14} />} onClick={() => resendInvitation(drawerUser)}>重发邀请</Button>
              <Button icon={<KeyRound size={14} />} onClick={() => message.success('密码重置邮件已发送')}>发送密码重置邮件</Button>
            </div>
          </div>
        )}
      </Drawer>
    </main>
  )
}

function PermissionCell({ text, role }: { text: string; role: string }) {
  const color = roleMap[role].color
  const bg = roleMap[role].bg
  const isNone = text === '无'

  if (isNone) {
    return <span className="text-xs text-[#CBD5E1]">--</span>
  }

  return (
    <Tooltip title={text}>
      <Tag style={{ color: isNone ? '#94A3B8' : color, background: isNone ? '#F8FAFC' : bg, border: 'none' }} className="!text-xs">
        {text}
      </Tag>
    </Tooltip>
  )
}
