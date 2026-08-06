import { useState } from 'react'
import { Table, Tag, Avatar, Segmented, Card, Progress, Button, Input, Select, Empty, Modal, Tooltip } from 'antd'
import { AlertTriangle, Gavel, Bot, Plus, Link2, Clock, Search, RotateCcw } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import dayjs from 'dayjs'
import { evalStatusMap } from '../mock/evaluationData'
import type { ColumnsType } from 'antd/es/table'
import { useDemo } from '../context/DemoContext'

const filterTabs = [
  { label: '全部', value: 'all' },
  { label: '材料收集中', value: 'collecting' },
  { label: 'AI初审中', value: 'ai_review' },
  { label: '人工复审', value: 'human_review' },
  { label: '已完成', value: 'completed' },
  { label: '已关闭', value: 'closed' },
]

export default function EvaluationDashboard() {
  const navigate = useNavigate()
  const { evaluationTasks } = useDemo()
  const [filter, setFilter] = useState('all')
  const [viewMode, setViewMode] = useState<'table' | 'board'>('table')
  const [keyword, setKeyword] = useState('')
  const [assignee, setAssignee] = useState('all')

  const filteredTasks = evaluationTasks.filter(task => {
    const normalized = keyword.trim().toLowerCase()
    return (filter === 'all' || task.status === filter)
      && (assignee === 'all' || task.assignee === assignee)
      && (!normalized || [task.projectName, task.tenderNo, task.tenderEntity].some(value => String(value).toLowerCase().includes(normalized)))
  })
  const stats = [
    { label: '评标任务总数', value: evaluationTasks.length, icon: Gavel, color: '#2563EB', bg: '#EFF6FF', filter: 'all' },
    { label: '材料收集中', value: evaluationTasks.filter(t => t.status === 'collecting').length, icon: Clock, color: '#0891B2', bg: '#ECFEFF', filter: 'collecting' },
    { label: 'AI初审中', value: evaluationTasks.filter(t => t.status === 'ai_review').length, icon: Bot, color: '#7C3AED', bg: '#F5F3FF', filter: 'ai_review' },
    { label: '废标预警', value: 1, icon: AlertTriangle, color: '#DC2626', bg: '#FEF2F2', filter: 'risk' },
  ]

  const assignees = Array.from(new Set(evaluationTasks.map(task => task.assignee)))
  const deadlineDays = (date: string) => dayjs(date).startOf('day').diff(dayjs().startOf('day'), 'day')
  const relativeDeadline = (record: any) => {
    if (record.status === 'completed' || record.status === 'closed') return evalStatusMap[record.status].label
    const days = deadlineDays(record.deadline)
    if (days < 0) return `已逾期 ${Math.abs(days)} 天`
    if (days === 0) return '今天截止'
    return `剩余 ${days} 天`
  }
  const formatBudget = (budget: string) => {
    const value = Number(String(budget).replace(/,/g, ''))
    return value >= 10000 ? `¥${(value / 10000).toLocaleString('zh-CN', { maximumFractionDigits: 2 })} 万` : `¥${budget}`
  }
  const showRisk = () => Modal.warning({
    title: '废标风险下钻',
    width: 620,
    okText: '前往人工复核',
    onOk: () => navigate('/evaluation/EVAL-2026-001'),
    content: (
      <div className="mt-3 space-y-2">
        <div className="rounded-lg bg-[#FEF2F2] border border-[#FECACA] p-3"><div className="font-medium text-[#991B1B]">北京华信科技 · 高风险</div><div className="text-xs text-[#64748B] mt-1">报价超过预算，且证书编号、业绩合同编号存在异常，需人工确认后才能形成结论。</div></div>
        <div className="text-xs text-[#64748B]">AI 预警仅提供复核线索，不会自动执行废标。</div>
      </div>
    ),
  })

  const columns: ColumnsType<any> = [
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const s = evalStatusMap[status]
        return <Tag color={s.color} className="!text-xs">{s.label}</Tag>
      },
    },
    {
      title: '项目名称',
      dataIndex: 'projectName',
      key: 'projectName',
      render: (name: string, record) => (
        <div className="cursor-pointer" onClick={() => navigate(`/evaluation/${record.id}`)}>
          <div className="text-sm font-medium text-[#1E293B] hover:text-[#2563EB] transition-colors">{name}</div>
          <div className="text-xs text-[#94A3B8] mt-0.5">{record.tenderNo}</div>
        </div>
      ),
    },
    {
      title: '招标方',
      dataIndex: 'tenderEntity',
      key: 'tenderEntity',
      render: (entity: string) => <span className="text-sm text-[#475569]">{entity}</span>,
    },
    {
      title: '投标人',
      dataIndex: 'bidderCount',
      key: 'bidderCount',
      width: 80,
      render: (count: number) => (
        <div className="flex items-center gap-1">
          <span className="text-sm font-medium text-[#1E293B]">{count}</span>
          <span className="text-xs text-[#94A3B8]">家</span>
        </div>
      ),
    },
    {
      title: '预算',
      dataIndex: 'budget',
      key: 'budget',
      render: (budget: string) => (
        <Tooltip title={`¥${budget}`}><span className="text-sm text-[#475569]">{formatBudget(budget)}</span></Tooltip>
      ),
    },
    {
      title: '评标截止日期',
      dataIndex: 'deadline',
      key: 'deadline',
      render: (date: string, record) => <div><div className="text-xs text-[#64748B]">{date}</div><div className={`text-xs mt-0.5 ${deadlineDays(date) <= 7 && !['completed', 'closed'].includes(record.status) ? 'text-[#D97706]' : 'text-[#64748B]'}`}>{relativeDeadline(record)}</div></div>,
    },
    {
      title: '评审进度',
      key: 'progress',
      width: 160,
      render: (_, record) => (
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-[#64748B]">{evalStatusMap[record.status].step}</span>
            <span className="text-xs font-medium text-[#1E293B]">{record.progress}%</span>
          </div>
          <Tooltip title="评审进度按材料收集、AI 初审、人工复审和结果发布阶段综合计算">
            <div><Progress percent={record.progress} size="small" strokeColor={record.status === 'completed' ? '#16A34A' : record.status === 'ai_review' ? '#7C3AED' : '#2563EB'} showInfo={false} /></div>
          </Tooltip>
        </div>
      ),
    },
    {
      title: '负责人',
      dataIndex: 'assignee',
      key: 'assignee',
      render: (name: string) => (
        <div className="flex items-center gap-2">
          <Avatar size={24} style={{ background: '#2563EB', fontSize: 11 }}>{name.slice(-2)}</Avatar>
          <span className="text-xs text-[#475569]">{name}</span>
        </div>
      ),
    },
  ]

  const boardColumns = [
    { key: 'collecting', title: '材料收集中', color: '#0891B2' },
    { key: 'ai_review', title: 'AI初审中', color: '#7C3AED' },
    { key: 'human_review', title: '人工复审', color: '#D97706' },
    { key: 'completed', title: '已完成/已关闭', color: '#16A34A' },
  ]

  return (
    <div className="p-6">
      {/* Stats */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        {stats.map(stat => {
          const Icon = stat.icon
          return (
            <Card
              key={stat.label}
              hoverable
              onClick={() => stat.filter === 'risk' ? showRisk() : setFilter(stat.filter)}
              className={`!shadow-none cursor-pointer ${filter === stat.filter ? '!border-[#2563EB]' : '!border-[#E2E8F0]'}`}
            >
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

      {/* Toolbar */}
      <div className="bg-white border border-[#E2E8F0] rounded-xl p-3 mb-4 flex flex-col md:flex-row md:items-center gap-2">
        <Input
          allowClear
          value={keyword}
          onChange={event => setKeyword(event.target.value)}
          prefix={<Search size={15} className="text-[#94A3B8]" />}
          placeholder="搜索项目名称、编号或招标方"
          className="md:max-w-[360px]"
        />
        <Select
          value={assignee}
          onChange={setAssignee}
          className="md:w-40"
          options={[{ value: 'all', label: '全部负责人' }, ...assignees.map(name => ({ value: name, label: name }))]}
        />
        <Button icon={<RotateCcw size={14} />} onClick={() => { setKeyword(''); setAssignee('all'); setFilter('all') }}>重置筛选</Button>
        <span className="text-xs text-[#64748B] md:ml-auto">当前显示 {filteredTasks.length} / {evaluationTasks.length} 个任务</span>
      </div>
      <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-3 mb-4">
        <div className="overflow-x-auto"><Segmented value={filter} onChange={(v) => setFilter(v as string)} options={filterTabs} /></div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button icon={<Link2 size={14} />} className="!rounded-lg" onClick={() => navigate('/evaluation/portal/EVAL-2026-001')}>
            打开供应商门户（外部）
          </Button>
          <Button type="primary" icon={<Plus size={14} />} className="!rounded-lg !bg-[#2563EB]" onClick={() => navigate('/evaluation/create')}>
            创建评标任务
          </Button>
          <Segmented
            value={viewMode}
            onChange={(v) => setViewMode(v as 'table' | 'board')}
            options={[
              { label: '表格', value: 'table' },
              { label: '看板', value: 'board' },
            ]}
          />
        </div>
      </div>

      {/* Content */}
      {viewMode === 'table' ? (
        <Card className="!border-[#E2E8F0] !shadow-none overflow-x-auto" styles={{ body: { padding: 0 } }}>
          <Table
            columns={columns}
            dataSource={filteredTasks}
            rowKey="id"
            pagination={{ pageSize: 10, showSizeChanger: false }}
            locale={{ emptyText: <Empty description="当前筛选条件下没有评标任务"><Button onClick={() => { setKeyword(''); setAssignee('all'); setFilter('all') }}>清除筛选</Button></Empty> }}
            onRow={(record) => ({ onClick: () => navigate(`/evaluation/${record.id}`), className: 'cursor-pointer' })}
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {boardColumns.map(col => {
            const tasks = filteredTasks.filter(t => col.key === 'completed' ? (t.status === 'completed' || t.status === 'closed') : t.status === col.key)
            return (
              <div key={col.key} className="rounded-xl bg-[#F8FAFC] p-3">
                <div className="flex items-center justify-between mb-3 px-1">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ background: col.color }} />
                    <span className="text-sm font-medium text-[#1E293B]">{col.title}</span>
                  </div>
                  <span className="text-xs text-[#94A3B8] bg-white px-2 py-0.5 rounded-full">{tasks.length}</span>
                </div>
                <div className="space-y-2">
                  {tasks.map(task => (
                    <div
                      key={task.id}
                      onClick={() => navigate(`/evaluation/${task.id}`)}
                      className="bg-white rounded-lg border border-[#E2E8F0] p-3 cursor-pointer hover:border-[#2563EB] hover:shadow-sm transition-all"
                    >
                      <div className="text-sm font-medium text-[#1E293B] mb-1 line-clamp-2">{task.projectName}</div>
                      <div className="text-xs text-[#94A3B8] mb-2">{task.tenderEntity}</div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1">
                          <Avatar size={20} style={{ background: '#2563EB', fontSize: 10 }}>{task.assignee.slice(-2)}</Avatar>
                          <span className="text-xs text-[#64748B]">{task.bidderCount}家投标人</span>
                        </div>
                        <span className="text-xs font-medium" style={{ color: col.color }}>{task.progress}%</span>
                      </div>
                    </div>
                  ))}
                  {tasks.length === 0 && <div className="rounded-lg border border-dashed border-[#CBD5E1] py-8 text-center text-xs text-[#64748B]">暂无任务</div>}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
