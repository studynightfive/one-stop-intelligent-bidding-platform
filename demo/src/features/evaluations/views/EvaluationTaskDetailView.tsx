import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Alert, Button, Card, Empty, Input, InputNumber, Modal, Progress, Select, Space, Table, Tabs, Tag, Timeline, message } from 'antd'
import {
  ArrowLeft,
  Bell,
  Bot,
  CheckCircle2,
  Clock,
  Copy,
  DollarSign,
  Download,
  FileBarChart,
  FileCheck2,
  Gavel,
  History,
  RefreshCw,
  ShieldCheck,
  TrendingUp,
  Upload,
} from 'lucide-react'
import dayjs from 'dayjs'
import { useDemo } from '../../../context/DemoContext'
import { shouldUseMocks } from '../../../api/runtime'
import { copyText, downloadDemoFile } from '../../../utils/demoActions'
import { EVAL_STATUS_META, EVAL_TEST_IDS } from '../constants'
import {
  closeEvaluation,
  closePriceRound,
  confirmScores,
  createEvaluationReport,
  createPriceRound,
  createSupplementNotice,
  decideRisk,
  downloadEvaluationReport,
  fetchEvaluationAuditEvents,
  fetchEvaluationDetail,
  fetchEvaluationReports,
  fetchLatestMaterialCheck,
  fetchPriceComparison,
  fetchPriceRounds,
  fetchRanking,
  fetchRisks,
  fetchScores,
  fetchSupplierInvites,
  fetchSupplierSubmissions,
  fetchSupplementNotices,
  revokeSupplierInvite,
  rotateSupplierInvite,
  startAiScoring,
  startMaterialCheck,
  startRiskCheck,
  updateScore,
  type AuditEvent,
  type EvaluationRanking,
  type EvaluationReport,
  type EvaluationTaskDetail,
  type MaterialCheckResult,
  type PriceComparison,
  type PriceRound,
  type RiskFinding,
  type ScoreItem,
  type SupplierInviteSummary,
  type SupplierSubmission,
  type SupplementNotice,
} from '../api'

type TabKey = 'submissions' | 'pricing' | 'qualification' | 'technical' | 'commercial' | 'summary' | 'audit'

function saveBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  anchor.click()
  URL.revokeObjectURL(url)
}

export default function EvaluationTaskDetailView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { evaluationTasks, updateEvaluationTask } = useDemo()
  const mockMode = shouldUseMocks() || !id
  const evaluationId = id || evaluationTasks[0]?.id || 'EVAL-2026-001'
  const [activeTab, setActiveTab] = useState<TabKey>('submissions')
  const [detail, setDetail] = useState<EvaluationTaskDetail | null>(() => mockMode ? buildMockDetail(evaluationId, evaluationTasks[0]) : null)
  const [invites, setInvites] = useState<SupplierInviteSummary[]>([])
  const [notices, setNotices] = useState<SupplementNotice[]>([])
  const [rounds, setRounds] = useState<PriceRound[]>([])
  const [comparison, setComparison] = useState<PriceComparison | null>(null)
  const [materialCheck, setMaterialCheck] = useState<MaterialCheckResult | null>(null)
  const [risks, setRisks] = useState<RiskFinding[]>([])
  const [scores, setScores] = useState<ScoreItem[]>([])
  const [ranking, setRanking] = useState<EvaluationRanking | null>(null)
  const [reports, setReports] = useState<EvaluationReport[]>([])
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [loading, setLoading] = useState(!mockMode)
  const [actionLoading, setActionLoading] = useState('')
  const [error, setError] = useState('')
  const [roundOpen, setRoundOpen] = useState(false)
  const [roundDraft, setRoundDraft] = useState({ title: '新一轮报价', opensAt: dayjs().format('YYYY-MM-DDTHH:mm'), deadline: dayjs().add(1, 'day').format('YYYY-MM-DDTHH:mm'), rankingVisibleToSupplier: false })
  const [submissionSupplier, setSubmissionSupplier] = useState<string | null>(null)
  const [submissions, setSubmissions] = useState<SupplierSubmission[]>([])
  const [scoreDrafts, setScoreDrafts] = useState<Record<string, { value: string; reason: string }>>({})

  const load = useCallback(async () => {
    if (mockMode) return
    setLoading(true)
    setError('')
    try {
      const current = await fetchEvaluationDetail(evaluationId)
      setDetail(current)
      const results = await Promise.allSettled([
        fetchSupplierInvites(evaluationId),
        fetchSupplementNotices(evaluationId),
        fetchPriceRounds(evaluationId),
        fetchPriceComparison(evaluationId),
        fetchLatestMaterialCheck(evaluationId),
        fetchRisks(evaluationId),
        fetchScores(evaluationId),
        fetchRanking(evaluationId),
        fetchEvaluationReports(evaluationId),
        fetchEvaluationAuditEvents(evaluationId),
      ])
      if (results[0].status === 'fulfilled') setInvites(results[0].value)
      if (results[1].status === 'fulfilled') setNotices(results[1].value)
      if (results[2].status === 'fulfilled') setRounds(results[2].value)
      if (results[3].status === 'fulfilled') setComparison(results[3].value)
      if (results[4].status === 'fulfilled') setMaterialCheck(results[4].value)
      if (results[5].status === 'fulfilled') setRisks(results[5].value)
      if (results[6].status === 'fulfilled') setScores(results[6].value)
      if (results[7].status === 'fulfilled') setRanking(results[7].value)
      if (results[8].status === 'fulfilled') setReports(results[8].value)
      if (results[9].status === 'fulfilled') setAuditEvents(results[9].value)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : '评标任务加载失败')
    } finally {
      setLoading(false)
    }
  }, [evaluationId, mockMode])

  useEffect(() => {
    const timeout = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timeout)
  }, [load])

  const runAiReview = async () => {
    if (!detail || !['collecting', 'pending'].includes(detail.status)) {
      message.warning('当前评标状态不允许发起 AI 初审')
      return
    }
    setActionLoading('ai')
    message.loading({ content: 'AI 正在执行材料完整性、风险与评分检查…', key: 'eval-ai', duration: 0 })
    try {
      if (mockMode) {
        updateEvaluationTask(evaluationId, { status: 'human_review', currentStep: 4, progress: 80 })
      } else {
        const jobs = await Promise.all([startMaterialCheck(evaluationId), startRiskCheck(evaluationId), startAiScoring(evaluationId)])
        const failed = jobs.find(job => job.status === 'failed')
        if (failed) throw new Error(failed.error?.message || 'AI 初审任务失败')
        await load()
      }
      setActiveTab('qualification')
      message.success({ content: 'AI 初审任务已完成或进入执行队列', key: 'eval-ai' })
    } catch (actionError) {
      message.error({ content: actionError instanceof Error ? actionError.message : 'AI 初审失败', key: 'eval-ai' })
    } finally { setActionLoading('') }
  }

  const closeTask = () => {
    Modal.confirm({
      title: '确认关闭评标？',
      content: '关闭后供应商提交通道将结束，评标结果与审计记录会被保留。',
      okText: '确认关闭',
      okButtonProps: { danger: true },
      onOk: async () => {
        if (mockMode) {
          updateEvaluationTask(evaluationId, { status: 'closed', currentStep: 6, progress: 100 })
          setDetail(previous => previous ? { ...previous, status: 'closed', currentStep: 6, progressPercent: 100 } : previous)
        } else {
          await closeEvaluation(evaluationId, '评标流程已完成，结果已确认', crypto.randomUUID())
          await load()
        }
        message.success('评标已关闭，供应商将看到结束页面')
      },
    })
  }

  if (loading && !detail) return <main data-testid={EVAL_TEST_IDS.taskDetail} className="p-6"><Card loading /></main>
  if (error && !detail) return <main data-testid={EVAL_TEST_IDS.taskDetail} className="p-6"><Alert type="error" showIcon message={error} action={<Button onClick={() => void load()}>重试</Button>} /></main>
  if (!detail) return <main data-testid={EVAL_TEST_IDS.taskDetail} className="p-6"><Empty description="评标任务不存在" /></main>

  const statusMeta = EVAL_STATUS_META[detail.status] || { label: detail.status, color: 'default', step: '处理中' }
  const canRunAiReview = ['collecting', 'pending'].includes(detail.status)
  const canCreateRound = ['collecting', 'pending', 'ai_review', 'human_review'].includes(detail.status)
    && rounds.length < detail.reviewSettings.maxRounds
  const canClose = detail.status === 'completed'
  const tabs = [
    { key: 'submissions', label: <span className="flex items-center gap-1"><Upload size={14} />供应商提交</span> },
    { key: 'pricing', label: <span className="flex items-center gap-1"><DollarSign size={14} />多轮报价</span> },
    { key: 'qualification', label: <span className="flex items-center gap-1"><ShieldCheck size={14} />资格与风险</span> },
    { key: 'technical', label: <span className="flex items-center gap-1"><FileCheck2 size={14} />技术评分</span> },
    { key: 'commercial', label: <span className="flex items-center gap-1"><TrendingUp size={14} />商务评分</span> },
    { key: 'summary', label: <span className="flex items-center gap-1"><FileBarChart size={14} />综合评标</span> },
    { key: 'audit', label: <span className="flex items-center gap-1"><History size={14} />操作留痕</span> },
  ]

  return <main data-testid={EVAL_TEST_IDS.taskDetail} className="p-4 sm:p-6">
    <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <div className="flex items-center gap-3"><Button type="text" icon={<ArrowLeft size={18} />} onClick={() => navigate('/evaluation')} data-testid={EVAL_TEST_IDS.taskBack} /><div><div className="flex items-center gap-2"><h1 className="text-xl font-semibold text-[#1E293B]">{detail.projectName}</h1><Tag color={statusMeta.color}>{statusMeta.label}</Tag></div><div className="mt-1 text-xs text-[#64748B]">{detail.tenderNo} · {detail.tenderEntity} · 预算 ¥{Number(detail.budgetAmount).toLocaleString('zh-CN')}</div></div></div>
      <Space wrap><Button icon={<RefreshCw size={14} />} onClick={() => void load()}>刷新</Button><Button title={canRunAiReview ? undefined : '仅材料收集或待初审状态可发起'} disabled={!canRunAiReview} loading={actionLoading === 'ai'} icon={<Bot size={14} />} onClick={() => void runAiReview()} data-testid={EVAL_TEST_IDS.taskAiReview}>发起 AI 初审</Button><Button title={canCreateRound ? undefined : '当前状态不可创建报价轮次，或已达到最大轮次'} disabled={!canCreateRound} icon={<DollarSign size={14} />} onClick={() => { setActiveTab('pricing'); setRoundOpen(true) }}>新一轮报价</Button><Button danger title={canClose ? undefined : '全部评分确认完成后才可关闭评标'} disabled={!canClose} icon={<Gavel size={14} />} onClick={closeTask} data-testid={EVAL_TEST_IDS.taskClose}>{detail.status === 'closed' ? '评标已关闭' : '关闭评标'}</Button></Space>
    </div>

    {error && <Alert className="mb-4" type="warning" showIcon message={error} closable />}
    <WorkflowProgress step={detail.currentStep} percent={detail.progressPercent} />
    <Card className="mt-4 !border-[#E2E8F0] !shadow-none">
      <Tabs activeKey={activeTab} onChange={value => setActiveTab(value as TabKey)} items={tabs} />
      {activeTab === 'submissions' && <SubmissionPanel detail={detail} invites={invites} notices={notices} mockMode={mockMode} onReload={load} onRotate={async supplierId => { if (mockMode) { message.success('模拟邀请链接已轮换'); return } const updated = await rotateSupplierInvite(evaluationId, supplierId, '管理员重新生成邀请链接'); setInvites(previous => previous.map(invite => invite.supplierId === supplierId ? updated : invite)); await copyText(updated.inviteUrl); message.success('新邀请链接已生成并复制，请立即安全发送') }} onRevoke={async supplierId => { if (!mockMode) await revokeSupplierInvite(evaluationId, supplierId, '管理员撤销邀请'); setInvites(previous => previous.map(invite => invite.supplierId === supplierId ? { ...invite, status: 'revoked' } : invite)); message.success('邀请链接已撤销') }} onOpenSubmissions={async supplierId => { setSubmissionSupplier(supplierId); setSubmissions(mockMode ? [] : await fetchSupplierSubmissions(evaluationId, supplierId)) }} />}
      {activeTab === 'pricing' && <PricingPanel rounds={rounds} comparison={comparison} mockMode={mockMode} canCreate={canCreateRound} onCreate={() => setRoundOpen(true)} onClose={async roundId => { if (mockMode) setRounds(previous => previous.map(row => row.id === roundId ? { ...row, status: 'closed' } : row)); else { await closePriceRound(evaluationId, roundId); await load() } }} />}
      {activeTab === 'qualification' && <QualificationPanel detail={detail} materialCheck={materialCheck} risks={risks} mockMode={mockMode} onDecision={async (risk, decision) => { if (mockMode) setRisks(previous => previous.map(row => row.id === risk.id ? { ...row, decision } : row)); else { const updated = await decideRisk(evaluationId, risk.id, decision, '人工复核后确认'); setRisks(previous => previous.map(row => row.id === risk.id ? updated : row)) } }} />}
      {(activeTab === 'technical' || activeTab === 'commercial') && <ScoringPanel category={activeTab} detail={detail} scores={scores} drafts={scoreDrafts} setDrafts={setScoreDrafts} mockMode={mockMode} onSave={async score => { const draft = scoreDrafts[scoreKey(score)]; if (!draft?.value) return; if (mockMode) { setScores(previous => previous.map(row => scoreKey(row) === scoreKey(score) ? { ...row, humanScore: draft.value, finalScore: draft.value, adjustmentReason: draft.reason } : row)); setDetail(previous => previous ? { ...previous, status: 'human_review', currentStep: 5, progressPercent: 80 } : previous) } else { const updated = await updateScore(evaluationId, score, draft.value, draft.reason || '人工复核调整'); setScores(previous => previous.map(row => scoreKey(row) === scoreKey(score) ? updated : row)); setDetail(previous => previous ? { ...previous, status: 'human_review', currentStep: 5, progressPercent: 80 } : previous) } message.success('人工复审评分已保存') }} onConfirm={async () => { if (mockMode) setDetail(previous => previous ? { ...previous, status: 'completed', currentStep: 6, progressPercent: 100 } : previous); else { await confirmScores(evaluationId, undefined, '全部技术与商务评分复核完成'); await load() } message.success('全部评分已确认，评审已完成') }} />}
      {activeTab === 'summary' && <SummaryPanel detail={detail} ranking={ranking} reports={reports} mockMode={mockMode} onGenerate={async () => { if (mockMode) { downloadDemoFile('综合评标报告.txt', `项目：${detail.projectName}\n评标报告演示文件`); return } const job = await createEvaluationReport(evaluationId, ['docx', 'pdf']); if (job.status === 'failed') throw new Error(job.error?.message || '报告生成失败'); await load(); message.success('评标报告已生成或进入执行队列') }} onDownload={async report => { if (mockMode) return; const blob = await downloadEvaluationReport(evaluationId, report.id); saveBlob(blob, report.file.fileName) }} />}
      {activeTab === 'audit' && <AuditPanel events={auditEvents} />}
    </Card>

    <Modal title="新一轮报价" open={roundOpen} onCancel={() => setRoundOpen(false)} okText="创建报价轮次" okButtonProps={{ disabled: !canCreateRound }} onOk={async () => {
      if (!canCreateRound) { message.warning('当前状态不可创建报价轮次，或已达到最大轮次'); return }
      if (!roundDraft.title.trim() || !roundDraft.opensAt || !roundDraft.deadline) { message.warning('请完整填写报价轮次信息'); return }
      if (mockMode) {
        setRounds(previous => [...previous, { id: `ROUND-${Date.now()}`, evaluationId, roundNumber: previous.length + 1, title: roundDraft.title, opensAt: new Date(roundDraft.opensAt).toISOString(), deadline: new Date(roundDraft.deadline).toISOString(), status: 'open', eligibleSupplierIds: detail.suppliers.map(item => item.id), submissionCount: 0, version: 1 }])
      } else {
        await createPriceRound(evaluationId, { title: roundDraft.title, opensAt: new Date(roundDraft.opensAt).toISOString(), deadline: new Date(roundDraft.deadline).toISOString(), eligibleSupplierIds: detail.suppliers.map(item => item.id), rankingVisibleToSupplier: roundDraft.rankingVisibleToSupplier })
        await load()
      }
      setRoundOpen(false)
      message.success('新一轮报价已创建')
    }}>
      <div className="space-y-3 pt-3"><Input value={roundDraft.title} onChange={event => setRoundDraft(previous => ({ ...previous, title: event.target.value }))} placeholder="轮次标题" /><label className="block text-xs text-[#64748B]">开始时间<Input type="datetime-local" className="mt-1" value={roundDraft.opensAt} onChange={event => setRoundDraft(previous => ({ ...previous, opensAt: event.target.value }))} /></label><label className="block text-xs text-[#64748B]">截止时间<Input type="datetime-local" className="mt-1" value={roundDraft.deadline} onChange={event => setRoundDraft(previous => ({ ...previous, deadline: event.target.value }))} /></label></div>
    </Modal>

    <Modal title="供应商提交材料" open={Boolean(submissionSupplier)} onCancel={() => setSubmissionSupplier(null)} footer={<Button onClick={() => setSubmissionSupplier(null)}>关闭</Button>} width={800}><Table rowKey="id" dataSource={submissions} locale={{ emptyText: '该供应商尚无提交材料' }} columns={[{ title: '文件', render: (_, row: SupplierSubmission) => row.file.fileName }, { title: '状态', dataIndex: 'status', render: value => <Tag>{value}</Tag> }, { title: '提交时间', dataIndex: 'submittedAt', render: value => value ? formatDate(value) : '-' }, { title: '版本', dataIndex: 'version' }]} /></Modal>
  </main>
}

function WorkflowProgress({ step, percent }: { step: number; percent: number }) {
  const labels = ['创建任务', '供应商提交', '材料检查', 'AI 初审', '人工复审', '生成报告']
  return <Card className="!border-[#E2E8F0] !shadow-none"><div className="mb-3 grid grid-cols-3 gap-2 text-center text-xs md:grid-cols-6">{labels.map((label, index) => <div key={label} className={`rounded-lg px-2 py-2 ${index + 1 <= step ? 'bg-[#EFF6FF] font-medium text-[#2563EB]' : 'bg-[#F8FAFC] text-[#94A3B8]'}`}>{index + 1}. {label}</div>)}</div><Progress percent={percent} /></Card>
}

function SubmissionPanel({ detail, invites, notices, mockMode, onReload, onRotate, onRevoke, onOpenSubmissions }: { detail: EvaluationTaskDetail; invites: SupplierInviteSummary[]; notices: SupplementNotice[]; mockMode: boolean; onReload: () => Promise<void>; onRotate: (supplierId: string) => Promise<void>; onRevoke: (supplierId: string) => Promise<void>; onOpenSubmissions: (supplierId: string) => Promise<void> }) {
  const [sending, setSending] = useState('')
  const inviteBySupplier = Object.fromEntries(invites.map(invite => [invite.supplierId, invite]))
  return <div className="space-y-4">
    <Alert type="info" showIcon message={`共 ${detail.suppliers.length} 家供应商，已提交 ${detail.suppliers.filter(item => item.status === 'submitted').length} 家；补充通知 ${notices.length} 条。`} />
    <Table rowKey="id" dataSource={detail.suppliers} columns={[
      { title: '供应商', render: (_, row) => <div><div className="font-medium">{row.name}</div><div className="text-xs text-[#64748B]">{row.contactName} · {row.email}</div></div> },
      { title: '状态', dataIndex: 'status', render: value => <Tag color={value === 'submitted' ? 'green' : 'gold'}>{value}</Tag> },
      { title: '材料', render: (_, row) => `${row.submittedMaterialCount}/${row.requiredMaterialCount}` },
      { title: '邀请', render: (_, row) => inviteBySupplier[row.id] ? <Tag color={inviteBySupplier[row.id].status === 'active' ? 'blue' : 'default'}>{inviteBySupplier[row.id].status}</Tag> : '-' },
      { title: '操作', render: (_, row) => {
        const invite = inviteBySupplier[row.id]
        const canCopyInvite = Boolean(invite?.status === 'active' && !invite.inviteUrl.endsWith('/masked'))
        const canSupplement = ['submitted', 'supplementing'].includes(row.status)
        const canManageInvite = Boolean(invite && !['closed', 'cancelled'].includes(detail.status))
        return <Space wrap>
          <Button size="small" onClick={() => void onOpenSubmissions(row.id).catch(error => message.error(error instanceof Error ? error.message : '材料加载失败'))}>查看材料</Button>
          <Button size="small" title={canCopyInvite ? undefined : '脱敏链接不可复制，请先轮换生成新链接'} icon={<Copy size={12} />} disabled={!canCopyInvite} onClick={() => void copyText(invite?.inviteUrl || '').then(() => message.success('供应商邀请链接已复制')).catch(error => message.error(error instanceof Error ? error.message : '邀请链接复制失败'))}>复制邀请</Button>
          <Button size="small" title={canSupplement ? undefined : '供应商提交材料后才能发送补充通知'} disabled={!canSupplement} loading={sending === row.id} icon={<Bell size={12} />} onClick={async () => { setSending(row.id); try { if (!mockMode) { await createSupplementNotice(detail.id, { supplierId: row.id, materialIds: detail.materials.filter(item => item.required).map(item => item.id), deadlineMinutes: detail.reviewSettings.supplementDeadlineMinutes, message: '请按评标要求补充缺失或不合格材料' }); await onReload() } message.success('补充通知已发送并记录留痕') } catch (error) { message.error(error instanceof Error ? error.message : '补充通知发送失败') } finally { setSending('') } }}>发补充通知</Button>
          <Button size="small" disabled={!canManageInvite} onClick={() => void onRotate(row.id).catch(error => message.error(error instanceof Error ? error.message : '邀请链接轮换失败'))}>轮换链接</Button>
          <Button size="small" danger disabled={!canManageInvite || invite?.status !== 'active'} onClick={() => void onRevoke(row.id).catch(error => message.error(error instanceof Error ? error.message : '邀请链接撤销失败'))}>撤销</Button>
        </Space>
      } },
    ]} />
  </div>
}

function PricingPanel({ rounds, comparison, mockMode, canCreate, onCreate, onClose }: { rounds: PriceRound[]; comparison: PriceComparison | null; mockMode: boolean; canCreate: boolean; onCreate: () => void; onClose: (roundId: string) => Promise<void> }) {
  return <div className="space-y-4"><div className="flex justify-between"><div className="text-sm text-[#64748B]">报价趋势包含 {comparison?.supplierTrends.length || 0} 家供应商；所有金额由服务端留痕。</div><Button type="primary" title={canCreate ? undefined : '当前状态不可创建报价轮次，或已达到最大轮次'} disabled={!canCreate} icon={<DollarSign size={14} />} onClick={onCreate}>新建报价轮次</Button></div><Table rowKey="id" dataSource={rounds} locale={{ emptyText: '尚未创建报价轮次' }} columns={[{ title: '轮次', render: (_, row) => `第 ${row.roundNumber} 轮` }, { title: '标题', dataIndex: 'title' }, { title: '开始', dataIndex: 'opensAt', render: formatDate }, { title: '截止', dataIndex: 'deadline', render: formatDate }, { title: '状态', dataIndex: 'status', render: value => <Tag color={value === 'open' ? 'green' : 'default'}>{value}</Tag> }, { title: '报价数', dataIndex: 'submissionCount' }, { title: '操作', render: (_, row) => <Button size="small" danger disabled={row.status === 'closed'} onClick={() => void onClose(row.id).then(() => message.success('本轮报价已关闭')).catch(error => message.error(error instanceof Error ? error.message : '报价轮次关闭失败'))}>{row.status === 'closed' ? '已关闭' : '关闭轮次'}</Button> }]} /><div className="text-xs text-[#94A3B8]">{mockMode ? '模拟模式用于页面演示。' : '真实模式下报价由供应商专属门户提交。'}</div></div>
}

function QualificationPanel({ detail, materialCheck, risks, mockMode, onDecision }: { detail: EvaluationTaskDetail; materialCheck: MaterialCheckResult | null; risks: RiskFinding[]; mockMode: boolean; onDecision: (risk: RiskFinding, decision: 'passed' | 'rejected') => Promise<void> }) {
  const supplierName = Object.fromEntries(detail.suppliers.map(item => [item.id, item.name]))
  const materialName = Object.fromEntries(detail.materials.map(item => [item.id, item.name]))
  return <div className="space-y-5"><Card size="small" title="材料完整性检查"><Table rowKey={(row, index) => `${row.supplierId}-${row.materialId}-${index}`} dataSource={materialCheck?.rows || []} locale={{ emptyText: '尚无材料检查结果，请点击页面顶部“发起 AI 初审”' }} columns={[{ title: '供应商', render: (_, row) => supplierName[row.supplierId] || row.supplierId }, { title: '材料', render: (_, row) => materialName[row.materialId] || row.materialId }, { title: '结论', dataIndex: 'result', render: value => <Tag color={value === 'provided' ? 'green' : value === 'missing' ? 'red' : 'gold'}>{value}</Tag> }, { title: '证据', dataIndex: 'evidence', render: value => value.join('；') || '-' }, { title: '置信度', dataIndex: 'confidence', render: value => value === undefined ? '-' : `${Math.round(value * 100)}%` }]} /></Card><Card size="small" title="风险与废标项"><Table rowKey="id" dataSource={risks} locale={{ emptyText: '尚无风险项' }} columns={[{ title: '供应商', render: (_, row) => supplierName[row.supplierId] || row.supplierId }, { title: '风险', render: (_, row) => <div><div className="font-medium">{row.title}</div><div className="text-xs text-[#64748B]">{row.evidence.join('；')}</div></div> }, { title: '级别', dataIndex: 'severity', render: value => <Tag color={value === 'critical' || value === 'high' ? 'red' : 'gold'}>{value}</Tag> }, { title: '决定', dataIndex: 'decision', render: value => <Tag>{value}</Tag> }, { title: '人工复核', render: (_, row) => <Space><Button size="small" type="primary" disabled={row.decision !== 'pending'} onClick={() => void onDecision(row, 'passed').then(() => message.success('风险已人工确认通过'))}>通过</Button><Button size="small" danger disabled={row.decision !== 'pending'} onClick={() => void onDecision(row, 'rejected').then(() => message.warning('风险已确认，供应商不通过'))}>不通过</Button></Space> }]} /></Card>{mockMode && <Alert type="warning" showIcon message="模拟模式中的复核决定只保存于当前页面。" />}</div>
}

function ScoringPanel({ category, detail, scores, drafts, setDrafts, onSave, onConfirm }: { category: 'technical' | 'commercial'; detail: EvaluationTaskDetail; scores: ScoreItem[]; drafts: Record<string, { value: string; reason: string }>; setDrafts: React.Dispatch<React.SetStateAction<Record<string, { value: string; reason: string }>>>; mockMode: boolean; onSave: (score: ScoreItem) => Promise<void>; onConfirm: () => Promise<void> }) {
  const criteria = Object.fromEntries(detail.scoringCriteria.map(item => [item.id, item]))
  const suppliers = Object.fromEntries(detail.suppliers.map(item => [item.id, item]))
  const filtered = scores.filter(score => criteria[score.criterionId]?.category === category)
  const canConfirm = detail.status === 'human_review' && filtered.length > 0
  return <div className="space-y-4"><div className="flex justify-between"><div className="text-sm text-[#64748B]">AI 分值可人工复核；调整必须填写理由并保留版本。</div><Button type="primary" title={canConfirm ? undefined : '进入人工复审并保存评分后才可确认'} disabled={!canConfirm} onClick={() => void onConfirm().catch(error => message.error(error instanceof Error ? error.message : '评分确认失败'))}>确认全部评分并完成评审</Button></div><Table rowKey={scoreKey} dataSource={filtered} locale={{ emptyText: '暂无评分数据，请先发起 AI 初审' }} columns={[{ title: '供应商', render: (_, row) => suppliers[row.supplierId]?.name || row.supplierId }, { title: '评分项', render: (_, row) => <div><div>{criteria[row.criterionId]?.name || row.criterionId}</div><div className="text-xs text-[#64748B]">满分 {criteria[row.criterionId]?.maxScore || '-'}</div></div> }, { title: 'AI 分', dataIndex: 'aiScore', render: value => value || '-' }, { title: '最终分', dataIndex: 'finalScore' }, { title: '人工分', render: (_, row) => <InputNumber min={0} max={Number(criteria[row.criterionId]?.maxScore || 100)} value={Number(drafts[scoreKey(row)]?.value ?? row.humanScore ?? row.finalScore)} onChange={value => setDrafts(previous => ({ ...previous, [scoreKey(row)]: { value: String(value ?? ''), reason: previous[scoreKey(row)]?.reason || '' } }))} /> }, { title: '调整理由', render: (_, row) => <Input value={drafts[scoreKey(row)]?.reason ?? row.adjustmentReason ?? ''} onChange={event => setDrafts(previous => ({ ...previous, [scoreKey(row)]: { value: previous[scoreKey(row)]?.value ?? row.humanScore ?? row.finalScore, reason: event.target.value } }))} placeholder="人工调整时必填" /> }, { title: '操作', render: (_, row) => <Button size="small" onClick={() => void onSave(row).catch(error => message.error(error instanceof Error ? error.message : '人工复审评分保存失败'))}>保存复审</Button> }]} /></div>
}

function SummaryPanel({ detail, ranking, reports, mockMode, onGenerate, onDownload }: { detail: EvaluationTaskDetail; ranking: EvaluationRanking | null; reports: EvaluationReport[]; mockMode: boolean; onGenerate: () => Promise<void>; onDownload: (report: EvaluationReport) => Promise<void> }) {
  return <div className="space-y-5"><Card size="small" title="综合排名"><Table rowKey="supplierId" dataSource={ranking?.rows || []} locale={{ emptyText: '评分确认后生成综合排名' }} columns={[{ title: '排名', dataIndex: 'rank', render: value => <strong>{value}</strong> }, { title: '供应商', dataIndex: 'supplierName' }, { title: '资格分', dataIndex: 'qualificationScore' }, { title: '技术分', dataIndex: 'technicalScore' }, { title: '商务分', dataIndex: 'commercialScore' }, { title: '总分', dataIndex: 'totalScore', render: value => <strong className="text-[#2563EB]">{value}</strong> }, { title: '状态', dataIndex: 'status', render: value => <Tag>{value}</Tag> }]} /></Card><Card size="small" title="评标报告" extra={<Button type="primary" icon={<FileBarChart size={14} />} onClick={() => void onGenerate().catch(error => message.error(error instanceof Error ? error.message : '报告生成失败'))}>生成 DOCX / PDF 报告</Button>}><Table rowKey="id" dataSource={reports} locale={{ emptyText: mockMode ? '点击生成演示报告' : '尚未生成报告' }} columns={[{ title: '格式', dataIndex: 'format', render: value => <Tag>{value.toUpperCase()}</Tag> }, { title: '版本', dataIndex: 'versionNumber' }, { title: '文件', render: (_, row) => row.file.fileName }, { title: '生成时间', dataIndex: 'createdAt', render: formatDate }, { title: '操作', render: (_, row) => <Button size="small" icon={<Download size={12} />} onClick={() => void onDownload(row).catch(error => message.error(error instanceof Error ? error.message : '报告下载失败'))}>下载</Button> }]} /></Card><Alert type="info" showIcon message={`项目“${detail.projectName}”的排名、报告与关闭结果均由服务端留痕。`} /></div>
}

function AuditPanel({ events }: { events: AuditEvent[] }) {
  return events.length ? <Timeline items={events.map(event => ({ color: 'blue', dot: <Clock size={13} />, children: <div><div className="text-sm font-medium">{event.summary}</div><div className="mt-1 text-xs text-[#64748B]">{formatDate(event.createdAt)} · {event.actorName} · {event.action} · 请求 {event.requestId}</div></div> }))} /> : <Empty description="暂无操作留痕" />
}

function scoreKey(score: ScoreItem): string { return `${score.supplierId}:${score.criterionId}` }
function formatDate(value: string): string { const date = new Date(value); return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false }) }

function buildMockDetail(id: string, task?: any): EvaluationTaskDetail {
  const now = new Date().toISOString()
  return {
    id,
    projectName: task?.projectName || '2026年深圳市政务云平台采购项目',
    tenderNo: task?.tenderNo || 'SZGYY-2026-0312',
    tenderEntity: task?.tenderEntity || '深圳市政务服务数据管理局',
    budgetAmount: String(task?.budget || 5000000),
    currency: 'CNY',
    supplierDeadline: now,
    evaluationStartAt: now,
    evaluationEndAt: dayjs().add(7, 'day').toISOString(),
    status: task?.status || 'human_review',
    currentStep: task?.currentStep || 4,
    progressPercent: task?.progress || 75,
    assignee: { id: 'U001', name: task?.assignee || '张明远', role: 'project_lead' },
    supplierCount: 2,
    riskCount: 0,
    version: 1,
    createdAt: now,
    updatedAt: now,
    materials: [{ id: 'MAT-1', evaluationId: id, name: '营业执照', category: 'qualification', required: true, allowedMimeTypes: ['application/pdf'], maxSizeBytes: 50_000_000, sortOrder: 1 }],
    scoringCriteria: [{ id: 'CRIT-1', evaluationId: id, name: '技术方案完整性', category: 'technical', maxScore: '40', weightPercent: '40', method: 'expert', description: '技术方案完整、可实施', sortOrder: 1 }],
    reviewSettings: { multiRoundPricing: true, maxRounds: 3, supplementDeadlineMinutes: 1440, allowModifyBeforeDeadline: true, notifyOnMissing: true, closeSubmissionAtDeadline: true },
    reviewers: [{ id: 'U001', name: '张明远', role: 'project_lead' }],
    suppliers: [{ id: 'SUP-1', evaluationId: id, name: '华南云科技有限公司', contactName: '王经理', email: 'supplier@example.com', status: 'submitted', submittedMaterialCount: 1, requiredMaterialCount: 1 }],
    latestJobs: [],
    allowedActions: ['review', 'close'],
  }
}
