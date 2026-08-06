import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Tag, Table, Tabs, Progress, Avatar, Tooltip, Alert, Button, Segmented, Timeline, Modal, message, InputNumber, Input } from 'antd'
import {
  ArrowLeft, ShieldCheck, AlertTriangle, FileX2, Bot, UserCheck,
  FileBarChart, CheckCircle2, XCircle, ChevronRight, Gavel, TrendingUp,
  FileCheck2, ScanLine, ClipboardCheck, Upload, DollarSign, History, Bell,
  Clock, Link2, Copy
} from 'lucide-react'
import {
  evalProjectInfo, bidders, materialCheckResults, materialCheckStatusMap,
  disqualificationChecks, disqualResultMap, scoringCriteria, aiScores,
  humanScores, finalResults, evalCategoryLabels, evalWorkflowSteps,
  supplierSubmissions, supplierSubmissionStatusMap, supplierMaterialRecords,
  priceRounds, supplementNotifications, auditTrail,
} from '../mock/evaluationData'
import type { ColumnsType } from 'antd/es/table'
import { useDemo } from '../context/DemoContext'
import { copyText, downloadDemoFile, downloadTableAsCsv } from '../utils/demoActions'

type TabKey = 'submissions' | 'pricing' | 'qualification' | 'technical' | 'commercial' | 'summary' | 'audit'

export default function EvaluationTaskDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { evaluationTasks, updateEvaluationTask } = useDemo()
  const [activeTab, setActiveTab] = useState<TabKey>('submissions')
  const [selectedBidder, setSelectedBidder] = useState('B01')
  const [aiRunning, setAiRunning] = useState(false)
  const [qualificationDecisions, setQualificationDecisions] = useState<Record<string, 'auto' | 'qualified' | 'disqualified'>>({})
  const [scoreEdits, setScoreEdits] = useState<Record<string, number>>({})
  const [commentEdits, setCommentEdits] = useState<Record<string, string>>({})
  const [supplements, setSupplements] = useState<any[]>(supplementNotifications)
  const [rounds, setRounds] = useState<any[]>(priceRounds)
  const task = evaluationTasks.find(item => item.id === id)
  const project = task || evalProjectInfo

  const runAiReview = () => {
    if (!id) return
    setAiRunning(true)
    updateEvaluationTask(id, { status: 'ai_review', currentStep: 4, progress: 60 })
    message.loading({ content: 'AI 正在执行材料完整性、废标项和评分检查…', key: 'eval-ai', duration: 0 })
    window.setTimeout(() => {
      setAiRunning(false)
      updateEvaluationTask(id, { status: 'human_review', currentStep: 4, progress: 80 })
      message.success({ content: 'AI 初审完成，已进入人工复审', key: 'eval-ai' })
      setActiveTab('qualification')
    }, 1600)
  }

  const closeEvaluation = () => {
    if (!id) return
    Modal.confirm({
      title: '确认关闭评标？',
      content: '关闭后供应商提交通道将结束；Demo 中仍可通过重置数据恢复。',
      okText: '确认关闭',
      okButtonProps: { danger: true },
      onOk: () => {
        updateEvaluationTask(id, { status: 'closed', currentStep: 6, progress: 100 })
        message.success('评标已关闭，供应商将看到结束页面')
      },
    })
  }

  const tabItems = [
    { key: 'submissions', label: <span className="flex items-center gap-1.5"><Upload size={15} /> 供应商提交</span> },
    { key: 'pricing', label: <span className="flex items-center gap-1.5"><DollarSign size={15} /> 多轮报价</span> },
    { key: 'qualification', label: <span className="flex items-center gap-1.5"><ShieldCheck size={15} /> 资格审查</span> },
    { key: 'technical', label: <span className="flex items-center gap-1.5"><FileCheck2 size={15} /> 技术评分</span> },
    { key: 'commercial', label: <span className="flex items-center gap-1.5"><TrendingUp size={15} /> 商务评分</span> },
    { key: 'summary', label: <span className="flex items-center gap-1.5"><FileBarChart size={15} /> 综合评标</span> },
    { key: 'audit', label: <span className="flex items-center gap-1.5"><History size={15} /> 操作留痕</span> },
  ]

  return (
    <div className="p-6">
      {/* Back button + title */}
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between mb-4">
        <div className="flex items-center gap-3">
        <Button type="text" icon={<ArrowLeft size={18} />} onClick={() => navigate('/evaluation')} className="!px-2" />
        <div>
          <h2 className="text-lg font-semibold text-[#1E293B]">{project.projectName}</h2>
          <div className="text-xs text-[#64748B] mt-0.5">
            {project.tenderNo} · {project.tenderEntity} · 预算 ¥{project.budget}
          </div>
        </div>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button loading={aiRunning} onClick={runAiReview} icon={<Bot size={14} />}>发起 AI 初审</Button>
          <Button onClick={() => { setActiveTab('pricing'); message.info('可在报价页发起新一轮报价') }} icon={<DollarSign size={14} />}>新一轮报价</Button>
          <Button danger disabled={task?.status === 'closed'} onClick={closeEvaluation} icon={<Gavel size={14} />}>{task?.status === 'closed' ? '评标已关闭' : '关闭评标'}</Button>
        </div>
      </div>

      {/* Workflow steps */}
      <WorkflowSteps currentStep={task?.currentStep || 4} />

      {/* Tabs */}
      <div className="mt-5">
        <Tabs
          activeKey={activeTab}
          onChange={(k) => setActiveTab(k as TabKey)}
          items={tabItems}
        />

        <div className="mt-2">
          {activeTab === 'submissions' && <SubmissionsTab taskId={id || 'EVAL-2026-001'} supplements={supplements} setSupplements={setSupplements} />}
          {activeTab === 'pricing' && <PricingTab rounds={rounds} setRounds={setRounds} />}
          {activeTab === 'qualification' && <QualificationTab selectedBidder={selectedBidder} onBidderChange={setSelectedBidder} decisions={qualificationDecisions} setDecisions={setQualificationDecisions} />}
          {activeTab === 'technical' && <ScoringTab category="technical" selectedBidder={selectedBidder} onBidderChange={setSelectedBidder} scoreEdits={scoreEdits} setScoreEdits={setScoreEdits} commentEdits={commentEdits} setCommentEdits={setCommentEdits} />}
          {activeTab === 'commercial' && <ScoringTab category="commercial" selectedBidder={selectedBidder} onBidderChange={setSelectedBidder} scoreEdits={scoreEdits} setScoreEdits={setScoreEdits} commentEdits={commentEdits} setCommentEdits={setCommentEdits} />}
          {activeTab === 'summary' && <SummaryTab />}
          {activeTab === 'audit' && <AuditTab />}
        </div>
      </div>
    </div>
  )
}

// ===== Workflow Steps =====
function WorkflowSteps({ currentStep }: { currentStep: number }) {
  return (
    <div className="overflow-x-auto bg-white rounded-xl border border-[#E2E8F0] p-4">
      <div className="flex items-center gap-1 min-w-[820px]">
      {evalWorkflowSteps.map((step, idx) => {
        const done = step.step < currentStep
        const current = step.step === currentStep
        const isLast = idx === evalWorkflowSteps.length - 1

        return (
          <div key={step.step} className="flex items-center flex-1">
            <div className="flex flex-col items-center gap-1.5 min-w-[120px]">
              <Tooltip title={step.desc}>
                <div
                  className={`w-9 h-9 rounded-full flex items-center justify-center transition-all ${
                    done ? 'bg-[#16A34A]' : current ? 'bg-[#2563EB] ring-4 ring-[#EFF6FF]' : 'bg-[#F1F5F9]'
                  }`}
                >
                  {done ? (
                    <CheckCircle2 size={18} color="#fff" />
                  ) : current ? (
                    <span className="text-sm font-bold text-white">{step.step}</span>
                  ) : (
                    <span className="text-sm font-medium text-[#94A3B8]">{step.step}</span>
                  )}
                </div>
              </Tooltip>
              <div className="text-center">
                <div className={`text-xs font-medium ${done || current ? 'text-[#1E293B]' : 'text-[#94A3B8]'}`}>
                  {step.title}
                </div>
              </div>
            </div>
            {!isLast && (
              <div className="flex-1 h-0.5 mx-2 rounded-full" style={{ background: done ? '#16A34A' : '#E2E8F0' }} />
            )}
          </div>
        )
      })}
      </div>
    </div>
  )
}

// ===== Bidder Selector =====
function BidderSelector({ selectedBidder, onBidderChange }: { selectedBidder: string; onBidderChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-2 mb-4 overflow-x-auto pb-1">
      <span className="text-xs text-[#64748B] mr-1">投标人：</span>
      {bidders.map(b => {
        const isDisqualified = b.status === 'disqualified'
        return (
          <div
            key={b.id}
            onClick={() => onBidderChange(b.id)}
            className={`px-3 py-1.5 rounded-lg cursor-pointer text-sm transition-all border ${
              selectedBidder === b.id
                ? 'border-[#2563EB] bg-[#EFF6FF] text-[#2563EB] font-medium'
                : 'border-[#E2E8F0] bg-white text-[#475569] hover:border-[#CBD5E1]'
            } ${isDisqualified ? 'opacity-60' : ''}`}
          >
            <span>{b.name}</span>
            {isDisqualified && <Tag color="red" className="!text-xs !ml-1.5 !py-0">废标</Tag>}
          </div>
        )
      })}
    </div>
  )
}

// ===== Qualification Tab =====
function QualificationTab({ selectedBidder, onBidderChange, decisions, setDecisions }: { selectedBidder: string; onBidderChange: (v: string) => void; decisions: Record<string, 'auto' | 'qualified' | 'disqualified'>; setDecisions: React.Dispatch<React.SetStateAction<Record<string, 'auto' | 'qualified' | 'disqualified'>>> }) {
  const manualDecision = decisions[selectedBidder] || 'auto'
  const setManualDecision = (decision: 'auto' | 'qualified' | 'disqualified') => setDecisions(prev => ({ ...prev, [selectedBidder]: decision }))
  const bidderName = bidders.find(b => b.id === selectedBidder)?.name || ''
  const bidderMaterials = materialCheckResults.filter(m => m.bidderId === selectedBidder)
  const bidderDisquals = disqualificationChecks.filter(d => d.bidderId === selectedBidder)

  const providedCount = bidderMaterials.filter(m => m.status === 'provided').length
  const missingCount = bidderMaterials.filter(m => m.status === 'missing').length
  const fakeCount = bidderMaterials.filter(m => m.status === 'fake').length
  const passCount = bidderDisquals.filter(d => d.result === 'pass').length
  const warningCount = bidderDisquals.filter(d => d.result === 'warning').length
  const failCount = bidderDisquals.filter(d => d.result === 'fail').length
  const isDisqualified = manualDecision === 'disqualified' || (manualDecision === 'auto' && failCount > 0)

  const materialColumns: ColumnsType<typeof bidderMaterials[0]> = [
    {
      title: '材料名称',
      dataIndex: 'material',
      key: 'material',
      render: (name: string, record) => (
        <div className="flex items-center gap-2">
          <span className="text-sm text-[#1E293B]">{name}</span>
          {record.required && <Tag className="!text-xs" color="red">必填</Tag>}
        </div>
      ),
    },
    {
      title: '检查结果',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const s = materialCheckStatusMap[status]
        return (
          <div className="flex items-center gap-1.5">
            {status === 'fake' ? <AlertTriangle size={14} color={s.color} /> : null}
            <Tag style={{ color: s.color, background: s.bg, border: 'none' }} className="!text-xs">{s.label}</Tag>
          </div>
        )
      },
    },
    {
      title: '备注',
      dataIndex: 'note',
      key: 'note',
      render: (note: string, record) => (
        <span className={`text-xs ${record.status === 'fake' || record.status === 'missing' ? 'text-[#DC2626]' : 'text-[#64748B]'}`}>
          {note}
        </span>
      ),
    },
  ]

  return (
    <div>
      <BidderSelector selectedBidder={selectedBidder} onBidderChange={onBidderChange} />

      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 bg-white border border-[#E2E8F0] rounded-xl p-3 mb-4">
        <div><p className="text-sm font-medium text-[#1E293B]">人工资格结论</p><p className="text-xs text-[#64748B]">当前：{manualDecision === 'auto' ? '采用 AI 检测结论' : manualDecision === 'qualified' ? '人工确认通过' : '人工确认废标'}</p></div>
        <div className="flex gap-2"><Button onClick={() => { setManualDecision('qualified'); message.success('已人工确认资格通过') }} type={manualDecision === 'qualified' ? 'primary' : 'default'}>确认通过</Button><Button danger onClick={() => { setManualDecision('disqualified'); message.warning('已人工确认废标') }} type={manualDecision === 'disqualified' ? 'primary' : 'default'}>确认废标</Button><Button onClick={() => { setManualDecision('auto'); message.info('已恢复 AI 检测结论') }}>恢复 AI 结论</Button></div>
      </div>

      {/* Disqualification alert */}
      {isDisqualified && (
        <Alert
          type="error"
          showIcon
          icon={<FileX2 size={18} />}
          className="!mb-4 !rounded-xl"
          message={`检测到 ${failCount} 项废标条件，该投标人已触发废标`}
          description={`废标项：${bidderDisquals.filter(d => d.result === 'fail').map(d => d.item).join('、')}`}
        />
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-4">
        {[
          { label: '已提供', value: providedCount, color: '#16A34A', bg: '#F0FDF4', icon: CheckCircle2 },
          { label: '缺失', value: missingCount, color: '#DC2626', bg: '#FEF2F2', icon: XCircle },
          { label: '疑似伪造', value: fakeCount, color: '#DC2626', bg: '#FEF2F2', icon: AlertTriangle },
          { label: '废标检测通过', value: passCount, color: '#16A34A', bg: '#F0FDF4', icon: ShieldCheck },
          { label: '需关注', value: warningCount, color: '#D97706', bg: '#FFFBEB', icon: AlertTriangle },
          { label: '废标', value: failCount, color: '#DC2626', bg: '#FEF2F2', icon: FileX2 },
        ].map(s => {
          const Icon = s.icon
          return (
            <Card key={s.label} className="!border-[#E2E8F0] !shadow-none">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: s.bg }}>
                  <Icon size={15} color={s.color} />
                </div>
                <div>
                  <div className="text-lg font-semibold" style={{ color: s.color }}>{s.value}</div>
                  <div className="text-xs text-[#64748B]">{s.label}</div>
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* AI inspection banner */}
      <div className="flex items-center gap-3 bg-gradient-to-r from-[#EFF6FF] to-[#F5F3FF] rounded-xl border border-[#DBEAFE] p-3 mb-4">
        <div className="w-9 h-9 rounded-lg bg-[#2563EB] flex items-center justify-center flex-shrink-0">
          <ScanLine size={18} color="#fff" />
        </div>
        <div className="flex-1">
          <div className="text-sm font-medium text-[#1E293B]">AI智能审查已完成</div>
          <div className="text-xs text-[#64748B] mt-0.5">
            已对 {bidderName} 的 {bidderMaterials.length} 项材料进行完整性检查，{bidderDisquals.length} 项废标条件检测
          </div>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[#16A34A] font-medium">
          <CheckCircle2 size={14} />
          检测完成
        </div>
      </div>

      {/* Material check table */}
      <Card className="!border-[#E2E8F0] !shadow-none mb-4 overflow-x-auto" title={<span className="text-sm font-semibold flex items-center gap-2"><ClipboardCheck size={16} color="#2563EB" /> 材料完整性检查</span>}>
        <Table
          columns={materialColumns}
          dataSource={bidderMaterials}
          rowKey="id"
          pagination={false}
          size="middle"
          rowClassName={(record) => record.status === 'fake' || record.status === 'missing' ? '!bg-[#FEF2F2]/30' : ''}
        />
      </Card>

      {/* Disqualification checks */}
      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><ShieldCheck size={16} color="#2563EB" /> 废标条件检测</span>}>
        <div className="space-y-2">
          {bidderDisquals.map(check => {
            const r = disqualResultMap[check.result]
            const Icon = check.result === 'pass' ? CheckCircle2 : check.result === 'warning' ? AlertTriangle : FileX2
            return (
              <div
                key={check.id}
                className={`flex items-start gap-3 p-3 rounded-lg border ${
                  check.result === 'fail' ? 'border-[#FECACA] bg-[#FEF2F2]/50' :
                  check.result === 'warning' ? 'border-[#FDE68A] bg-[#FFFBEB]/50' :
                  'border-[#E2E8F0] bg-white'
                }`}
              >
                <Icon size={18} color={r.color} className="mt-0.5 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-sm font-medium text-[#1E293B]">{check.item}</span>
                    <Tag style={{ color: r.color, background: r.bg, border: 'none' }} className="!text-xs">{r.label}</Tag>
                  </div>
                  <div className="text-xs text-[#64748B]">{check.desc}</div>
                </div>
              </div>
            )
          })}
        </div>
      </Card>
    </div>
  )
}

// ===== Scoring Tab (Technical & Commercial) =====
function ScoringTab({ category, selectedBidder, onBidderChange, scoreEdits, setScoreEdits, commentEdits, setCommentEdits }: { category: string; selectedBidder: string; onBidderChange: (v: string) => void; scoreEdits: Record<string, number>; setScoreEdits: React.Dispatch<React.SetStateAction<Record<string, number>>>; commentEdits: Record<string, string>; setCommentEdits: React.Dispatch<React.SetStateAction<Record<string, string>>> }) {
  const criteria = scoringCriteria.filter(c => c.category === category)
  const bidderAiScores = aiScores.filter(s => s.bidderId === selectedBidder && criteria.some(c => c.id === s.criteriaId))
  const bidderHumanScores = humanScores.filter(s => s.bidderId === selectedBidder && criteria.some(c => c.id === s.criteriaId))

  const maxTotal = criteria.reduce((sum, c) => sum + c.maxScore, 0)
  const aiTotal = bidderAiScores.reduce((sum, s) => sum + s.aiScore, 0)
  const scoreKey = (criteriaId: string) => `${selectedBidder}-${criteriaId}`
  const getHumanScore = (criteriaId: string) => scoreEdits[scoreKey(criteriaId)] ?? bidderHumanScores.find(item => item.criteriaId === criteriaId)?.humanScore ?? bidderAiScores.find(item => item.criteriaId === criteriaId)?.aiScore ?? 0
  const humanTotal = criteria.reduce((sum, item) => sum + getHumanScore(item.id), 0)

  const isCommercial = category === 'commercial'

  // Price comparison for commercial tab
  const priceComparison = bidders.map(b => {
    const priceScore = aiScores.find(s => s.bidderId === b.id && s.criteriaId === 'SC01')
    const lowestPrice = Math.min(...bidders.map(bd => parseFloat(bd.quotedPrice.replace(/,/g, ''))))
    const bidderPrice = parseFloat(b.quotedPrice.replace(/,/g, ''))
    const calculatedScore = b.status === 'disqualified' ? 0 : (lowestPrice / bidderPrice) * 30
    return {
      ...b,
      calculatedScore: calculatedScore.toFixed(1),
      aiPriceScore: priceScore?.aiScore || 0,
    }
  })

  const columns: ColumnsType<typeof criteria[0] & { aiScore?: number; aiReason?: string; humanScore?: number; comment?: string; reviewer?: string }> = [
    {
      title: '评分项',
      dataIndex: 'name',
      key: 'name',
      width: 160,
      render: (name: string, record) => (
        <div>
          <div className="text-sm font-medium text-[#1E293B]">{name}</div>
          <div className="text-xs text-[#94A3B8] mt-0.5">{record.method}</div>
        </div>
      ),
    },
    {
      title: '满分',
      dataIndex: 'maxScore',
      key: 'maxScore',
      width: 60,
      render: (score: number) => <span className="text-xs text-[#64748B]">{score}分</span>,
    },
    {
      title: 'AI初评',
      key: 'aiScore',
      width: 90,
      render: (_, record) => {
        const ai = bidderAiScores.find(s => s.criteriaId === record.id)
        if (!ai) return <span className="text-xs text-[#CBD5E1]">--</span>
        return (
          <div className="flex items-center gap-1.5">
            <Bot size={14} color="#7C3AED" />
            <span className="text-sm font-semibold text-[#7C3AED]">{ai.aiScore}</span>
            <span className="text-xs text-[#94A3B8]">/{record.maxScore}</span>
          </div>
        )
      },
    },
    {
      title: 'AI评分依据',
      key: 'aiReason',
      render: (_, record) => {
        const ai = bidderAiScores.find(s => s.criteriaId === record.id)
        if (!ai) return null
        return (
          <div className="text-xs text-[#64748B] leading-relaxed max-w-md">{ai.aiReason}</div>
        )
      },
    },
    {
      title: '人工复审',
      key: 'humanScore',
      width: 90,
      render: (_, record) => {
        const human = bidderHumanScores.find(s => s.criteriaId === record.id)
        const value = getHumanScore(record.id)
        const aiValue = bidderAiScores.find(item => item.criteriaId === record.id)?.aiScore || 0
        const adjusted = value !== aiValue
        return (
          <div className="flex items-center gap-1.5 min-w-[130px]">
            <InputNumber size="small" min={0} max={record.maxScore} step={0.5} value={value} onChange={next => setScoreEdits(prev => ({ ...prev, [scoreKey(record.id)]: next || 0 }))} className="!w-20" />
            {adjusted && <Tag color="orange" className="!text-xs !px-1 !py-0">调整</Tag>}
          </div>
        )
      },
    },
    {
      title: '复审意见',
      key: 'comment',
      width: 200,
      render: (_, record) => {
        const human = bidderHumanScores.find(s => s.criteriaId === record.id)
        const key = scoreKey(record.id)
        const value = commentEdits[key] ?? human?.comment ?? ''
        return (
          <Input size="small" value={value} onChange={event => setCommentEdits(prev => ({ ...prev, [key]: event.target.value }))} placeholder="填写人工复审意见" />
        )
      },
    },
  ]

  return (
    <div>
      <BidderSelector selectedBidder={selectedBidder} onBidderChange={onBidderChange} />

      {/* Score summary */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-3 mb-4">
        <Card className="!border-[#E2E8F0] !shadow-none">
          <div className="text-xs text-[#64748B] mb-1">评分项数</div>
          <div className="text-2xl font-semibold text-[#1E293B]">{criteria.length}<span className="text-sm text-[#94A3B8] ml-1">项</span></div>
        </Card>
        <Card className="!border-[#E2E8F0] !shadow-none">
          <div className="text-xs text-[#64748B] mb-1">满分</div>
          <div className="text-2xl font-semibold text-[#1E293B]">{maxTotal}<span className="text-sm text-[#94A3B8] ml-1">分</span></div>
        </Card>
        <Card className="!border-[#E2E8F0] !shadow-none">
          <div className="text-xs text-[#64748B] mb-1 flex items-center gap-1"><Bot size={12} color="#7C3AED" /> AI初评总分</div>
          <div className="text-2xl font-semibold text-[#7C3AED]">{aiTotal.toFixed(1)}<span className="text-sm text-[#94A3B8] ml-1">分</span></div>
        </Card>
        <Card className="!border-[#E2E8F0] !shadow-none">
          <div className="text-xs text-[#64748B] mb-1 flex items-center gap-1"><UserCheck size={12} color="#16A34A" /> 人工复审总分</div>
          <div className="text-2xl font-semibold text-[#16A34A]">{humanTotal.toFixed(1)}<span className="text-sm text-[#94A3B8] ml-1">分</span></div>
        </Card>
      </div>

      {/* Price comparison for commercial */}
      {isCommercial && (
        <Card className="!border-[#E2E8F0] !shadow-none mb-4" title={<span className="text-sm font-semibold flex items-center gap-2"><TrendingUp size={16} color="#2563EB" /> 报价对比（最低价得分法）</span>}>
          <Table
            dataSource={priceComparison}
            rowKey="id"
            pagination={false}
            size="middle"
            columns={[
              {
                title: '投标人',
                dataIndex: 'name',
                key: 'name',
                render: (name: string, record) => (
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-[#1E293B]">{name}</span>
                    {record.status === 'disqualified' && <Tag color="red" className="!text-xs">废标</Tag>}
                  </div>
                ),
              },
              {
                title: '投标报价',
                dataIndex: 'quotedPrice',
                key: 'quotedPrice',
                render: (price: string) => <span className="text-sm font-medium text-[#1E293B]">¥{price}</span>,
              },
              {
                title: '与最低价差额',
                key: 'diff',
                render: (_, record) => {
                  const lowest = Math.min(...bidders.map(b => parseFloat(b.quotedPrice.replace(/,/g, ''))))
                  const diff = parseFloat(record.quotedPrice.replace(/,/g, '')) - lowest
                  if (diff === 0) return <Tag color="green" className="!text-xs">最低价</Tag>
                  return <span className="text-xs text-[#DC2626]">+¥{diff.toLocaleString()}</span>
                },
              },
              {
                title: '计算得分',
                dataIndex: 'calculatedScore',
                key: 'calculatedScore',
                render: (score: string, record) => (
                  <span className={`text-sm font-semibold ${record.status === 'disqualified' ? 'text-[#94A3B8]' : 'text-[#2563EB]'}`}>
                    {record.status === 'disqualified' ? '0.0' : score}
                  </span>
                ),
              },
              {
                title: 'AI评分',
                dataIndex: 'aiPriceScore',
                key: 'aiPriceScore',
                render: (score: number) => <span className="text-sm text-[#7C3AED]">{score}</span>,
              },
            ]}
          />
        </Card>
      )}

      {/* Scoring table */}
      <Card className="!border-[#E2E8F0] !shadow-none overflow-x-auto" title={<span className="text-sm font-semibold flex items-center gap-2"><FileCheck2 size={16} color="#2563EB" /> {evalCategoryLabels[category]}评分明细</span>} extra={<Button type="primary" size="small" onClick={() => message.success(`${evalCategoryLabels[category]}人工复审评分已保存`)}>保存复审</Button>}>
        <Table
          columns={columns}
          dataSource={criteria as any}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      </Card>
    </div>
  )
}

// ===== Summary Tab =====
function SummaryTab() {
  const sortedResults = [...finalResults].sort((a, b) => b.totalScore - a.totalScore)

  const summaryColumns: ColumnsType<typeof finalResults[0]> = [
    {
      title: '排名',
      dataIndex: 'ranking',
      key: 'ranking',
      width: 60,
      render: (rank: number, record) => {
        if (record.status === 'disqualified') return <span className="text-xs text-[#94A3B8]">--</span>
        const colors = ['#D97706', '#94A3B8', '#B45309']
        return (
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-sm font-bold" style={{ background: colors[rank - 1] || '#E2E8F0', color: '#fff' }}>
            {rank}
          </div>
        )
      },
    },
    {
      title: '投标人',
      dataIndex: 'bidderName',
      key: 'bidderName',
      render: (name: string, record) => (
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-[#1E293B]">{name}</span>
          {record.status === 'recommended' && <Tag color="green" className="!text-xs">推荐中标</Tag>}
          {record.status === 'candidate' && <Tag color="blue" className="!text-xs">候选</Tag>}
          {record.status === 'disqualified' && <Tag color="red" className="!text-xs">废标</Tag>}
        </div>
      ),
    },
    {
      title: '投标报价',
      dataIndex: 'quotedPrice',
      key: 'quotedPrice',
      render: (price: string) => <span className="text-sm text-[#475569]">¥{price}</span>,
    },
    {
      title: '商务标',
      dataIndex: 'priceScore',
      key: 'priceScore',
      width: 80,
      render: (score: number) => <ScoreCell score={score} max={35} />,
    },
    {
      title: '技术标',
      dataIndex: 'technicalScore',
      key: 'technicalScore',
      width: 80,
      render: (score: number) => <ScoreCell score={score} max={40} />,
    },
    {
      title: '资质标',
      dataIndex: 'qualificationScore',
      key: 'qualificationScore',
      width: 80,
      render: (score: number) => <ScoreCell score={score} max={25} />,
    },
    {
      title: '售后',
      dataIndex: 'serviceScore',
      key: 'serviceScore',
      width: 80,
      render: (score: number) => <ScoreCell score={score} max={5} />,
    },
    {
      title: 'AI总分',
      dataIndex: 'aiTotalScore',
      key: 'aiTotalScore',
      width: 80,
      render: (score: number) => <span className="text-sm text-[#7C3AED] font-medium">{score.toFixed(1)}</span>,
    },
    {
      title: '最终得分',
      dataIndex: 'totalScore',
      key: 'totalScore',
      width: 100,
      render: (score: number, record) => {
        if (record.status === 'disqualified') return <span className="text-sm text-[#94A3B8]">0.0</span>
        const percent = (score / 100) * 100
        return (
          <div className="flex items-center gap-2">
            <div className="w-12">
              <Progress percent={percent} size="small" strokeColor={score >= 85 ? '#16A34A' : score >= 70 ? '#2563EB' : '#D97706'} showInfo={false} />
            </div>
            <span className={`text-sm font-bold ${score >= 85 ? 'text-[#16A34A]' : score >= 70 ? 'text-[#2563EB]' : 'text-[#D97706]'}`}>
              {score.toFixed(1)}
            </span>
          </div>
        )
      },
    },
  ]

  return (
    <div>
      {/* Evaluation conclusion banner */}
      <div className="flex items-center gap-4 bg-gradient-to-r from-[#EFF6FF] to-[#F0FDF4] rounded-xl border border-[#DBEAFE] p-4 mb-4">
        <div className="w-12 h-12 rounded-xl bg-[#2563EB] flex items-center justify-center flex-shrink-0">
          <Gavel size={24} color="#fff" />
        </div>
        <div className="flex-1">
          <div className="text-sm font-semibold text-[#1E293B]">评标结论</div>
          <div className="text-xs text-[#64748B] mt-0.5">
            共 {bidders.length} 家投标人参与评审，{bidders.filter(b => b.status !== 'disqualified').length} 家通过资格审查，{bidders.filter(b => b.status === 'disqualified').length} 家触发废标。
            推荐中标候选人：<span className="font-semibold text-[#16A34A]">{sortedResults.find(r => r.status !== 'disqualified')?.bidderName}</span>
          </div>
        </div>
        <Button type="primary" onClick={() => downloadDemoFile('综合评标报告.txt', `综合评标报告\n\n项目：${evalProjectInfo.projectName}\n推荐中标候选人：${sortedResults.find(r => r.status !== 'disqualified')?.bidderName}\n\n本文件用于演示评标报告生成与下载流程。`)} icon={<FileBarChart size={15} />}>生成评标报告</Button>
      </div>

      {/* Score comparison cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        {sortedResults.map(result => {
          const isDisqualified = result.status === 'disqualified'
          const isRecommended = result.status === 'recommended'
          return (
            <Card
              key={result.bidderId}
              className={`!shadow-none !border-2 ${isRecommended ? '!border-[#16A34A]' : isDisqualified ? '!border-[#FECACA]' : '!border-[#E2E8F0]'}`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  {isRecommended && <div className="w-7 h-7 rounded-full bg-[#D97706] flex items-center justify-center text-white text-xs font-bold">1</div>}
                  {!isRecommended && !isDisqualified && <div className="w-7 h-7 rounded-full bg-[#94A3B8] flex items-center justify-center text-white text-xs font-bold">2</div>}
                  {isDisqualified && <div className="w-7 h-7 rounded-full bg-[#DC2626] flex items-center justify-center"><XCircle size={16} color="#fff" /></div>}
                </div>
                {isRecommended && <Tag color="green" className="!text-xs">推荐中标</Tag>}
                {isDisqualified && <Tag color="red" className="!text-xs">废标</Tag>}
              </div>

              <div className="text-sm font-medium text-[#1E293B] mb-1">{result.bidderName}</div>
              <div className="text-xs text-[#94A3B8] mb-3">报价 ¥{result.quotedPrice}</div>

              {isDisqualified ? (
                <div className="text-center py-2">
                  <div className="text-3xl font-bold text-[#94A3B8]">0.0</div>
                  <div className="text-xs text-[#94A3B8] mt-1">已废标</div>
                </div>
              ) : (
                <div className="text-center py-2">
                  <div className={`text-3xl font-bold ${isRecommended ? 'text-[#16A34A]' : 'text-[#2563EB]'}`}>
                    {result.totalScore.toFixed(1)}
                  </div>
                  <div className="text-xs text-[#64748B] mt-1">综合得分 / 100</div>
                </div>
              )}

              <div className="mt-3 pt-3 border-t border-[#F1F5F9]">
                <div className="text-xs text-[#64748B] leading-relaxed line-clamp-3">{result.conclusion}</div>
              </div>
            </Card>
          )
        })}
      </div>

      {/* Detailed comparison table */}
      <Card className="!border-[#E2E8F0] !shadow-none overflow-x-auto" title={<span className="text-sm font-semibold flex items-center gap-2"><FileBarChart size={16} color="#2563EB" /> 综合评分对比表</span>}>
        <Table
          columns={summaryColumns}
          dataSource={sortedResults}
          rowKey="bidderId"
          pagination={false}
          size="middle"
          rowClassName={(record) => record.status === 'disqualified' ? '!opacity-60' : ''}
        />
      </Card>

      {/* Scoring method */}
      <Card className="!border-[#E2E8F0] !shadow-none mt-4" title={<span className="text-sm font-semibold flex items-center gap-2"><ClipboardCheck size={16} color="#2563EB" /> 评分办法</span>}>
        <div className="space-y-2">
          {scoringCriteria.map(c => (
            <div key={c.id} className="flex items-center gap-3 py-1.5 border-b border-[#F1F5F9] last:border-0">
              <Tag className="!text-xs !min-w-[60px] !text-center" color={
                c.category === 'commercial' ? 'blue' :
                c.category === 'technical' ? 'purple' :
                c.category === 'qualification' ? 'green' : 'orange'
              }>
                {evalCategoryLabels[c.category]}
              </Tag>
              <span className="text-sm text-[#1E293B] flex-1">{c.name}</span>
              <span className="text-xs text-[#94A3B8]">{c.method}</span>
              <span className="text-sm font-medium text-[#1E293B] w-12 text-right">{c.maxScore}分</span>
            </div>
          ))}
          <div className="flex items-center justify-between pt-2">
            <span className="text-sm font-medium text-[#1E293B]">总分</span>
            <span className="text-sm font-bold text-[#1E293B]">100分</span>
          </div>
        </div>
      </Card>
    </div>
  )
}

function ScoreCell({ score, max }: { score: number; max: number }) {
  if (score === 0) return <span className="text-sm text-[#94A3B8]">0</span>
  const percent = (score / max) * 100
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-sm font-medium text-[#1E293B]">{score}</span>
      <span className="text-xs text-[#94A3B8]">/{max}</span>
    </div>
  )
}

// ===== Submissions Tab (供应商提交) =====
function SubmissionsTab({ taskId, supplements, setSupplements }: { taskId: string; supplements: any[]; setSupplements: React.Dispatch<React.SetStateAction<any[]>> }) {
  const [selectedSupplier, setSelectedSupplier] = useState('S01')

  const supplierPortalLink = (supplierId: string) => {
    const token = window.btoa(`${taskId}:${supplierId}:demo`).replace(/=/g, '')
    return `${window.location.origin}/evaluation/portal/${taskId}?supplier=${supplierId}&token=${token}`
  }

  const copySupplierLink = async (supplier: any) => {
    await copyText(supplierPortalLink(supplier.supplierId))
    message.success(`${supplier.supplierName} 的专属邀请链接已复制`)
  }

  const sendSupplement = (supplier: any) => {
    Modal.confirm({
      title: `向 ${supplier.supplierName} 发送补充通知？`,
      content: `系统将通知其补充 ${supplier.missingCount} 项缺失材料，限时 90 分钟。`,
      okText: '发送通知',
      onOk: () => {
        setSupplements(prev => [{ id: `SN-${Date.now()}`, supplierId: supplier.supplierId, supplierName: supplier.supplierName, missingMaterials: ['待补充材料'], sentTime: new Date().toLocaleString('zh-CN', { hour12: false }), deadline: '90 分钟后', status: 'sent', note: '人工发起的限时补充通知' }, ...prev])
        message.success('补充通知已发送并记录留痕')
      },
    })
  }

  const supplierCols: ColumnsType<any> = [
    { title: '供应商', dataIndex: 'supplierName', width: 200, render: (v: string) => <span className="font-medium text-[#1E293B]">{v}</span> },
    { title: '联系人', dataIndex: 'contact', width: 80 },
    { title: '联系电话', dataIndex: 'phone', width: 120 },
    { title: '提交状态', dataIndex: 'status', width: 100, render: (v: string) => {
      const s = supplierSubmissionStatusMap[v]
      return <Tag color={s?.color === '#16A34A' ? 'green' : s?.color === '#DC2626' ? 'red' : s?.color === '#D97706' ? 'orange' : 'blue'}>{s?.label}</Tag>
    }},
    { title: '材料', width: 100, render: (_: any, r: any) => (
      <span className="text-sm">
        <span className="text-[#16A34A] font-medium">{r.materialCount}</span>
        <span className="text-[#94A3B8]"> / {r.requiredCount}</span>
        {r.missingCount > 0 && <span className="text-[#DC2626] ml-1">(-{r.missingCount})</span>}
      </span>
    )},
    { title: '报价轮次', dataIndex: 'priceRound', width: 80, render: (v: number) => <Tag>{v}轮</Tag> },
    { title: '当前报价', dataIndex: 'currentPrice', width: 140, render: (v: string) => <span className="font-medium text-[#2563EB]">¥{v}</span> },
    { title: '提交时间', dataIndex: 'submitTime', width: 160, render: (v: string) => <span className="text-xs text-[#64748B]">{v}</span> },
    { title: '邀请入口', width: 130, render: (_: any, r: any) => (
      <Button type="link" size="small" icon={<Link2 size={13} />} className="!px-0" onClick={(event) => { event.stopPropagation(); copySupplierLink(r) }}>复制专属链接</Button>
    )},
    { title: '操作', width: 160, render: (_: any, r: any) => (
      <div className="flex items-center gap-2">
        <Button type="link" size="small" className="!px-0" onClick={() => setSelectedSupplier(r.supplierId)}>查看材料</Button>
        {r.missingCount > 0 && r.status !== 'overdue' && (
          <Button onClick={(event) => { event.stopPropagation(); sendSupplement(r) }} type="link" size="small" className="!px-0 !text-[#EA580C]">发补充通知</Button>
        )}
      </div>
    )},
  ]

  const supplierMaterials = supplierMaterialRecords.filter(m => m.supplierId === selectedSupplier)
  const currentSupplier = supplierSubmissions.find(s => s.supplierId === selectedSupplier)

  const materialCols: ColumnsType<any> = [
    { title: '材料名称', dataIndex: 'material', width: 200, render: (v: string) => <span className="font-medium text-[#1E293B]">{v}</span> },
    { title: '文件名', dataIndex: 'fileName', width: 200, render: (v: string, record: any) => v ? <button onClick={() => Modal.info({ title: record.material, content: `文件：${v}\n提交时间：${record.submitTime}` })} className="text-sm text-[#2563EB] hover:underline">{v}</button> : <span className="text-[#94A3B8]">—</span> },
    { title: '大小', dataIndex: 'fileSize', width: 80, render: (v: string) => v || '—' },
    { title: '提交时间', dataIndex: 'submitTime', width: 160, render: (v: string) => <span className="text-xs text-[#64748B]">{v || '—'}</span> },
    { title: '轮次', dataIndex: 'round', width: 60, render: (v: number) => <Tag>第{v}轮</Tag> },
    { title: '状态', dataIndex: 'status', width: 100, render: (v: string) => {
      const s = materialCheckStatusMap[v] || supplierSubmissionStatusMap[v]
      return s ? <Tag color={s.color === '#16A34A' ? 'green' : s.color === '#DC2626' ? 'red' : 'blue'}>{s.label}</Tag> : <Tag>{v}</Tag>
    }},
    { title: '备注', dataIndex: 'note', render: (v: string) => v ? <span className="text-xs text-[#EA580C]">{v}</span> : '—' },
  ]

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Card size="small" className="!border-[#E2E8F0] !shadow-none !rounded-lg" styles={{ body: { padding: 14 } }}>
          <div className="flex items-center gap-2 mb-1"><Upload size={15} className="text-[#2563EB]" /><span className="text-xs text-[#64748B]">已提交</span></div>
          <p className="text-xl font-bold text-[#1E293B]">{supplierSubmissions.filter(s => s.status === 'submitted').length}</p>
        </Card>
        <Card size="small" className="!border-[#E2E8F0] !shadow-none !rounded-lg" styles={{ body: { padding: 14 } }}>
          <div className="flex items-center gap-2 mb-1"><AlertTriangle size={15} className="text-[#D97706]" /><span className="text-xs text-[#64748B]">部分提交</span></div>
          <p className="text-xl font-bold text-[#D97706]">{supplierSubmissions.filter(s => s.status === 'partial' || s.status === 'supplementing').length}</p>
        </Card>
        <Card size="small" className="!border-[#E2E8F0] !shadow-none !rounded-lg" styles={{ body: { padding: 14 } }}>
          <div className="flex items-center gap-2 mb-1"><Bell size={15} className="text-[#EA580C]" /><span className="text-xs text-[#64748B]">补充通知</span></div>
          <p className="text-xl font-bold text-[#EA580C]">{supplements.length}</p>
        </Card>
        <Card size="small" className="!border-[#E2E8F0] !shadow-none !rounded-lg" styles={{ body: { padding: 14 } }}>
          <div className="flex items-center gap-2 mb-1"><Clock size={15} className="text-[#16A34A]" /><span className="text-xs text-[#64748B]">材料记录</span></div>
          <p className="text-xl font-bold text-[#1E293B]">{supplierMaterialRecords.length}</p>
        </Card>
      </div>

      {/* Supplier submissions table */}
      <Card className="!border-[#E2E8F0] !shadow-none overflow-x-auto" styles={{ body: { padding: 0 } }}>
        <div className="px-4 pt-4 pb-2 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-[#1E293B]">供应商提交状态</h3>
            <p className="text-xs text-[#64748B] mt-1">外发时请使用每行的专属邀请链接；统一入口仅用于内部切换视角演示。</p>
          </div>
          <div className="flex items-center gap-2">
            <Button size="small" onClick={async () => { await copyText(`${window.location.origin}/evaluation/portal/${taskId}`); message.success('统一演示入口已复制') }} className="!rounded-lg" icon={<Link2 size={13} />}>复制统一演示入口</Button>
          </div>
        </div>
        <Table
          dataSource={supplierSubmissions}
          columns={supplierCols}
          rowKey="supplierId"
          size="middle"
          pagination={false}
          onRow={(r) => ({ onClick: () => setSelectedSupplier(r.supplierId), className: 'cursor-pointer' })}
        />
      </Card>

      {/* Selected supplier materials */}
      {currentSupplier && (
        <Card className="!border-[#E2E8F0] !shadow-none overflow-x-auto" styles={{ body: { padding: 16 } }}>
          <div className="flex items-center gap-2 mb-3">
            <FileCheck2 size={16} className="text-[#2563EB]" />
            <h3 className="text-sm font-semibold text-[#1E293B]">{currentSupplier.supplierName} - 提交材料明细</h3>
            <span className="text-xs text-[#64748B]">（全部留痕记录）</span>
          </div>
          <Table
            dataSource={supplierMaterials}
            columns={materialCols}
            rowKey="id"
            size="middle"
            pagination={false}
          />
        </Card>
      )}

      {/* Supplement notifications */}
      <Card className="!border-[#EA580C] !shadow-none" styles={{ body: { padding: 16 } }}>
        <div className="flex items-center gap-2 mb-3">
          <Bell size={16} className="text-[#EA580C]" />
          <h3 className="text-sm font-semibold text-[#1E293B]">材料补充通知记录</h3>
        </div>
        <div className="space-y-2">
          {supplements.map(sn => (
            <div key={sn.id} className="flex items-center gap-3 p-3 bg-[#FFFBEB] rounded-lg">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${sn.status === 'expired' ? 'bg-[#FEE2E2]' : sn.status === 'responded' ? 'bg-[#F0FDF4]' : 'bg-[#FFFBEB]'}`}>
                {sn.status === 'expired' ? <XCircle size={16} className="text-[#DC2626]" /> :
                 sn.status === 'responded' ? <CheckCircle2 size={16} className="text-[#16A34A]" /> :
                 <Bell size={16} className="text-[#EA580C]" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-[#1E293B]">
                  <span className="font-medium">{sn.supplierName}</span> - 缺失：{sn.missingMaterials.join('、')}
                </p>
                <p className="text-xs text-[#64748B] mt-0.5">{sn.note}</p>
              </div>
              <div className="text-right flex-shrink-0 text-xs">
                <p className="text-[#64748B]">发送：{sn.sentTime.slice(11)}</p>
                <p className="text-[#DC2626]">截止：{sn.deadline.slice(11)}</p>
              </div>
              <div>
                {sn.status === 'sent' && <Tag color="orange">待响应</Tag>}
                {sn.status === 'expired' && <Tag color="red">已超时</Tag>}
                {sn.status === 'responded' && <Tag color="green">已响应</Tag>}
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}

// ===== Pricing Tab (多轮报价) =====
function PricingTab({ rounds, setRounds }: { rounds: any[]; setRounds: React.Dispatch<React.SetStateAction<any[]>> }) {
  const startRound = () => {
    const roundNumber = rounds.length + 1
    setRounds(prev => [...prev.map(item => ({ ...item, status: 'completed' })), {
      round: roundNumber,
      title: `第 ${roundNumber} 轮报价（Demo）`,
      startTime: new Date().toLocaleString('zh-CN', { hour12: false }),
      deadline: '60 分钟后',
      status: 'active',
      suppliers: supplierSubmissions.map(item => ({ supplierId: item.supplierId, supplierName: item.supplierName, price: '—', submitTime: '', isLowest: false, note: '等待供应商报价' })),
    }])
    message.success(`第 ${roundNumber} 轮报价已开启，供应商入口同步更新`)
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end"><Button type="primary" onClick={startRound} icon={<DollarSign size={14} />}>发起新一轮报价</Button></div>
      <Alert
        type="info"
        showIcon
        message={`本项目采用竞争性谈判方式，当前共 ${rounds.length} 轮报价`}
        description="每轮报价截止后系统自动关闭报价通道，供应商需在规定时间内提交报价"
        className="!rounded-lg"
      />

      {rounds.map(round => (
        <Card key={round.round} className="!border-[#E2E8F0] !shadow-none overflow-x-auto" styles={{ body: { padding: 20 } }}>
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${round.status === 'completed' ? 'bg-[#F0FDF4]' : 'bg-[#EFF6FF]'}`}>
                <span className={`text-sm font-bold ${round.status === 'completed' ? 'text-[#16A34A]' : 'text-[#2563EB]'}`}>{round.round}</span>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-[#1E293B]">{round.title}</h3>
                <p className="text-xs text-[#64748B]">{round.startTime} ~ {round.deadline}</p>
              </div>
            </div>
            {round.status === 'completed' ? <Tag color="green">已完成</Tag> : <Tag color="blue">进行中</Tag>}
          </div>

          <Table
            dataSource={round.suppliers}
            rowKey="supplierId"
            size="middle"
            pagination={false}
            columns={[
              { title: '供应商', dataIndex: 'supplierName', width: 200, render: (v: string) => <span className="font-medium text-[#1E293B]">{v}</span> },
              { title: '报价（元）', dataIndex: 'price', width: 180, render: (v: string, r: any) => (
                <div className="flex items-center gap-2">
                  {v !== '—' ? <span className="text-base font-bold text-[#2563EB]">¥{v}</span> : <span className="text-[#94A3B8]">—</span>}
                  {r.isLowest && v !== '—' && <Tag color="green">最低价</Tag>}
                </div>
              )},
              { title: '提交时间', dataIndex: 'submitTime', width: 160, render: (v: string) => <span className="text-xs text-[#64748B]">{v || '—'}</span> },
              { title: '备注', dataIndex: 'note', render: (v: string) => v ? <span className="text-xs text-[#EA580C]">{v}</span> : '—' },
            ]}
          />
        </Card>
      ))}

      {/* Price comparison */}
      <Card className="!border-[#E2E8F0] !shadow-none" styles={{ body: { padding: 20 } }}>
        <div className="flex items-center gap-2 mb-4">
          <TrendingUp size={16} className="text-[#2563EB]" />
          <h3 className="text-sm font-semibold text-[#1E293B]">报价趋势对比</h3>
        </div>
        <Table
          dataSource={[
            { key: '1', supplier: '深圳智联科技', round1: '12,800,000', round2: '12,500,000', change: '-300,000', changeRate: '-2.3%' },
            { key: '2', supplier: '广州云图信息', round1: '11,950,000', round2: '11,800,000', change: '-150,000', changeRate: '-1.3%' },
            { key: '3', supplier: '上海数擎科技', round1: '12,300,000', round2: '12,000,000', change: '-300,000', changeRate: '-2.4%' },
            { key: '4', supplier: '北京华信科技', round1: '13,200,000', round2: '—', change: '未参与', changeRate: '-' },
          ]}
          size="middle"
          pagination={false}
          columns={[
            { title: '供应商', dataIndex: 'supplier', width: 180, render: (v: string) => <span className="font-medium text-[#1E293B]">{v}</span> },
            { title: '首轮报价', dataIndex: 'round1', width: 150, render: (v: string) => <span className="text-[#1E293B]">¥{v}</span> },
            { title: '二轮报价', dataIndex: 'round2', width: 150, render: (v: string) => v !== '—' ? <span className="font-medium text-[#2563EB]">¥{v}</span> : <span className="text-[#94A3B8]">—</span> },
            { title: '降价金额', dataIndex: 'change', width: 120, render: (v: string) => v.startsWith('-') ? <span className="text-[#16A34A]">{v}</span> : <span className="text-[#94A3B8]">{v}</span> },
            { title: '降幅', dataIndex: 'changeRate', width: 100, render: (v: string) => v.startsWith('-') ? <span className="text-[#16A34A]">{v}</span> : <span className="text-[#94A3B8]">{v}</span> },
          ]}
        />
      </Card>
    </div>
  )
}

// ===== Audit Tab (操作留痕) =====
function AuditTab() {
  const actionColorMap: Record<string, string> = {
    '创建评标任务': 'blue',
    '发布评标页面': 'blue',
    '提交材料': 'green',
    '提交报价': 'green',
    '发送补充通知': 'orange',
    '提交截止': 'red',
    '报价截止': 'red',
    '补充通知过期': 'red',
    'AI材料审查': 'blue',
    'AI初审启动': 'blue',
    '发起二次报价': 'blue',
  }

  const roleColorMap: Record<string, string> = {
    '评标管理员': '#2563EB',
    '供应商': '#16A34A',
    'AI': '#8B5CF6',
  }

  return (
    <div className="space-y-4">
      <Alert
        type="info"
        showIcon
        message="全程操作留痕"
        description="所有供应商提交、管理员操作、AI自动处理均记录在案，不可篡改，供审计追溯"
        className="!rounded-lg"
      />

      <Card className="!border-[#E2E8F0] !shadow-none overflow-x-auto" styles={{ body: { padding: 24 } }}>
        <div className="flex items-center justify-between gap-2 mb-4">
          <div className="flex items-center gap-2"><History size={18} className="text-[#2563EB]" /><h3 className="text-base font-semibold text-[#1E293B]">操作日志（{auditTrail.length}条）</h3></div>
          <Button size="small" onClick={() => downloadTableAsCsv('评标操作留痕.csv', ['时间', '操作人', '角色', '操作', '对象', '详情', 'IP'], auditTrail.map(row => [row.time, row.operator, row.role, row.action, row.target, row.detail, row.ip]))}>导出日志</Button>
        </div>

        <Table
          dataSource={auditTrail}
          rowKey="id"
          size="middle"
          pagination={{ pageSize: 15, showSizeChanger: false }}
          columns={[
            { title: '时间', dataIndex: 'time', width: 160, render: (v: string) => <span className="text-xs text-[#64748B] font-mono">{v}</span> },
            { title: '操作人', dataIndex: 'operator', width: 140, render: (v: string, r: any) => (
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-[#1E293B]">{v}</span>
                <Tag style={{ color: roleColorMap[r.role], borderColor: roleColorMap[r.role], fontSize: 10, lineHeight: '16px', padding: '0 4px' }}>{r.role}</Tag>
              </div>
            )},
            { title: '操作', dataIndex: 'action', width: 140, render: (v: string) => <Tag color={actionColorMap[v] || 'default'}>{v}</Tag> },
            { title: '操作对象', dataIndex: 'target', width: 160, render: (v: string) => <span className="text-sm text-[#475569]">{v}</span> },
            { title: '详情', dataIndex: 'detail', render: (v: string) => <span className="text-xs text-[#64748B]">{v}</span> },
            { title: 'IP', dataIndex: 'ip', width: 120, render: (v: string) => <span className="text-xs text-[#94A3B8] font-mono">{v}</span> },
          ]}
        />
      </Card>
    </div>
  )
}
