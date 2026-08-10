import { useEffect, useState } from 'react'
import { Card, Button, Tag, Progress, Alert, Upload, Input, Table, Timeline, Divider, message, Modal, Spin } from 'antd'
import { Clock, UploadCloud, FileCheck2, AlertTriangle, Lock, Bell, DollarSign, CheckCircle2, XCircle, ArrowLeft, Building2, Calendar, Trophy, Save, Download } from 'lucide-react'
import { useParams, useSearchParams } from 'react-router-dom'
import dayjs from 'dayjs'
import {
  createPortalApiClient, exchangePortalSession, refreshPortalSession,
  fetchPortalContext, fetchPortalMaterials, uploadPortalMaterialFile, savePortalDraft,
  submitPortalMaterials, fetchPortalReceipt, fetchPortalNotices,
  fetchPortalPriceRounds, submitPortalQuote, fetchPortalActivity,
} from '../../evaluations/api'
import { shouldUseMocks } from '../../../api/runtime'
import { createHttpBidApi } from '../../bids/adapters/httpBidApi'
import { PORTAL_TEST_IDS } from '../constants'
import { requiredMaterialTemplates, supplierMaterialRecords, priceRounds, supplementNotifications, closedEvaluationExample } from '../../../mock/evaluationData'
import { downloadDemoFile } from '../../../utils/demoActions'

const PORTAL_TOKEN_PREFIX = 'bid-platform-portal-token:'

function portalTokenKey(inviteCode: string) {
  return `${PORTAL_TOKEN_PREFIX}${inviteCode}`
}

function readPortalToken(inviteCode: string) {
  try { return sessionStorage.getItem(portalTokenKey(inviteCode)) }
  catch { return null }
}

function writePortalToken(inviteCode: string, token: string) {
  try { sessionStorage.setItem(portalTokenKey(inviteCode), token) }
  catch { /* Storage can be disabled; the in-memory state still works. */ }
}

function readableError(error: unknown, fallback: string) {
  return error instanceof Error && error.message ? error.message : fallback
}

type PortalMode = 'active' | 'closed'

interface MaterialRecord {
  id: string; supplierId: string; supplierName: string; material: string
  fileName: string; fileSize: string; submitTime: string; status: string; round: number; note?: string
}

const supplierOptions = [
  { id: 'S01', name: '深圳市智联科技有限公司' },
  { id: 'S02', name: '广州云图信息技术有限公司' },
  { id: 'S03', name: '北京华信科技股份有限公司' },
  { id: 'S04', name: '上海数擎科技有限公司' },
]

export default function SupplierPortal() {
  const { id: inviteCode } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const requestedSupplier = searchParams.get('supplier')
  const isDemo = shouldUseMocks()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [mode, setMode] = useState<PortalMode>('active')
  const [portalCtx, setPortalCtx] = useState<any>(null)
  const [portalToken, setPortalToken] = useState('')
  const [materials, setMaterials] = useState<any[]>([])
  const [records, setRecords] = useState<MaterialRecord[]>([])
  const [finalSubmitted, setFinalSubmitted] = useState(false)
  const [priceRoundData, setPriceRoundData] = useState<any[]>([])
  const [quoteValue, setQuoteValue] = useState('')
  const [submittedQuotes, setSubmittedQuotes] = useState<Record<string, string>>({})
  const [supplements, setSupplements] = useState<any[]>([])
  const [supplementModalOpen, setSupplementModalOpen] = useState(false)
  const [activeSupplement, setActiveSupplement] = useState<any>(null)
  const [lastDraftSaved, setLastDraftSaved] = useState('')
  const [activityRecords, setActivityRecords] = useState<any[]>([])
  const invitedSupplierId = supplierOptions.some(s => s.id === requestedSupplier) ? requestedSupplier! : null
  const [selectedSupplier, setSelectedSupplier] = useState(invitedSupplierId || 'S01')

  const applyPortalMaterials = (mats: any[], ctx: any) => {
    setMaterials(mats)
    setRecords(mats.map((material: any) => ({
      id: `SMR-${material.id}`,
      supplierId: ctx.supplier.id,
      supplierName: ctx.supplier.name,
      material: material.name,
      fileName: material.file?.fileName ?? '',
      fileSize: material.file?.sizeBytes
        ? `${(material.file.sizeBytes / 1024 / 1024).toFixed(1)}MB`
        : '',
      submitTime: material.submittedAt
        ? dayjs(material.submittedAt).format('YYYY-MM-DD HH:mm:ss')
        : '',
      status: material.status === 'missing' ? 'missing' : 'submitted',
      round: 1,
    })))
  }

  const deadlineRaw = portalCtx?.evaluation?.supplierDeadline
  const deadlineText = deadlineRaw ? dayjs(deadlineRaw).format('YYYY-MM-DD HH:mm') : '2026-08-08 17:00'
  const remaining = deadlineRaw
    ? (() => { const diff = dayjs(deadlineRaw).diff(dayjs()); if (diff <= 0) return '已截止'; const h = Math.floor(diff / 3600000); const m = Math.floor((diff % 3600000) / 60000); return `${h}小时${m}分钟` })()
    : '02小时15分钟'

  useEffect(() => {
    let cancelled = false
    async function loadWithToken(token: string) {
      const ctx = await fetchPortalContext(token)
      if (cancelled) return
      setPortalCtx(ctx)
      setPortalToken(token)
      setSelectedSupplier(ctx.supplier.id)
      if (['completed', 'closed', 'cancelled'].includes(ctx.evaluation.status)) setMode('closed')
      const [mats, prs, supps, acts] = await Promise.all([
        fetchPortalMaterials(token), fetchPortalPriceRounds(token), fetchPortalNotices(token), fetchPortalActivity(token),
      ])
      if (cancelled) return
      applyPortalMaterials(mats, ctx)
      setPriceRoundData(prs.map((pr: any) => ({
        id: pr.id, round: pr.roundNumber, title: pr.title,
        startTime: dayjs(pr.opensAt).format('YYYY-MM-DD HH:mm'),
        deadline: dayjs(pr.deadline).format('YYYY-MM-DD HH:mm'),
        status: pr.status === 'closed' ? 'completed' : pr.status === 'open' ? 'active' : 'scheduled',
        suppliers: pr.myQuote ? [{ supplierId: ctx.supplier.id, supplierName: ctx.supplier.name, price: pr.myQuote.amount, submitTime: dayjs(pr.myQuote.submittedAt).format('YYYY-MM-DD HH:mm:ss'), isLowest: pr.myRank === 1 }] : [],
      })))
      setSupplements(supps.map((sn: any) => ({
        id: sn.id, supplierId: sn.supplierId, supplierName: ctx.supplier.name,
        missingMaterials: (sn.materialIds ?? []).map((mid: string) => mats.find((m: any) => m.id === mid)?.name ?? mid),
        sentTime: dayjs(sn.sentAt).format('YYYY-MM-DD HH:mm:ss'),
        deadline: dayjs(sn.deadline).format('YYYY-MM-DD HH:mm:ss'),
        remainingMinutes: Math.max(0, dayjs(sn.deadline).diff(dayjs(), 'minute')),
        status: sn.status,
        responseTime: sn.respondedAt ? dayjs(sn.respondedAt).format('YYYY-MM-DD HH:mm:ss') : null,
        responseStatus: sn.status === 'responded' ? 'supplementing' : 'pending',
        note: sn.message,
      })))
      setActivityRecords(acts.map((a: any) => ({
        id: a.id, action: a.action, summary: a.summary,
        submitTime: dayjs(a.occurredAt).format('YYYY-MM-DD HH:mm:ss'),
      })))
      setFinalSubmitted(ctx.submissionSummary?.finalSubmitted ?? false)
    }
    async function loadFromApi() {
      if (!inviteCode) throw new Error('邀请链接缺少邀请码')
      const storedToken = readPortalToken(inviteCode)
      if (storedToken) {
        try {
          await loadWithToken(storedToken)
          return
        } catch {
          const refreshed = await refreshPortalSession()
          writePortalToken(inviteCode, refreshed.portalAccessToken)
          await loadWithToken(refreshed.portalAccessToken)
          return
        }
      }
      const session = await exchangePortalSession(inviteCode)
      writePortalToken(inviteCode, session.portalAccessToken)
      await loadWithToken(session.portalAccessToken)
    }
    function loadFromMock() {
      if (cancelled) return
      setRecords(supplierMaterialRecords.map((item: any) => ({ ...item })))
      setPriceRoundData(priceRounds)
      setSupplements(supplementNotifications)
    }
    const load = isDemo ? Promise.resolve(loadFromMock()) : loadFromApi()
    load.catch((reason) => {
      if (!cancelled) setError(readableError(reason, '供应商门户加载失败，请确认邀请链接仍然有效'))
    }).finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [inviteCode, isDemo])

  const currentSupplier = portalCtx?.supplier
    ? { id: portalCtx.supplier.id, name: portalCtx.supplier.name }
    : supplierOptions.find(s => s.id === selectedSupplier)!
  const myMaterials = records.filter((m: any) => m.supplierId === selectedSupplier)
  const mySupplements = supplements.filter((s: any) => s.supplierId === selectedSupplier)
  const requiredMaterialDefs = materials.length > 0
    ? materials.filter((m: any) => m.required).map((m: any) => ({ id: m.id, name: m.name, category: m.category, required: m.required }))
    : requiredMaterialTemplates.filter(m => m.required)
  const findSubmission = (name: string) => myMaterials.find((m: any) =>
    m.material === name || m.material.includes(name.split('（')[0]) || name.includes(m.material.replace(/（.*?）/g, '')))
  const submittedCount = requiredMaterialDefs.filter(item => findSubmission(item.name)?.status === 'submitted').length
  const totalCount = requiredMaterialDefs.length
  const allSubmitted = submittedCount === totalCount

  // Upload single material
  const uploadMaterial = async (record: any, file: File) => {
    const materialId = record.id || materials.find((m: any) => m.name === record.name)?.id
    if (!isDemo) {
      if (!portalToken || !materialId || !portalCtx) {
        message.error('门户会话或材料信息不完整，请刷新页面后重试')
        return false
      }
      try {
        const uploadApi = createHttpBidApi(createPortalApiClient(portalToken))
        const uploaded = await uploadApi.uploadFile(file, 'supplierMaterial', { resourceId: materialId })
        await uploadPortalMaterialFile(portalToken, materialId, uploaded.id)
        const mats = await fetchPortalMaterials(portalToken)
        applyPortalMaterials(mats, portalCtx)
        setFinalSubmitted(false)
        message.success(`${record.name} 上传成功`)
      } catch (reason) {
        message.error(readableError(reason, `${record.name} 上传失败，请重试`))
      }
      return false
    }
    const existing = findSubmission(record.name)
    const next: MaterialRecord = { id: existing?.id || `SMR-${Date.now()}-${record.id}`, supplierId: selectedSupplier, supplierName: currentSupplier.name, material: record.name, fileName: file.name, fileSize: `${Math.max(file.size / 1024 / 1024, 0.1).toFixed(1)}MB`, submitTime: new Date().toLocaleString('zh-CN', { hour12: false }), status: 'submitted', round: 1 }
    setRecords(prev => existing ? prev.map(item => item.id === existing.id ? next : item) : [...prev, next])
    setFinalSubmitted(false)
    message.success(`${record.name} 上传成功`)
    return false
  }

  // Batch upload
  const batchUpload = async (file: File) => {
    if (!isDemo) {
      const missing = materials.filter((material: any) => material.required && material.status === 'missing')
      const normalizedName = file.name.replace(/\.[^.]+$/, '').replace(/[\s_\-（）()]/g, '').toLowerCase()
      const target = missing.find((material: any) => {
        const materialName = String(material.name).replace(/[\s_\-（）()]/g, '').toLowerCase()
        return normalizedName.includes(materialName) || materialName.includes(normalizedName)
      }) || (missing.length === 1 ? missing[0] : null)
      if (!target) {
        message.warning(`无法将“${file.name}”匹配到唯一材料，请在对应材料行上传，或让文件名包含材料名称`)
        return false
      }
      return uploadMaterial(target, file)
    }
    const missing = requiredMaterialDefs.filter(item => findSubmission(item.name)?.status !== 'submitted')
    const now = new Date().toLocaleString('zh-CN', { hour12: false })
    setRecords(prev => {
      const next = [...prev]
      missing.forEach((item, index) => {
        const existingIndex = next.findIndex(row => row.id === findSubmission(item.name)?.id)
        const row: MaterialRecord = { id: `SMR-BATCH-${Date.now()}-${index}`, supplierId: selectedSupplier, supplierName: currentSupplier.name, material: item.name, fileName: `${item.name}-${file.name}`, fileSize: '1.0MB', submitTime: now, status: 'submitted', round: 1 }
        if (existingIndex >= 0) next[existingIndex] = { ...next[existingIndex], ...row, id: next[existingIndex].id }
        else next.push(row)
      })
      return next
    })
    message.success(missing.length ? `批量上传完成，已匹配 ${missing.length} 项材料` : '所有必交材料均已提交')
    return false
  }

  // Submit quote
  const submitQuoteAction = async () => {
    const value = Number(quoteValue.replace(/,/g, ''))
    if (!value || value <= 0) { message.warning('请输入有效报价金额'); return }
    const formatted = value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    if (!isDemo) {
      const openRound = priceRoundData.find((r: any) => r.status === 'active')
      if (!openRound?.id || !portalToken) { message.warning('当前没有可提交的报价轮次'); return }
      try {
        await submitPortalQuote(portalToken, openRound.id, value, `quote-${crypto.randomUUID()}`)
        const prs = await fetchPortalPriceRounds(portalToken)
        setPriceRoundData(prs.map((pr: any) => ({
          id: pr.id,
          round: pr.roundNumber,
          title: pr.title,
          startTime: dayjs(pr.opensAt).format('YYYY-MM-DD HH:mm'),
          deadline: dayjs(pr.deadline).format('YYYY-MM-DD HH:mm'),
          status: pr.status === 'closed' ? 'completed' : pr.status === 'open' ? 'active' : 'scheduled',
          suppliers: pr.myQuote ? [{
            supplierId: portalCtx?.supplier?.id,
            supplierName: portalCtx?.supplier?.name ?? '',
            price: pr.myQuote.amount,
            submitTime: dayjs(pr.myQuote.submittedAt).format('YYYY-MM-DD HH:mm:ss'),
            isLowest: pr.myRank === 1,
          }] : [],
        })))
        setQuoteValue('')
        message.success('本轮报价已提交并留痕')
      } catch (reason) {
        message.error(readableError(reason, '报价提交失败，请重试'))
      }
      return
    }
    setSubmittedQuotes(prev => ({ ...prev, [selectedSupplier]: formatted }))
    setQuoteValue('')
    message.success('本轮报价已提交并留痕')
  }

  // Save draft
  const savePortalDraftAction = async () => {
    if (!isDemo) {
      if (!portalToken) { message.error('门户会话已失效，请刷新后重试'); return }
      try { const payload: any = {}; if (quoteValue) payload.quoteDraft = Number(quoteValue.replace(/,/g, '')); const result = await savePortalDraft(portalToken, payload); setLastDraftSaved(dayjs(result.savedAt).format('YYYY-MM-DD HH:mm:ss')); message.success('当前材料与报价草稿已保存到服务端'); return } catch (reason) { message.error(readableError(reason, '草稿保存失败，请重试')); return }
    }
    const savedAt = new Date().toLocaleString('zh-CN', { hour12: false })
    localStorage.setItem(`supplier-portal-draft-${selectedSupplier}`, JSON.stringify({ supplierId: selectedSupplier, records: records.filter(item => item.supplierId === selectedSupplier), quoteValue, savedAt }))
    setLastDraftSaved(savedAt)
    message.success('当前材料与报价草稿已保存到本地')
  }

  // Final submission
  const confirmFinalSubmission = () => {
    if (!allSubmitted) { message.warning(`仍有 ${totalCount - submittedCount} 项必交材料未上传`); return }
    Modal.confirm({
      title: '确认完成材料提交？', content: '正式提交后采购方将收到通知；如需修改，请联系采购方重新开放提交。', okText: '确认提交', cancelText: '继续检查',
      onOk: async () => {
        if (!isDemo) {
          if (!portalToken) { message.error('门户会话已失效，请刷新后重试'); return }
          try { const idemKey = `submit-${crypto.randomUUID()}`; await submitPortalMaterials(portalToken, idemKey); setFinalSubmitted(true); message.success('材料已正式提交，采购方将收到通知'); return } catch (reason) { message.error(readableError(reason, '提交失败，请重试')); return }
        }
        setFinalSubmitted(true)
        message.success('材料已正式提交，采购方将收到通知')
      },
    })
  }

  // Download receipt
  const downloadReceipt = async () => {
    if (!isDemo) {
      if (!portalToken) { message.error('门户会话已失效，请刷新后重试'); return }
      try { const blob = await fetchPortalReceipt(portalToken); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = `提交回执-${selectedSupplier}.pdf`; a.click(); URL.revokeObjectURL(url); message.success('提交回执已下载'); return } catch (reason) { message.error(readableError(reason, '回执下载失败，请重试')); return }
    }
    downloadDemoFile(`提交回执-${selectedSupplier}.txt`, ['智标云供应商材料提交回执', `供应商：${currentSupplier.name}`, '项目：2026年深圳市政务云平台采购项目', `提交材料：${submittedCount}/${totalCount}`, `生成时间：${new Date().toLocaleString('zh-CN', { hour12: false })}`, '说明：本文件为Demo生成的回执。'].join('\n'))
    message.success('提交回执已下载')
  }

  if (loading) return <div role="status" aria-live="polite" className="min-h-[600px] flex flex-col items-center justify-center gap-3"><Spin size="large" /><span className="text-sm text-[#64748B]">加载供应商门户...</span></div>

  if (error && mode === 'active') return <div className="min-h-[600px] flex items-center justify-center p-6"><Alert type="error" message="加载失败" description={error} showIcon className="max-w-lg" /></div>

  if (mode === 'closed') {
    const closedProject = portalCtx?.evaluation?.projectName || closedEvaluationExample.projectName
    const closedAt = portalCtx?.evaluation?.updatedAt ? dayjs(portalCtx.evaluation.updatedAt).format('YYYY-MM-DD HH:mm:ss') : closedEvaluationExample.closedAt
    return (
      <div data-testid={PORTAL_TEST_IDS.portalClosed} className="min-h-[600px] flex items-center justify-center p-6">
        <div className="max-w-[480px] text-center">
          <div className="w-20 h-20 rounded-full bg-[#F1F5F9] flex items-center justify-center mx-auto mb-6"><Lock size={36} className="text-[#64748B]" /></div>
          <h1 className="text-2xl font-bold text-[#1E293B] mb-3">评标已结束</h1>
          <p className="text-[#64748B] text-base mb-2">{closedProject}</p>
          <p className="text-[#94A3B8] text-sm mb-6">关闭时间：{closedAt}</p>
          <Alert type="info" showIcon message="所有提交通道已关闭" description={isDemo ? closedEvaluationExample.message : '当前评标已结束，材料与报价只可查看，不能继续修改。'} className="!rounded-lg !text-left mb-6" />
          <Card size="small" className="!border-[#E2E8F0] !rounded-lg mb-6" styles={{ body: { padding: 16 } }}>
            <div className="flex items-center gap-3 justify-center"><Trophy size={20} className="text-[#EA580C]" /><span className="text-sm text-[#64748B]">评标结果：</span><span className="text-sm font-medium text-[#1E293B]">{closedEvaluationExample.result}</span></div>
          </Card>
          <p className="text-xs text-[#94A3B8]">如有疑问，请联系采购单位。请等待最终结果通知。</p>
          <Divider className="my-6" />
          {isDemo && <Button type="link" onClick={() => setMode('active')} className="!text-[#2563EB]"><ArrowLeft size={14} className="mr-1" /> 返回查看提交记录</Button>}
        </div>
      </div>
    )
  }

  const projectName = portalCtx?.evaluation?.projectName || '2026年深圳市政务云平台采购项目'
  const tenderNo = portalCtx?.evaluation?.tenderNo || 'SZGYY-2026-0312'
  const tenderEntity = portalCtx?.evaluation?.tenderEntity || '深圳市政务服务数据管理局'

  return (
    <div data-testid={PORTAL_TEST_IDS.portal} className="min-h-screen bg-[#F8FAFC] px-4 py-5 sm:p-6">
      <div className="max-w-[960px] mx-auto">
      <div className="flex items-center justify-between mb-4 px-1">
        <div className="flex items-center gap-2"><div className="w-8 h-8 rounded-lg bg-[#2563EB] text-white flex items-center justify-center font-semibold">标</div><div><p className="text-sm font-semibold text-[#1E293B]">智标云 · 供应商提交门户</p><p className="text-xs text-[#64748B]">{isDemo ? '浏览器演示数据 · 不写入服务端' : '受邀供应商专属入口 · 提交行为全程留痕'}</p></div></div>
        <Tag color={isDemo ? 'orange' : 'green'}>{isDemo ? 'Demo 模式' : '专属邀请入口'}</Tag>
      </div>
      {isDemo && !invitedSupplierId && (
        <Card size="small" className="!border-[#EA580C] !bg-[#FFFBEB] !rounded-lg mb-4" styles={{ body: { padding: '10px 16px' } }}>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xs text-[#92400E] font-medium">Demo切换供应商视角：</span>
            {supplierOptions.map(s => <button key={s.id} onClick={() => setSelectedSupplier(s.id)} className={`px-2.5 py-1 rounded text-xs transition-colors ${selectedSupplier === s.id ? 'bg-[#EA580C] text-white' : 'bg-white text-[#92400E] hover:bg-[#FEF3C7]'}`}>{s.name}</button>)}
            <span className="text-xs text-[#92400E] ml-auto cursor-pointer" onClick={() => setMode('closed')}>查看评标结束页面 →</span>
          </div>
        </Card>
      )}
      {!isDemo && portalCtx?.supplier && (
        <Alert type="success" showIcon message={`当前受邀供应商：${currentSupplier.name}`} description="该邀请入口已锁定供应商身份，不能切换到其他供应商视角。" className="!rounded-lg mb-4" />
      )}

      <Card className="!border-[#E2E8F0] !shadow-none mb-4" styles={{ body: { padding: 24 } }}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-9 h-9 rounded-lg bg-[#2563EB] flex items-center justify-center"><Building2 size={18} color="#fff" /></div>
              <div><h1 className="text-lg font-semibold text-[#1E293B] leading-tight">{projectName}</h1><p className="text-xs text-[#64748B]">招标编号：{tenderNo} · 采购单位：{tenderEntity}</p></div>
            </div>
          </div>
          <Tag color={finalSubmitted ? 'green' : 'blue'} className="!text-sm !px-3 !py-1">{finalSubmitted ? '已完成提交' : '材料提交中'}</Tag>
        </div>
        <div className="bg-[#FEF2F2] border border-[#FECACA] rounded-lg p-4 flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-[#DC2626] flex items-center justify-center flex-shrink-0"><Clock size={24} color="#fff" /></div>
          <div className="flex-1"><p className="text-sm font-medium text-[#DC2626]">距提交截止还剩 {remaining}</p><p className="text-xs text-[#991B1B]">截止时间：{deadlineText} · 逾期将无法提交</p></div>
          <div className="text-right"><p className="text-xs text-[#64748B]">已提交 / 必交</p><p className="text-lg font-bold text-[#1E293B]">{submittedCount} / {totalCount}</p></div>
        </div>
      </Card>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <Card size="small" className="!border-[#E2E8F0] !shadow-none !rounded-lg" styles={{ body: { padding: 14 } }}><div className="flex items-center gap-2 mb-1"><FileCheck2 size={15} className="text-[#16A34A]" /><span className="text-xs text-[#64748B]">已提交</span></div><p className="text-xl font-bold text-[#1E293B]">{submittedCount}</p></Card>
        <Card size="small" className="!border-[#E2E8F0] !shadow-none !rounded-lg" styles={{ body: { padding: 14 } }}><div className="flex items-center gap-2 mb-1"><AlertTriangle size={15} className="text-[#DC2626]" /><span className="text-xs text-[#64748B]">待提交</span></div><p className="text-xl font-bold text-[#DC2626]">{totalCount - submittedCount}</p></Card>
        <Card size="small" className="!border-[#E2E8F0] !shadow-none !rounded-lg" styles={{ body: { padding: 14 } }}><div className="flex items-center gap-2 mb-1"><Bell size={15} className="text-[#EA580C]" /><span className="text-xs text-[#64748B]">补充通知</span></div><p className="text-xl font-bold text-[#EA580C]">{mySupplements.length}</p></Card>
        <Card size="small" className="!border-[#E2E8F0] !shadow-none !rounded-lg" styles={{ body: { padding: 14 } }}><div className="flex items-center gap-2 mb-1"><DollarSign size={15} className="text-[#2563EB]" /><span className="text-xs text-[#64748B]">报价轮次</span></div><p className="text-xl font-bold text-[#1E293B]">{priceRoundData.length}</p></Card>
      </div>

      {mySupplements.length > 0 && (
        <Card className="!border-[#EA580C] !shadow-none mb-4" styles={{ body: { padding: 16 } }}>
          <div className="flex items-center gap-2 mb-3"><Bell size={16} className="text-[#EA580C]" /><h3 className="text-sm font-semibold text-[#1E293B]">材料补充通知</h3><Tag color="orange">{mySupplements.length}条</Tag></div>
          <div className="space-y-2">
            {mySupplements.map((sn: any) => (
              <div key={sn.id} className="flex items-center gap-3 p-3 bg-[#FFFBEB] rounded-lg cursor-pointer hover:bg-[#FEF3C7] transition-colors" onClick={() => { setActiveSupplement(sn); setSupplementModalOpen(true) }}>
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${sn.status === 'expired' ? 'bg-[#FEE2E2]' : sn.status === 'responded' ? 'bg-[#F0FDF4]' : 'bg-[#FFFBEB]'}`}>
                  {sn.status === 'expired' ? <XCircle size={16} className="text-[#DC2626]" /> : sn.status === 'responded' ? <CheckCircle2 size={16} className="text-[#16A34A]" /> : <AlertTriangle size={16} className="text-[#EA580C]" />}
                </div>
                <div className="flex-1 min-w-0"><p className="text-sm text-[#1E293B]">缺少材料：<span className="font-medium">{sn.missingMaterials.join('、')}</span></p><p className="text-xs text-[#64748B] mt-0.5">{sn.note}</p></div>
                <div className="text-right flex-shrink-0">{sn.status === 'sent' && <Tag color="orange">待响应 · 剩{sn.remainingMinutes}分钟</Tag>}{sn.status === 'expired' && <Tag color="red">已超时</Tag>}{sn.status === 'responded' && <Tag color="green">已响应</Tag>}</div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card className="!border-[#E2E8F0] !shadow-none mb-4" styles={{ body: { padding: 24 } }}>
        <div className="flex items-center justify-between mb-4"><div className="flex items-center gap-2"><UploadCloud size={18} className="text-[#2563EB]" /><h3 className="text-base font-semibold text-[#1E293B]">材料提交</h3></div><span className="text-sm text-[#64748B]">当前供应商：<span className="font-medium text-[#1E293B]">{currentSupplier.name}</span></span></div>
        <Progress percent={totalCount ? Math.round((submittedCount / totalCount) * 100) : 0} strokeColor="#2563EB" className="!mb-4" format={() => `${submittedCount}/${totalCount}`} />
        <div className="overflow-x-auto">
        <Table dataSource={requiredMaterialDefs} rowKey="id" pagination={false} size="middle" columns={[
          { title: '材料名称', dataIndex: 'name', width: '30%', render: (name: string) => <span className="font-medium text-[#1E293B]">{name}</span> },
          { title: '类别', dataIndex: 'category', width: 80, render: (cat: string) => { const colors: Record<string, string> = { '资质': 'blue', '商务': 'orange', '技术': 'green', 'qualification': 'blue', 'commercial': 'orange', 'technical': 'green' }; return <Tag color={colors[cat] || 'default'}>{cat}</Tag> } },
          { title: '状态', width: 100, render: (_: any, record: any) => { const s = findSubmission(record.name); return s?.status === 'submitted' ? <Tag color="green">已上传</Tag> : <Tag color="red">未上传</Tag> } },
          { title: '提交时间', width: 160, render: (_: any, record: any) => { const s = findSubmission(record.name); return <span className="text-xs text-[#64748B]">{s?.submitTime || '—'}</span> } },
          { title: '操作', width: 120, render: (_: any, record: any) => { const s = findSubmission(record.name); if (s?.status === 'submitted') return <div className="flex items-center gap-2"><Button type="link" onClick={() => Modal.info({ title: record.name, content: `已提交文件：${s.fileName}\n提交时间：${s.submitTime}` })} size="small" className="!px-0">查看</Button><Upload showUploadList={false} beforeUpload={(file) => uploadMaterial(record, file)}><Button type="link" size="small" className="!px-0">替换</Button></Upload></div>; return <Upload showUploadList={false} beforeUpload={(file) => uploadMaterial(record, file)}><Button type="primary" size="small" icon={<UploadCloud size={13} />} className="!rounded-lg !bg-[#2563EB]">上传</Button></Upload> } },
        ]} />
        </div>
        <Upload.Dragger multiple showUploadList={false} beforeUpload={batchUpload} className="!mt-4"><UploadCloud size={32} className="text-[#94A3B8] mx-auto mb-2" /><p className="text-sm text-[#64748B]">点击或拖拽文件到此处批量上传</p><p className="text-xs text-[#94A3B8] mt-1">{isDemo ? 'Demo 会自动将文件匹配到所有待提交项目' : '选择多个文件时，请让每个文件名包含对应材料名称；无法唯一匹配时请在材料行上传'}</p></Upload.Dragger>
        <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-lg bg-[#F8FAFC] p-4">
          <div><p className="text-sm font-medium text-[#1E293B]">确认完成全部材料提交</p><p className="text-xs text-[#64748B]">{allSubmitted ? '材料已齐备，可完成本次提交。' : `仍有 ${totalCount - submittedCount} 项必交材料未上传。`}{lastDraftSaved && ` · 草稿保存于 ${lastDraftSaved}`}</p></div>
          <div className="flex gap-2 flex-wrap"><Button icon={<Save size={14} />} onClick={savePortalDraftAction} data-testid={PORTAL_TEST_IDS.portalSaveDraft}>保存草稿</Button>{finalSubmitted && <Button icon={<Download size={14} />} onClick={downloadReceipt}>下载提交回执</Button>}<Button type="primary" disabled={!allSubmitted || finalSubmitted} onClick={confirmFinalSubmission} className="!bg-[#2563EB]" data-testid={PORTAL_TEST_IDS.portalSubmit}>{finalSubmitted ? '已正式提交' : '完成材料提交'}</Button></div>
        </div>
      </Card>

      <Card className="!border-[#E2E8F0] !shadow-none mb-4" styles={{ body: { padding: 24 } }}>
        <div className="flex items-center justify-between mb-4"><div className="flex items-center gap-2"><DollarSign size={18} className="text-[#2563EB]" /><h3 className="text-base font-semibold text-[#1E293B]">报价提交</h3></div><Tag color="blue">共 {priceRoundData.length} 轮</Tag></div>
        <div className="space-y-3">
          {priceRoundData.map((round: any) => {
            const myPrice = round.suppliers.find((s: any) => s.supplierId === selectedSupplier)
            const isCurrent = round.status === 'active'
            return (
              <div key={round.round} className="border border-[#E2E8F0] rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2"><div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${round.status === 'completed' ? 'bg-[#F0FDF4] text-[#16A34A]' : 'bg-[#EFF6FF] text-[#2563EB]'}`}>{round.round}</div><span className="font-medium text-[#1E293B] text-sm">{round.title}</span></div>
                  <div className="flex items-center gap-3 text-xs text-[#64748B]"><span className="flex items-center gap-1"><Calendar size={12} /> {round.startTime} ~ {round.deadline}</span>{round.status === 'completed' ? <Tag color="green">已完成</Tag> : <Tag color="blue">进行中</Tag>}</div>
                </div>
                {myPrice ? (
                  <div className="flex items-center gap-4 pl-9"><div className="flex-1"><p className="text-xs text-[#64748B]">您的报价</p><p className="text-lg font-bold text-[#2563EB]">¥ {myPrice.price}</p>{myPrice.note && <p className="text-xs text-[#EA580C] mt-0.5">{myPrice.note}</p>}</div><div className="text-right"><p className="text-xs text-[#64748B]">提交时间</p><p className="text-xs text-[#1E293B]">{myPrice.submitTime || '—'}</p></div>{myPrice.isLowest && <Tag color="green">最低价</Tag>}</div>
                ) : (
                  <div className="pl-9">{isCurrent ? <div className="flex items-center gap-3"><Input value={quoteValue} onChange={event => setQuoteValue(event.target.value)} placeholder="请输入报价金额（元）" size="large" prefix="¥" className="!rounded-lg !max-w-[280px]" /><Button onClick={submitQuoteAction} type="primary" size="large" className="!rounded-lg !bg-[#2563EB]" data-testid={PORTAL_TEST_IDS.portalQuoteSubmit}>提交报价</Button></div> : <p className="text-sm text-[#94A3B8]">未参与本轮报价</p>}</div>
                )}
              </div>
            )
          })}
        </div>
        <Alert type="info" showIcon message="每轮报价截止后，您可看到自己的价格排名（不显示其他供应商报价）" className="!rounded-lg mt-3" />
        {isDemo && <div className="mt-4 border border-[#BFDBFE] bg-[#EFF6FF] rounded-lg p-4"><div className="flex flex-col sm:flex-row sm:items-end gap-3"><div className="flex-1"><p className="text-sm font-medium text-[#1E293B] mb-2">演示进行中报价</p><Input value={quoteValue} onChange={e => setQuoteValue(e.target.value)} placeholder="请输入本轮报价金额（元）" prefix="¥" /></div><Button type="primary" onClick={submitQuoteAction} className="!bg-[#2563EB]" data-testid={PORTAL_TEST_IDS.portalQuoteSubmit}>提交本轮报价</Button></div>{submittedQuotes[selectedSupplier] && <p className="text-xs text-[#16A34A] mt-2">已提交：¥ {submittedQuotes[selectedSupplier]}（本次会话留痕）</p>}</div>}
      </Card>

      <Card className="!border-[#E2E8F0] !shadow-none mb-4" styles={{ body: { padding: 24 } }}>
        <div className="flex items-center gap-2 mb-4"><Clock size={18} className="text-[#2563EB]" /><h3 className="text-base font-semibold text-[#1E293B]">提交记录留痕</h3></div>
        <Timeline items={(activityRecords.length > 0 ? activityRecords : myMaterials.filter((m: any) => m.submitTime).sort((a: any, b: any) => b.submitTime.localeCompare(a.submitTime))).map((m: any) => ({ dot: <div className="w-2.5 h-2.5 rounded-full bg-[#2563EB]" />, children: <div className="flex items-start gap-2"><div className="flex-1"><p className="text-sm text-[#1E293B]">{m.action || m.material ? `提交 ${m.material || m.action}` : m.summary || m.fileName}</p><p className="text-xs text-[#64748B] mt-0.5">{m.submitTime} {m.fileName ? `· ${m.fileName}${m.fileSize ? ` (${m.fileSize})` : ''}` : ''}</p></div></div> }))} />
      </Card>

      {isDemo && <div className="text-center pb-6"><Button type="link" onClick={() => setMode('closed')} className="!text-[#64748B]"><Lock size={14} className="mr-1" /> 查看评标结束页面（Demo）</Button></div>}

      <Modal open={supplementModalOpen} onCancel={() => setSupplementModalOpen(false)} footer={null} title="材料补充通知详情" width={520}>
        {activeSupplement && <div className="space-y-4">
          <Alert type={activeSupplement.status === 'expired' ? 'error' : activeSupplement.status === 'responded' ? 'success' : 'warning'} showIcon message={activeSupplement.note} className="!rounded-lg" />
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div><p className="text-xs text-[#64748B] mb-1">发送时间</p><p className="text-[#1E293B]">{activeSupplement.sentTime}</p></div>
            <div><p className="text-xs text-[#64748B] mb-1">补充截止</p><p className="text-[#DC2626]">{activeSupplement.deadline}</p></div>
            <div><p className="text-xs text-[#64748B] mb-1">缺少材料</p><div className="flex flex-wrap gap-1">{activeSupplement.missingMaterials.map((m: string) => <Tag key={m} color="red">{m}</Tag>)}</div></div>
            <div><p className="text-xs text-[#64748B] mb-1">响应状态</p><Tag color={activeSupplement.status === 'expired' ? 'red' : activeSupplement.status === 'responded' ? 'green' : 'orange'}>{activeSupplement.status === 'expired' ? '已超时' : activeSupplement.status === 'responded' ? '已响应' : '待响应'}</Tag></div>
          </div>
          {activeSupplement.status !== 'expired' && activeSupplement.status !== 'responded' && <Button type="primary" block className="!rounded-lg !bg-[#2563EB]" onClick={() => { message.success('已跳转到材料上传页面'); setSupplementModalOpen(false) }}>立即补充材料</Button>}
        </div>}
      </Modal>
      </div>
    </div>
  )
}
