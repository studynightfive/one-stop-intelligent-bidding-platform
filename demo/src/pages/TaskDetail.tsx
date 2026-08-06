import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Button, Tag, Progress, Tabs, Tooltip, Avatar, Badge, Upload as AntUpload, Modal, Form, Input, Select, message } from 'antd'
import {
  Upload, FileSearch, ClipboardList, Download, UploadCloud, ShieldCheck,
  FileOutput, Check, ChevronRight, ChevronLeft, AlertCircle, AlertTriangle,
  Info, Lightbulb, Clock, Users2, History, FileText, FileCheck2, FileWarning,
  Download as DownloadIcon, RefreshCw, ArrowLeft, Zap, TrendingUp, CircleDot, Gavel
} from 'lucide-react'
import {
  statusMap, workflowSteps, materialStatusMap,
  reviewSuggestions, reviewSummary, documentVersions, tenderRequirements,
  currentUser
} from '../mock/data'
import { useDemo } from '../context/DemoContext'
import { downloadDemoFile, downloadTableAsCsv } from '../utils/demoActions'

const stepIcons: Record<number, any> = {
  1: Upload, 2: FileSearch, 3: ClipboardList, 4: Download,
  5: UploadCloud, 6: ShieldCheck, 7: FileOutput
}

const severityConfig = {
  error: { icon: AlertCircle, color: '#DC2626', bg: '#FEF2F2', label: '错误' },
  warning: { icon: AlertTriangle, color: '#D97706', bg: '#FFFBEB', label: '警告' },
  info: { icon: Info, color: '#2563EB', bg: '#EFF6FF', label: '建议' },
  suggestion: { icon: Lightbulb, color: '#0891B2', bg: '#ECFEFF', label: '优化' }
}

export default function TaskDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { bidTasks, evaluationTasks, getTaskMaterials, updateTaskMaterial, addTaskMaterial, removeTaskMaterial, updateBidTask } = useDemo()
  const [activeTab, setActiveTab] = useState('materials')
  const [reviewProcessing, setReviewProcessing] = useState(false)
  const [reviewDone, setReviewDone] = useState(true)
  const [suggestionStates, setSuggestionStates] = useState<Record<string, string>>({})
  const [outputVersions, setOutputVersions] = useState<any[]>(documentVersions)

  const task = bidTasks.find(t => t.id === id) || bidTasks[0]
  const relatedEvaluation = evaluationTasks.find(item => item.tenderNo === task?.tenderNo)
  const taskMaterials = getTaskMaterials(task?.id)
  const have = taskMaterials.filter(m => m.status === 'have').length
  const missing = taskMaterials.filter(m => m.status === 'missing').length
  const template = taskMaterials.filter(m => m.status === 'template').length
  const total = taskMaterials.length

  const partLabels: Record<string, string> = {
    qualification: '资质标',
    commercial: '商务标',
    technical: '技术标'
  }

  const runReview = () => {
    setReviewProcessing(true)
    setReviewDone(false)
    message.loading({ content: 'AI 正在重新检查材料与文档一致性…', key: 'task-review', duration: 0 })
    window.setTimeout(() => {
      setReviewProcessing(false)
      setReviewDone(true)
      updateBidTask(task.id, { status: 'pending_output', currentStep: 7, progress: 92 })
      message.success({ content: '复审完成，已更新审核结果', key: 'task-review' })
    }, 1400)
  }

  const handleSuggestion = (suggestionId: string, action: string) => {
    setSuggestionStates(prev => ({ ...prev, [suggestionId]: action }))
    message.success(action === 'accepted' ? '已采纳建议并加入修改清单' : action === 'ignored' ? '已忽略该建议' : '已打开手动修改流程')
  }

  if (!task) return <div className="p-6">暂无投标任务</div>

  return (
    <div className="p-6">
      {/* Back button */}
      <div className="flex items-center gap-2 mb-4">
        <Button type="text" size="small" icon={<ArrowLeft size={16} />} onClick={() => navigate('/dashboard')}>
          返回投标工作台
        </Button>
      </div>

      {/* Task header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h1 className="text-xl font-semibold text-[#1E293B]">{task.projectName}</h1>
            <Tag color={statusMap[task.status].color} className="rounded-md border-0">{statusMap[task.status].label}</Tag>
          </div>
          <div className="flex items-center gap-4 text-xs text-[#64748B]">
            <span className="font-mono">{task.tenderNo}</span>
            <span>{task.tenderEntity}</span>
            <span className="flex items-center gap-1"><Clock size={12} />截止：{task.deadline}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button icon={<RefreshCw size={14} />} onClick={() => message.success('任务状态已刷新')}>刷新</Button>
          <Button icon={<Gavel size={14} />} onClick={() => navigate(relatedEvaluation ? `/evaluation/${relatedEvaluation.id}` : `/evaluation/create?sourceTask=${task.id}`)}>{relatedEvaluation ? '查看关联评标' : '发起评标任务'}</Button>
          <Button type="primary" icon={<FileOutput size={14} />} onClick={() => { setActiveTab('output'); downloadDemoFile(`${task.projectName}-投标文件说明.txt`, `${task.projectName}\n当前演示已生成投标文件包。`) }}>导出投标文件</Button>
        </div>
      </div>

      {/* 7-Step Indicator */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] p-5 mb-6">
        <div className="flex items-center justify-between min-w-[880px]">
          {workflowSteps.map((step, idx) => {
            const Icon = stepIcons[step.step]
            const isDone = task.currentStep > step.step
            const isCurrent = task.currentStep === step.step
            return (
              <div key={step.step} className="flex items-center flex-1">
                <div className="flex flex-col items-center gap-1.5 flex-shrink-0">
                  <Tooltip title={`${step.step}. ${step.title} - ${step.desc}`}>
                    <div
                      className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
                        isDone
                          ? 'bg-[#16A34A] text-white'
                          : isCurrent
                          ? 'bg-[#2563EB] text-white shadow-md shadow-blue-200 ring-4 ring-blue-50'
                          : 'bg-[#F1F5F9] text-[#94A3B8]'
                      }`}
                    >
                      {isDone ? <Check size={18} /> : <Icon size={18} />}
                    </div>
                  </Tooltip>
                  <div className="text-center">
                    <div className={`text-xs font-medium ${isCurrent ? 'text-[#2563EB]' : isDone ? 'text-[#16A34A]' : 'text-[#94A3B8]'}`}>
                      {step.title}
                    </div>
                  </div>
                </div>
                {idx < workflowSteps.length - 1 && (
                  <div className={`flex-1 h-0.5 mx-2 rounded-full ${isDone ? 'bg-[#16A34A]' : 'bg-[#E2E8F0]'}`} />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* Main content: 3 columns */}
      <div className="grid grid-cols-1 xl:grid-cols-[256px_minmax(0,1fr)_288px] gap-5">
        {/* Left: Task info */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-[#E2E8F0] p-4">
            <div className="text-xs font-medium text-[#64748B] mb-3">项目信息</div>
            <div className="space-y-2.5 text-xs">
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">招标编号</span>
                <span className="text-[#1E293B] font-mono">{task.tenderNo}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">招标方</span>
                <span className="text-[#1E293B]">{task.tenderEntity}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">截止时间</span>
                <span className="text-[#1E293B]">{task.deadline}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">预算金额</span>
                <span className="text-[#1E293B] font-medium">{tenderRequirements.budget}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#94A3B8]">要求工期</span>
                <span className="text-[#1E293B]">{tenderRequirements.duration}</span>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl border border-[#E2E8F0] p-4">
            <div className="text-xs font-medium text-[#64748B] mb-3 flex items-center gap-1.5">
              <Users2 size={14} /> 协作成员
            </div>
            <div className="space-y-2">
              {[
                { name: '张明远', role: '项目负责人', color: '#2563EB' },
                { name: '李雪琴', role: '商务标', color: '#D97706' },
                { name: '王建国', role: '技术标', color: '#16A34A' },
                { name: '陈审核', role: '审核员', color: '#7C3AED' }
              ].map(m => (
                <div key={m.name} className="flex items-center gap-2">
                  <Avatar size={24} style={{ background: m.color, fontSize: 10 }}>{m.name.charAt(0)}</Avatar>
                  <div>
                    <div className="text-xs text-[#1E293B]">{m.name}</div>
                    <div className="text-xs text-[#94A3B8]">{m.role}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white rounded-xl border border-[#E2E8F0] p-4">
            <div className="text-xs font-medium text-[#64748B] mb-3 flex items-center gap-1.5">
              <History size={14} /> 版本历史
            </div>
            <div className="space-y-2">
              {documentVersions.slice(0, 4).map((v, i) => (
                <div key={v.version} className="flex items-start gap-2">
                  <div className={`w-1.5 h-1.5 rounded-full mt-1.5 ${v.status === 'latest' ? 'bg-[#16A34A]' : 'bg-[#CBD5E1]'}`} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs font-medium text-[#1E293B] font-mono">{v.version}</span>
                      {v.status === 'latest' && <Tag color="green" className="text-xs border-0 rounded">最新</Tag>}
                    </div>
                    <div className="text-xs text-[#94A3B8] truncate">{v.changeSummary}</div>
                    <div className="text-xs text-[#CBD5E1]">{v.createdAt}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Center: Tab content */}
        <div className="flex-1 min-w-0">
          <div className="bg-white rounded-xl border border-[#E2E8F0]">
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              className="px-4"
              items={[
                { key: 'materials', label: '材料清单', children: <MaterialsTab taskId={task.id} materials={taskMaterials} have={have} missing={missing} template={template} total={total} partLabels={partLabels} updateMaterial={updateTaskMaterial} addMaterial={addTaskMaterial} removeMaterial={removeTaskMaterial} /> },
                { key: 'review', label: 'AI审核', children: <ReviewTab processing={reviewProcessing} done={reviewDone} onRerun={runReview} suggestionStates={suggestionStates} onSuggestion={handleSuggestion} /> },
                { key: 'output', label: '文档输出', children: <OutputTab projectName={task.projectName} versions={outputVersions} setVersions={setOutputVersions} /> },
                { key: 'requirements', label: '招标要求', children: <RequirementsTab /> }
              ]}
            />
          </div>
        </div>

        {/* Right: AI suggestions */}
        <div>
          <div className="bg-white rounded-xl border border-[#E2E8F0] p-4 sticky top-0">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-6 h-6 rounded-lg bg-[#EFF6FF] flex items-center justify-center">
                <Zap size={14} color="#2563EB" />
              </div>
              <span className="text-sm font-medium text-[#1E293B]">AI 建议</span>
              <Badge count={reviewSummary.total} size="small" color="#DC2626" />
            </div>

            <div className="grid grid-cols-3 gap-2 mb-4">
              <div className="bg-[#FEF2F2] rounded-lg p-2 text-center">
                <div className="text-lg font-semibold text-[#DC2626]">{reviewSummary.errors}</div>
                <div className="text-xs text-[#94A3B8]">错误</div>
              </div>
              <div className="bg-[#FFFBEB] rounded-lg p-2 text-center">
                <div className="text-lg font-semibold text-[#D97706]">{reviewSummary.warnings}</div>
                <div className="text-xs text-[#94A3B8]">警告</div>
              </div>
              <div className="bg-[#EFF6FF] rounded-lg p-2 text-center">
                <div className="text-lg font-semibold text-[#2563EB]">{reviewSummary.info}</div>
                <div className="text-xs text-[#94A3B8]">建议</div>
              </div>
            </div>

            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {reviewSuggestions.map(s => {
                const cfg = severityConfig[s.severity as keyof typeof severityConfig]
                const Icon = cfg.icon
                return (
                  <div key={s.id} className="border border-[#F1F5F9] rounded-lg p-3 hover:border-[#E2E8F0] transition-colors">
                    <div className="flex items-start gap-2 mb-1.5">
                      <div className="w-5 h-5 rounded flex items-center justify-center flex-shrink-0 mt-0.5" style={{ background: cfg.bg }}>
                        <Icon size={13} color={cfg.color} />
                      </div>
                      <div className="text-xs font-medium text-[#1E293B] flex-1">{s.title}</div>
                    </div>
                    <div className="text-xs text-[#64748B] mb-1.5 pl-7">{s.description}</div>
                    <div className="text-xs text-[#94A3B8] pl-7 mb-2">
                      <span className="font-mono">{s.location}</span>
                    </div>
                    <div className="flex items-center gap-1.5 pl-7">
                      <Button disabled={Boolean(suggestionStates[s.id])} onClick={() => handleSuggestion(s.id, 'accepted')} size="small" type="primary" className="text-xs h-6">采纳</Button>
                      <Button disabled={Boolean(suggestionStates[s.id])} onClick={() => handleSuggestion(s.id, 'ignored')} size="small" className="text-xs h-6">忽略</Button>
                      <Button disabled={Boolean(suggestionStates[s.id])} onClick={() => handleSuggestion(s.id, 'manual')} size="small" type="text" className="text-xs h-6">手动修改</Button>
                      {suggestionStates[s.id] && <Tag color="green" className="!m-0">已处理</Tag>}
                    </div>
                  </div>
                )
              })}
            </div>

            <div className="mt-3 pt-3 border-t border-[#F1F5F9]">
              <div className="text-xs font-medium text-[#16A34A] mb-2 flex items-center gap-1">
                <Check size={12} /> 审核通过项
              </div>
              <div className="space-y-1">
                {reviewSummary.passed.map((p, i) => (
                  <div key={i} className="text-xs text-[#64748B] flex items-center gap-1.5">
                    <Check size={11} color="#16A34A" />
                    {p}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Materials Tab
function MaterialsTab({ taskId, materials, have, missing, template, total, partLabels, updateMaterial, addMaterial, removeMaterial }: any) {
  const [expandedPart, setExpandedPart] = useState<string>('all')
  const [addOpen, setAddOpen] = useState(false)
  const [draft, setDraft] = useState({ name: '', type: '资质文件', part: 'qualification', requirement: '' })

  const parts = ['qualification', 'commercial', 'technical']
  const filteredMaterials = expandedPart === 'all' ? materials : materials.filter((m: any) => m.part === expandedPart)

  const createMaterial = () => {
    if (!draft.name.trim() || !draft.requirement.trim()) {
      message.warning('请填写材料名称和招标要求')
      return
    }
    addMaterial(taskId, {
      id: `M-${Date.now()}`,
      ...draft,
      status: 'missing',
      source: '手动新增',
      libraryRef: null,
    })
    setDraft({ name: '', type: '资质文件', part: 'qualification', requirement: '' })
    setAddOpen(false)
    message.success('材料已加入清单')
  }

  const batchUpload = (file: File) => {
    const targets = materials.filter((item: any) => item.status === 'missing')
    targets.forEach((item: any) => updateMaterial(taskId, item.id, { status: 'have', source: '批量上传', fileName: file.name }))
    message.success(targets.length ? `已匹配并补齐 ${targets.length} 项缺失材料` : '当前没有待补齐材料')
    return false
  }

  return (
    <div className="pb-4">
      {/* Progress summary */}
      <div className="grid grid-cols-4 gap-3 mb-4">
        <div className="bg-[#F8FAFC] rounded-lg p-3">
          <div className="text-2xl font-semibold text-[#1E293B]">{total}</div>
          <div className="text-xs text-[#64748B]">总需材料</div>
        </div>
        <div className="bg-[#F0FDF4] rounded-lg p-3">
          <div className="text-2xl font-semibold text-[#16A34A]">{have}</div>
          <div className="text-xs text-[#64748B]">已有</div>
        </div>
        <div className="bg-[#FEF2F2] rounded-lg p-3">
          <div className="text-2xl font-semibold text-[#DC2626]">{missing}</div>
          <div className="text-xs text-[#64748B]">缺失</div>
        </div>
        <div className="bg-[#EFF6FF] rounded-lg p-3">
          <div className="text-2xl font-semibold text-[#2563EB]">{template}</div>
          <div className="text-xs text-[#64748B]">模板可下载</div>
        </div>
      </div>

      <Progress percent={Math.round((have / total) * 100)} strokeColor="#2563EB" className="mb-4" />

      {/* Part filter */}
      <div className="flex items-center gap-2 mb-3">
        <button
          onClick={() => setExpandedPart('all')}
          className={`px-3 py-1 text-xs rounded-lg ${expandedPart === 'all' ? 'bg-[#2563EB] text-white' : 'bg-[#F8FAFC] text-[#64748B]'}`}
        >全部</button>
        {parts.map(p => (
          <button
            key={p}
            onClick={() => setExpandedPart(p)}
            className={`px-3 py-1 text-xs rounded-lg ${expandedPart === p ? 'bg-[#2563EB] text-white' : 'bg-[#F8FAFC] text-[#64748B]'}`}
          >{partLabels[p]}</button>
        ))}
        <div className="flex-1" />
        <Button size="small" onClick={() => setAddOpen(true)} className="text-xs">新增材料</Button>
        <Button size="small" icon={<Download size={14} />} onClick={() => downloadTableAsCsv('投标材料清单.csv', ['材料名称', '类型', '招标要求', '状态', '来源'], filteredMaterials.map((m: any) => [m.name, m.type, m.requirement, materialStatusMap[m.status]?.label || m.status, m.source]))} className="text-xs">导出清单</Button>
      </div>

      {/* Materials table */}
      <div className="border border-[#F1F5F9] rounded-lg overflow-x-auto">
        <table className="w-full min-w-[760px] text-xs">
          <thead>
            <tr className="bg-[#F8FAFC] border-b border-[#E2E8F0]">
              <th className="text-left px-3 py-2 font-medium text-[#64748B] w-8">#</th>
              <th className="text-left px-3 py-2 font-medium text-[#64748B]">材料名称</th>
              <th className="text-left px-3 py-2 font-medium text-[#64748B] w-20">类型</th>
              <th className="text-left px-3 py-2 font-medium text-[#64748B]">招标要求</th>
              <th className="text-left px-3 py-2 font-medium text-[#64748B] w-20">状态</th>
              <th className="text-left px-3 py-2 font-medium text-[#64748B] w-20">来源</th>
              <th className="text-right px-3 py-2 font-medium text-[#64748B] w-24">操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredMaterials.map((m: any, i: number) => {
              const status = materialStatusMap[m.status]
              return (
                <tr key={m.id} className="border-b border-[#F8FAFC] hover:bg-[#F8FAFC]">
                  <td className="px-3 py-2.5 text-[#94A3B8]">{i + 1}</td>
                  <td className="px-3 py-2.5">
                    <div className="text-[#1E293B] font-medium">{m.name}</div>
                    <div className="text-xs text-[#94A3B8]">{partLabels[m.part]}</div>
                  </td>
                  <td className="px-3 py-2.5 text-[#64748B]">{m.type}</td>
                  <td className="px-3 py-2.5 text-[#64748B] max-w-xs">
                    <div className="truncate">{m.requirement}</div>
                  </td>
                  <td className="px-3 py-2.5">
                    <span
                      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                      style={{ color: status.color, background: status.bg }}
                    >
                      {status.label}
                    </span>
                  </td>
                  <td className="px-3 py-2.5 text-[#64748B]">{m.source}</td>
                  <td className="px-3 py-2.5 text-right">
                    {m.status === 'have' && <Button type="link" onClick={() => Modal.info({ title: m.name, content: `演示预览：${m.fileName || m.name + '.pdf'} 已通过材料匹配。` })} size="small" className="text-xs p-0 h-5">预览</Button>}
                    {(m.status === 'missing' || m.status === 'expiring') && (
                      <AntUpload showUploadList={false} beforeUpload={(file) => { updateMaterial(taskId, m.id, { status: 'have', source: '本次上传', fileName: file.name }); message.success(`${m.name} 上传成功`); return false }}>
                        <Button type="link" size="small" className="text-xs p-0 h-5">{m.status === 'expiring' ? '更新' : '上传'}</Button>
                      </AntUpload>
                    )}
                    {m.status === 'template' && <Button type="link" onClick={() => downloadDemoFile(`${m.name}-模板.docx`, `${m.name}\n\n请按招标要求填写后上传。`)} size="small" className="text-xs p-0 h-5">下载模板</Button>}
                    <Button type="link" danger size="small" onClick={() => Modal.confirm({ title: `删除“${m.name}”？`, content: '仅影响当前演示任务。', onOk: () => removeMaterial(taskId, m.id) })} className="text-xs !px-1 h-5">删除</Button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Drag-drop upload zone */}
      <AntUpload.Dragger multiple showUploadList={false} beforeUpload={batchUpload} className="!mt-4">
        <UploadCloud size={28} className="mx-auto text-[#94A3B8] mb-2" />
        <div className="text-sm text-[#64748B]">拖拽文件到此处批量上传，或<span className="text-[#2563EB]">点击选择文件</span></div>
        <div className="text-xs text-[#94A3B8] mt-1">演示模式会自动匹配并补齐当前缺失材料</div>
      </AntUpload.Dragger>

      <Modal title="新增材料" open={addOpen} onCancel={() => setAddOpen(false)} onOk={createMaterial} okText="加入清单" cancelText="取消">
        <div className="space-y-4 pt-2">
          <Input value={draft.name} onChange={e => setDraft(prev => ({ ...prev, name: e.target.value }))} placeholder="材料名称" />
          <div className="grid grid-cols-2 gap-3">
            <Select value={draft.part} onChange={part => setDraft(prev => ({ ...prev, part }))} options={Object.entries(partLabels).map(([value, label]) => ({ value, label }))} />
            <Input value={draft.type} onChange={e => setDraft(prev => ({ ...prev, type: e.target.value }))} placeholder="材料类型" />
          </div>
          <Input.TextArea value={draft.requirement} onChange={e => setDraft(prev => ({ ...prev, requirement: e.target.value }))} placeholder="招标要求" rows={3} />
        </div>
      </Modal>
    </div>
  )
}

// AI Review Tab
function ReviewTab({ processing, done, onRerun, suggestionStates, onSuggestion }: { processing: boolean; done: boolean; onRerun: () => void; suggestionStates: Record<string, string>; onSuggestion: (id: string, action: string) => void }) {
  const reviewSteps = [
    { label: '正在解析文档结构...', done: true },
    { label: '正在检查签字盖章...', done: true },
    { label: '正在核对价格填充...', done: true },
    { label: '正在检查内容响应...', done: true },
    { label: '正在验证逻辑一致性...', done: true },
    { label: '正在生成审核报告...', done: true }
  ]

  return (
    <div className="pb-4">
      {/* Review summary */}
      <div className="bg-gradient-to-r from-[#EFF6FF] to-[#F0FDF4] rounded-xl p-4 mb-4">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <ShieldCheck size={18} color="#2563EB" />
              <span className="text-sm font-semibold text-[#1E293B]">{processing ? 'AI 正在复审' : 'AI审核完成'}</span>
              <Tag color={processing ? 'processing' : 'green'} className="border-0 rounded text-xs">{processing ? '处理中' : done ? '已完成' : '待审核'}</Tag>
            </div>
            <div className="text-xs text-[#64748B]">
              共发现 <span className="text-[#DC2626] font-medium">{reviewSummary.total}</span> 处问题，
              其中 <span className="text-[#DC2626] font-medium">{reviewSummary.errors} 错误</span>，
              <span className="text-[#D97706] font-medium"> {reviewSummary.warnings} 警告</span>，
              <span className="text-[#2563EB] font-medium"> {reviewSummary.info} 建议</span>
            </div>
          </div>
          <Button loading={processing} disabled={processing} onClick={onRerun} type="primary" icon={<RefreshCw size={14} />} className="text-xs">重新审核</Button>
        </div>
      </div>

      {/* Processing steps (show as completed) */}
      <div className="bg-[#F8FAFC] rounded-lg p-4 mb-4">
        <div className="text-xs font-medium text-[#64748B] mb-3">AI审核处理步骤</div>
        <div className="space-y-2">
          {reviewSteps.map((step, i) => (
            <div key={i} className="flex items-center gap-2">
              <div className={`w-5 h-5 rounded-full flex items-center justify-center ${!processing && step.done ? 'bg-[#16A34A]' : 'bg-[#DBEAFE]'}`}>
                {!processing && step.done ? <Check size={12} color="#fff" /> : <CircleDot size={12} color="#2563EB" />}
              </div>
              <span className={`text-xs ${step.done ? 'text-[#1E293B]' : 'text-[#94A3B8]'}`}>{step.label}</span>
              {step.done && <span className="text-xs text-[#16A34A] ml-auto">完成</span>}
            </div>
          ))}
        </div>
      </div>

      {/* Detailed suggestions */}
      <div className="space-y-3">
        <div className="text-sm font-medium text-[#1E293B]">详细审核结果</div>
        {reviewSuggestions.map(s => {
          const cfg = severityConfig[s.severity as keyof typeof severityConfig]
          const Icon = cfg.icon
          const typeLabels: Record<string, string> = {
            signature: '签字审核',
            price: '价格审核',
            content: '内容核对',
            consistency: '一致性检查'
          }
          return (
            <div key={s.id} className="border border-[#E2E8F0] rounded-lg p-4">
              <div className="flex items-start gap-3 mb-2">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: cfg.bg }}>
                  <Icon size={16} color={cfg.color} />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-medium text-[#1E293B]">{s.title}</span>
                    <Tag style={{ color: cfg.color, background: cfg.bg, border: 0 }} className="text-xs rounded">{cfg.label}</Tag>
                    <Tag className="text-xs border-0 rounded bg-[#F1F5F9] text-[#64748B]">{typeLabels[s.type]}</Tag>
                  </div>
                  <div className="text-xs text-[#64748B] mb-2">{s.description}</div>
                  <div className="flex items-center gap-2 text-xs mb-2">
                    <FileWarning size={12} className="text-[#94A3B8]" />
                    <span className="text-[#94A3B8] font-mono">{s.location}</span>
                  </div>
                  <div className="bg-[#F8FAFC] rounded-lg p-2.5 text-xs text-[#334155] flex items-start gap-2">
                    <Lightbulb size={13} className="text-[#D97706] mt-0.5 flex-shrink-0" />
                    <span>{s.suggestion}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2 pl-11">
                <Button disabled={Boolean(suggestionStates[s.id])} onClick={() => onSuggestion(s.id, 'accepted')} type="primary" size="small" className="text-xs h-7">采纳建议</Button>
                <Button disabled={Boolean(suggestionStates[s.id])} onClick={() => onSuggestion(s.id, 'ignored')} size="small" className="text-xs h-7">忽略</Button>
                <Button disabled={Boolean(suggestionStates[s.id])} onClick={() => onSuggestion(s.id, 'manual')} size="small" type="text" className="text-xs h-7">手动修改</Button>
                {suggestionStates[s.id] && <Tag color="green">已处理</Tag>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// Document Output Tab
function OutputTab({ projectName, versions, setVersions }: { projectName: string; versions: any[]; setVersions: React.Dispatch<React.SetStateAction<any[]>> }) {
  const [generating, setGenerating] = useState(false)
  const docTypes = [
    { type: 'qualification', name: '资质标', icon: FileCheck2, color: '#2563EB', bg: '#EFF6FF', pages: 45, status: 'ready' },
    { type: 'commercial', name: '商务标', icon: FileText, color: '#D97706', bg: '#FFFBEB', pages: 12, status: 'ready' },
    { type: 'technical', name: '技术标', icon: FileText, color: '#16A34A', bg: '#F0FDF4', pages: 68, status: 'ready' }
  ]

  const generateDocuments = () => {
    setGenerating(true)
    window.setTimeout(() => {
      const nextVersion = `v${versions.length + 1}.0`
      setVersions(prev => [
        { version: nextVersion, status: 'latest', createdAt: new Date().toLocaleString('zh-CN', { hour12: false }), changeSummary: '重新汇总材料并生成完整投标文件', createdBy: '张明远' },
        ...prev.map(item => ({ ...item, status: 'archived' })),
      ])
      setGenerating(false)
      message.success(`已生成 ${nextVersion} 版本`)
    }, 1200)
  }

  const downloadPackage = (name = `${projectName}-投标文件包.txt`) => downloadDemoFile(name, `${projectName}\n\n资质标、商务标、技术标已生成。\n此文件用于演示下载流程。`)

  const rollback = (version: string) => {
    Modal.confirm({
      title: `回滚到 ${version}？`,
      content: '系统会保留现有版本并将所选版本设为最新版本。',
      onOk: () => {
        setVersions(prev => prev.map(item => ({ ...item, status: item.version === version ? 'latest' : 'archived' })))
        message.success(`已回滚到 ${version}`)
      },
    })
  }

  return (
    <div className="pb-4">
      <div className="bg-[#F8FAFC] rounded-xl p-4 mb-4">
        <div className="text-sm font-medium text-[#1E293B] mb-1">输出配置</div>
        <div className="text-xs text-[#64748B] mb-3">按招标文件要求，投标文件拆分为资质标、商务标、技术标三部分</div>
        <div className="flex items-center gap-2">
          <Button loading={generating} onClick={generateDocuments} type="primary" icon={<FileOutput size={14} />}>生成全部投标文件</Button>
          <Button onClick={() => downloadPackage()} icon={<DownloadIcon size={14} />}>下载全部 (ZIP)</Button>
        </div>
      </div>

      {/* Document cards */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        {docTypes.map(doc => {
          const Icon = doc.icon
          return (
            <div key={doc.type} className="border border-[#E2E8F0] rounded-xl p-4 hover:shadow-md transition-shadow">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: doc.bg }}>
                  <Icon size={20} color={doc.color} />
                </div>
                <div>
                  <div className="text-sm font-medium text-[#1E293B]">{doc.name}</div>
                  <div className="text-xs text-[#94A3B8]">{doc.pages} 页</div>
                </div>
              </div>
              <div className="space-y-1.5 mb-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#64748B]">包含材料</span>
                  <span className="text-[#1E293B] font-medium">8 份</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#64748B]">审核状态</span>
                  <span className="text-[#16A34A]">已通过</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-[#64748B]">格式</span>
                  <span className="text-[#1E293B]">按招标要求</span>
                </div>
              </div>
              <div className="flex gap-1.5">
                <Button onClick={() => downloadPackage(`${projectName}-${doc.name}.txt`)} size="small" type="primary" block className="text-xs h-7">下载</Button>
                <Button onClick={() => Modal.info({ title: `${doc.name}预览`, width: 620, content: <div className="py-4 text-sm text-[#64748B]"><p className="font-medium text-[#1E293B] mb-2">{projectName}</p><p>已按招标目录生成 {doc.pages} 页演示文档，材料索引、页码和签章位置均已整理。</p></div> })} size="small" block className="text-xs h-7">预览</Button>
              </div>
            </div>
          )
        })}
      </div>

      {/* Version history */}
      <div className="bg-[#F8FAFC] rounded-xl p-4">
        <div className="text-sm font-medium text-[#1E293B] mb-3 flex items-center gap-1.5">
          <History size={15} /> 版本历史
        </div>
        <div className="space-y-2">
          {versions.map((v) => (
            <div key={v.version} className="flex items-start gap-3 bg-white rounded-lg p-3 border border-[#F1F5F9]">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${v.status === 'latest' ? 'bg-[#F0FDF4]' : 'bg-[#F8FAFC]'}`}>
                <FileText size={15} color={v.status === 'latest' ? '#16A34A' : '#94A3B8'} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-[#1E293B] font-mono">{v.version}</span>
                  {v.status === 'latest' && <Tag color="green" className="border-0 rounded text-xs">最新</Tag>}
                  <span className="text-xs text-[#94A3B8]">{v.createdAt}</span>
                </div>
                <div className="text-xs text-[#64748B] mt-0.5">{v.changeSummary}</div>
                <div className="text-xs text-[#94A3B8] mt-0.5">操作人：{v.createdBy}</div>
              </div>
              <div className="flex items-center gap-1">
                {v.status !== 'latest' && <Button onClick={() => rollback(v.version)} size="small" type="text" className="text-xs h-6">回滚</Button>}
                <Button onClick={() => downloadPackage(`${projectName}-${v.version}.txt`)} size="small" type="text" className="text-xs h-6">下载</Button>
                <Button onClick={() => Modal.info({ title: `${v.version} 版本对比`, content: `${v.changeSummary}。与当前版本相比，材料目录与页码有 3 处调整。` })} size="small" type="text" className="text-xs h-6">对比</Button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Requirements Tab
function RequirementsTab() {
  return (
    <div className="pb-4 space-y-4">
      {/* Scoring items */}
      <div>
        <div className="text-sm font-medium text-[#1E293B] mb-3">评分标准</div>
        <div className="space-y-2">
          {tenderRequirements.scoringItems.map((item, i) => (
            <div key={i} className="flex items-center gap-3 bg-[#F8FAFC] rounded-lg p-3">
              <div className="w-12 h-12 rounded-lg bg-white flex flex-col items-center justify-center flex-shrink-0">
                <span className="text-lg font-bold text-[#2563EB]">{item.maxScore}</span>
                <span className="text-xs text-[#94A3B8]">分</span>
              </div>
              <div>
                <div className="text-sm font-medium text-[#1E293B]">{item.item}</div>
                <div className="text-xs text-[#64748B] mt-0.5">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Disqualification items */}
      <div>
        <div className="text-sm font-medium text-[#1E293B] mb-3 flex items-center gap-1.5">
          <AlertCircle size={15} color="#DC2626" /> 废标条款（违反任一条即废标）
        </div>
        <div className="bg-[#FEF2F2] rounded-xl p-4 space-y-2">
          {tenderRequirements.disqualItems.map((item, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-[#1E293B]">
              <span className="text-[#DC2626] font-medium flex-shrink-0">{i + 1}.</span>
              <span>{item}</span>
            </div>
          ))}
        </div>
      </div>

      {/* AI extracted requirements */}
      <div>
        <div className="text-sm font-medium text-[#1E293B] mb-3 flex items-center gap-1.5">
          <Zap size={15} color="#2563EB" /> AI提取的关键要求
        </div>
        <div className="bg-[#EFF6FF] rounded-xl p-4 space-y-2">
          <div className="text-xs text-[#64748B]">以下内容由AI智能体从招标文件中自动提取，请核对确认</div>
          <div className="grid grid-cols-2 gap-3 mt-2">
            <div className="bg-white rounded-lg p-3">
              <div className="text-xs text-[#94A3B8] mb-0.5">预算金额</div>
              <div className="text-sm font-medium text-[#1E293B]">{tenderRequirements.budget}</div>
            </div>
            <div className="bg-white rounded-lg p-3">
              <div className="text-xs text-[#94A3B8] mb-0.5">要求工期</div>
              <div className="text-sm font-medium text-[#1E293B]">{tenderRequirements.duration}</div>
            </div>
            <div className="bg-white rounded-lg p-3">
              <div className="text-xs text-[#94A3B8] mb-0.5">投标保证金</div>
              <div className="text-sm font-medium text-[#1E293B]">50万元</div>
            </div>
            <div className="bg-white rounded-lg p-3">
              <div className="text-xs text-[#94A3B8] mb-0.5">资质等级要求</div>
              <div className="text-sm font-medium text-[#1E293B]">CMMI 3级 + ITSS三级</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
