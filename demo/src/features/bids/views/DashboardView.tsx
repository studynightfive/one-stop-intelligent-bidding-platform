import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Tag, Progress, Tooltip, Avatar, Segmented, Empty, Input, Select, Dropdown, Modal, Pagination, message } from 'antd'
import {
  Plus, LayoutGrid, Table2, ClipboardList,
  Download, ShieldCheck, FileOutput, Clock, ChevronRight,
  Search, MoreHorizontal, Copy, Gavel, RotateCcw, Archive
} from 'lucide-react'
import dayjs from 'dayjs'
import { currentUser, statusMap } from '../../../mock/data'
import { useDemo } from '../../../context/DemoContext'
import { downloadTableAsCsv } from '../../../utils/demoActions'
import { BID_BOARD_COLUMNS, BID_STATUS_COLORS, BID_STATUS_FALLBACK, BID_TEST_IDS } from '../constants'
import { buildDashboardStats, deadlineDays, formatDeadlineText } from '../hooks/filterBidTasks'
import { setMockBidTaskSource } from '../adapters/mockBidApi'
import { filterTasksForListQuery } from '../adapters/paginateLocal'
import { usePagedBidTasks } from '../hooks/usePagedBidTasks'
import type { BidTaskViewModel } from '../types'
import { useBidUiState } from '../hooks/useBidUiState'
import {
  BidConflictState,
  BidEmptyState,
  BidErrorState,
  BidForbiddenState,
  BidLoadingState,
  BidNotFoundState,
  BidTimeoutState,
} from '../components/BidPageStates'
import { BidUiStateSwitcher } from '../components/BidUiStateSwitcher'

const boardColumns = BID_BOARD_COLUMNS
const statusColors = BID_STATUS_COLORS

export default function DashboardView() {
  const navigate = useNavigate()
  const { bidTasks: tasks, addBidTask, updateBidTask, getTaskMaterials } = useDemo()
  const [view, setView] = useState<string>('table')
  const [filter, setFilter] = useState<string>('all')
  const [keyword, setKeyword] = useState('')
  const [assigneeFilter, setAssigneeFilter] = useState<string>('all')
  const [quickFilter, setQuickFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const { status: uiStatus, override, setUiOverride, retry } = useBidUiState({ bootstrapMs: 300 })

  useEffect(() => {
    setMockBidTaskSource(() => tasks as BidTaskViewModel[])
  }, [tasks])

  const resetPage = () => setPage(1)

  const listQuery = useMemo(() => ({
    page,
    pageSize,
    keyword,
    status: filter,
    assigneeId: assigneeFilter === 'all' ? undefined : assigneeFilter,
    quickFilter,
    includeArchived: filter === 'archived',
    currentUserName: currentUser.name,
  }), [page, pageSize, keyword, filter, assigneeFilter, quickFilter])

  const listDepsKey = JSON.stringify(listQuery)
  const { data: pagedTasks, meta: pageMeta, loading: listLoading } = usePagedBidTasks(listQuery, listDepsKey)

  const filteredTasks = useMemo(
    () => filterTasksForListQuery(tasks as BidTaskViewModel[], { ...listQuery, page: 1, pageSize: 1000 }),
    [tasks, listQuery],
  )
  const counts = buildDashboardStats(tasks)
  const stats = [
    { label: '总任务数', value: counts.total, icon: ClipboardList, color: '#2563EB', bg: '#EFF6FF', filter: 'all' },
    { label: '进行中', value: counts.active, icon: Clock, color: '#D97706', bg: '#FFFBEB', filter: 'active' },
    { label: '待审核', value: counts.aiReview, icon: ShieldCheck, color: '#7C3AED', bg: '#F5F3FF', filter: 'ai_review' },
    { label: '已完成', value: counts.completed, icon: FileOutput, color: '#16A34A', bg: '#F0FDF4', filter: 'completed' },
  ]

  const assignees = Array.from(new Set(tasks.map(task => task.assignee)))

  const resetFilters = () => {
    setFilter('all')
    setKeyword('')
    setAssigneeFilter('all')
    setQuickFilter('all')
    setPage(1)
  }

  const exportTasks = (items = filteredTasks) => {
    downloadTableAsCsv('投标项目清单.csv', ['项目名称', '招标编号', '招标方', '截止日期', '状态', '负责人', '综合进度', '缺失材料'], items.map(task => [
      task.projectName, task.tenderNo, task.tenderEntity, task.deadline, statusMap[task.status]?.label || task.status, task.assignee, `${task.progress}%`, task.materialMissing,
    ]))
    message.success(`已导出 ${items.length} 个项目`)
  }

  const copyTask = (task: any) => {
    const taskId = `TASK-${dayjs().format('YYYYMMDD-HHmmss')}`
    addBidTask({ ...task, id: taskId, projectName: `${task.projectName}（副本）`, status: 'parsing', currentStep: 1, progress: 5, createdAt: dayjs().format('YYYY-MM-DD') }, getTaskMaterials(task.id))
    message.success('项目副本已创建')
  }

  const archiveTask = (task: any) => {
    Modal.confirm({
      title: `归档「${task.projectName}」？`,
      content: '归档后默认不在工作台列表展示，可从“已归档”筛选查看。',
      okText: '确认归档',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: () => {
        updateBidTask(task.id, { status: 'archived' })
        message.success('项目已归档')
      },
    })
  }

  const showMissingMaterials = (task: any) => {
    const missing = getTaskMaterials(task.id).filter(item => item.status === 'missing')
    Modal.info({
      title: `${task.projectName} · 缺失材料`,
      width: 560,
      content: missing.length ? (
        <div className="mt-3 space-y-2">{missing.map(item => <div key={item.id} className="rounded-lg bg-[#FEF2F2] px-3 py-2 text-sm"><div className="font-medium text-[#991B1B]">{item.name}</div><div className="text-xs text-[#64748B] mt-0.5">{item.requirement}</div></div>)}</div>
      ) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="当前没有缺失材料" />,
      okText: '知道了',
    })
  }

  const deadlineText = (task: any) => formatDeadlineText(task)

  const shell = (body: ReactNode) => (
    <div className="p-6" data-testid={BID_TEST_IDS.dashboard}>
      <div className="flex items-center justify-between mb-4">
        <div className="text-xs text-[#94A3B8]">异常态预览（M1 本地，待真实 API 错误映射后移除）</div>
        <BidUiStateSwitcher value={override} onChange={setUiOverride} />
      </div>
      {body}
    </div>
  )

  if (uiStatus === 'loading') return shell(<BidLoadingState tip="正在加载投标工作台…" />)
  if (uiStatus === 'error') return shell(<BidErrorState onRetry={retry} />)
  if (uiStatus === 'forbidden') return shell(<BidForbiddenState onBack={() => navigate('/dashboard')} />)
  if (uiStatus === 'timeout') return shell(<BidTimeoutState onRetry={retry} />)
  if (uiStatus === 'conflict') return shell(<BidConflictState onRetry={retry} />)
  if (uiStatus === 'not_found') return shell(<BidNotFoundState onBack={() => navigate('/dashboard')} />)
  if (uiStatus === 'empty') {
    return shell(
      <BidEmptyState
        description="当前没有投标任务，可新建任务开始七步闭环。"
        actionLabel="新建投标任务"
        onAction={() => navigate('/tasks/create')}
      />,
    )
  }

  return (
    <div className="p-6" data-testid={BID_TEST_IDS.dashboard}>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#1E293B]">投标工作台</h1>
          <p className="text-sm text-[#64748B] mt-0.5">管理所有投标项目，跟踪进度和任务状态</p>
        </div>
        <div className="flex items-center gap-2">
          <BidUiStateSwitcher value={override} onChange={setUiOverride} />
          <Button
            type="primary"
            size="large"
            icon={<Plus size={16} />}
            onClick={() => navigate('/tasks/create')}
            className="flex items-center gap-1.5"
            data-testid={BID_TEST_IDS.dashboardCreate}
          >
            新建投标任务
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {stats.map(stat => {
          const Icon = stat.icon
          return (
            <button
              key={stat.label}
              type="button"
              onClick={() => { setFilter(stat.filter); resetPage() }}
              className={`bg-white text-left rounded-xl border p-4 flex items-center gap-3 transition-all hover:-translate-y-0.5 hover:shadow-sm ${filter === stat.filter ? 'border-[#2563EB] ring-1 ring-[#DBEAFE]' : 'border-[#E2E8F0]'}`}
            >
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: stat.bg }}>
                <Icon size={20} color={stat.color} />
              </div>
              <div>
                <div className="text-2xl font-semibold text-[#1E293B] leading-tight">{stat.value}</div>
                <div className="text-xs text-[#64748B]">{stat.label}</div>
              </div>
            </button>
          )
        })}
      </div>

      <div className="bg-white rounded-xl border border-[#E2E8F0] p-3 mb-4 flex flex-col xl:flex-row gap-3 xl:items-center xl:justify-between">
        <div className="flex flex-col md:flex-row gap-2 flex-1">
          <Input
            allowClear
            value={keyword}
            onChange={event => { setKeyword(event.target.value); resetPage() }}
            prefix={<Search size={15} className="text-[#94A3B8]" />}
            placeholder="搜索项目名称、编号或招标方"
            className="md:max-w-[320px]"
          />
          <Select
            value={assigneeFilter}
            onChange={value => { setAssigneeFilter(value); resetPage() }}
            className="md:w-36"
            options={[{ value: 'all', label: '全部负责人' }, ...assignees.map(name => ({ value: name, label: name }))]}
          />
          <Segmented
            value={quickFilter}
            onChange={value => { setQuickFilter(String(value)); resetPage() }}
            options={[{ label: '全部项目', value: 'all' }, { label: '我的项目', value: 'mine' }, { label: '临近截止', value: 'due' }, { label: '风险项目', value: 'risk' }]}
          />
        </div>
        <div className="flex gap-2">
          <Button icon={<RotateCcw size={14} />} onClick={resetFilters}>重置</Button>
          <Button icon={<Download size={14} />} onClick={() => exportTasks()}>导出当前结果</Button>
        </div>
      </div>

      {/* Filter + View toggle */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-2 overflow-x-auto pb-1 md:pb-0">
          {[
            { key: 'all', label: '全部' },
            { key: 'active', label: '全部进行中' },
            { key: 'parsing', label: 'AI解析中' },
            { key: 'material_prep', label: '材料准备' },
            { key: 'ai_review', label: 'AI审核中' },
            { key: 'pending_output', label: '待输出' },
            { key: 'completed', label: '已完成' },
            { key: 'archived', label: counts.archived ? `已归档 (${counts.archived})` : '已归档' },
          ].map(f => (
            <button
              key={f.key}
              onClick={() => { setFilter(f.key); resetPage() }}
              className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
                filter === f.key
                  ? 'bg-[#2563EB] text-white font-medium'
                  : 'bg-white text-[#64748B] border border-[#E2E8F0] hover:bg-[#F8FAFC]'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <Segmented
          value={view}
          onChange={(v) => setView(v as string)}
          options={[
            { label: '', value: 'table', icon: <Table2 size={16} /> },
            { label: '', value: 'board', icon: <LayoutGrid size={16} /> }
          ]}
        />
      </div>

      {/* Table view */}
      {view === 'table' && (
        <div className="bg-white rounded-xl border border-[#E2E8F0] overflow-x-auto">
          <table className="w-full min-w-[980px] text-sm">
            <thead>
              <tr className="bg-[#F8FAFC] border-b border-[#E2E8F0]">
                <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">状态</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">项目名称</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">招标方</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">投标截止日期</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">综合进度</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">材料</th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">负责人</th>
                <th className="text-right px-4 py-3 text-xs font-medium text-[#64748B]"></th>
              </tr>
            </thead>
            <tbody>
              {pagedTasks.map(task => {
                const status = statusMap[task.status] || BID_STATUS_FALLBACK[task.status] || { label: task.status, color: 'default' }
                return (
                  <tr
                    key={task.id}
                    onClick={() => navigate(`/tasks/${task.id}`)}
                    className="border-b border-[#F1F5F9] hover:bg-[#F8FAFC] cursor-pointer transition-colors"
                  >
                    <td className="px-4 py-3">
                      <Tag color={status.color} className="rounded-md border-0 text-xs">{status.label}</Tag>
                    </td>
                    <td className="px-4 py-3 max-w-xs">
                      <div className="text-[#1E293B] font-medium truncate">{task.projectName}</div>
                      <div className="text-xs text-[#94A3B8] font-mono mt-0.5">{task.tenderNo}</div>
                    </td>
                    <td className="px-4 py-3 text-[#64748B] text-xs">{task.tenderEntity}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1 text-xs text-[#64748B]">
                        <Clock size={12} />
                        {task.deadline}
                      </div>
                      <div className={`text-xs mt-0.5 ${deadlineDays(task.deadline) < 0 && task.status !== 'completed' ? 'text-[#DC2626]' : deadlineDays(task.deadline) <= 7 && task.status !== 'completed' ? 'text-[#D97706]' : 'text-[#64748B]'}`}>{deadlineText(task)}</div>
                    </td>
                    <td className="px-4 py-3 w-32">
                      <Tooltip title="综合进度由当前流程阶段与材料完整度综合计算">
                        <div><Progress percent={task.progress} size="small" strokeColor="#2563EB" /></div>
                      </Tooltip>
                      <div className="text-xs text-[#64748B] mt-0.5">当前步骤 {task.currentStep}/7</div>
                    </td>
                    <td className="px-4 py-3">
                      {task.materialTotal > 0 ? (
                        <span className="text-xs">
                          <span className="text-[#16A34A] font-medium">{task.materialHave}</span>
                          <span className="text-[#94A3B8]">/{task.materialTotal}</span>
                          {task.materialMissing > 0 && (
                            <button type="button" onClick={event => { event.stopPropagation(); showMissingMaterials(task) }} className="text-[#DC2626] ml-1 hover:underline">({task.materialMissing}缺失)</button>
                          )}
                        </span>
                      ) : (
                        <span className="text-xs text-[#94A3B8]">待解析</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <Avatar size={22} style={{ background: '#2563EB', fontSize: 10 }}>
                          {task.assignee.charAt(0)}
                        </Avatar>
                        <span className="text-xs text-[#64748B]">{task.assignee}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Dropdown
                          trigger={['click']}
                          menu={{
                            items: [
                              { key: 'evaluation', label: '发起评标任务', icon: <Gavel size={14} />, disabled: task.status === 'archived' },
                              { key: 'copy', label: '复制项目', icon: <Copy size={14} /> },
                              { key: 'archive', label: '归档项目', icon: <Archive size={14} />, disabled: task.status === 'archived' },
                              { key: 'export', label: '导出项目概览', icon: <Download size={14} /> },
                            ],
                            onClick: ({ key, domEvent }) => {
                              domEvent.stopPropagation()
                              if (key === 'evaluation') navigate(`/evaluation/create?sourceTask=${task.id}`)
                              if (key === 'copy') copyTask(task)
                              if (key === 'archive') archiveTask(task)
                              if (key === 'export') exportTasks([task])
                            },
                          }}
                        >
                          <Button type="text" size="small" icon={<MoreHorizontal size={16} />} onClick={event => event.stopPropagation()} aria-label="更多操作" />
                        </Dropdown>
                        <ChevronRight size={16} className="text-[#CBD5E1]" />
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          {!listLoading && pageMeta.total === 0 && (
            <div data-testid={BID_TEST_IDS.dashboardEmpty}>
              <BidEmptyState description="当前筛选条件下没有项目" actionLabel="清除筛选条件" onAction={resetFilters} />
            </div>
          )}
          {pageMeta.total > 0 && (
            <div className="flex justify-end px-4 py-3 border-t border-[#F1F5F9]" data-testid={BID_TEST_IDS.dashboardPagination}>
              <Pagination
                size="small"
                current={pageMeta.page}
                pageSize={pageMeta.pageSize}
                total={pageMeta.total}
                showSizeChanger
                showTotal={(total) => `共 ${total} 条`}
                pageSizeOptions={[10, 20, 50]}
                onChange={(nextPage, nextSize) => {
                  setPage(nextPage)
                  setPageSize(nextSize)
                }}
              />
            </div>
          )}

        </div>
      )}

      {/* Board view */}
      {view === 'board' && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-4">
          {boardColumns.map(col => {
            const colTasks = filteredTasks.filter(t => t.status === col.key)
            const status = statusMap[col.key]
            return (
              <div key={col.key} className="bg-[#F1F5F9] rounded-xl p-3 min-h-[200px]">
                <div className="flex items-center justify-between mb-3 px-1">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full" style={{ background: statusColors[status?.color] || '#94A3B8' }} />
                    <span className="text-xs font-medium text-[#334155]">{col.title}</span>
                  </div>
                  <span className="text-xs text-[#94A3B8] bg-white px-1.5 py-0.5 rounded">{colTasks.length}</span>
                </div>
                <div className="space-y-2">
                  {colTasks.map(task => (
                    <div
                      key={task.id}
                      onClick={() => navigate(`/tasks/${task.id}`)}
                      className="bg-white rounded-lg border border-[#E2E8F0] p-3 cursor-pointer hover:border-[#2563EB] hover:shadow-sm transition-all"
                    >
                      <div className="text-sm font-medium text-[#1E293B] mb-1 line-clamp-2">{task.projectName}</div>
                      <div className="text-xs text-[#94A3B8] font-mono mb-2">{task.tenderNo}</div>
                      <Progress percent={task.progress} size="small" strokeColor="#2563EB" />
                      <div className="flex items-center justify-between mt-2">
                        <div>
                          <div className="flex items-center gap-1 text-xs text-[#64748B]"><Clock size={12} />{task.deadline}</div>
                          <div className={`text-xs mt-0.5 ${deadlineDays(task.deadline) <= 7 && task.status !== 'completed' ? 'text-[#D97706]' : 'text-[#64748B]'}`}>{deadlineText(task)}</div>
                        </div>
                        <Avatar size={20} style={{ background: '#2563EB', fontSize: 9 }}>{task.assignee.charAt(0)}</Avatar>
                      </div>
                      {task.materialTotal > 0 && (
                        <div className="mt-2 pt-2 border-t border-[#F1F5F9] text-xs">
                          <span className="text-[#16A34A] font-medium">{task.materialHave}</span>
                          <span className="text-[#94A3B8]">/{task.materialTotal} 材料</span>
                          {task.materialMissing > 0 && (
                            <button type="button" onClick={event => { event.stopPropagation(); showMissingMaterials(task) }}><Tag color="red" className="ml-2 text-xs border-0 rounded hover:underline">{task.materialMissing}缺失</Tag></button>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                  {colTasks.length === 0 && (
                    <div className="text-center py-8 text-xs text-[#94A3B8]">暂无任务</div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
