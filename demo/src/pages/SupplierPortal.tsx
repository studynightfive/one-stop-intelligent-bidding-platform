import { useState } from 'react'
import { Card, Button, Tag, Progress, Alert, Upload, Input, Table, Timeline, Statistic, Divider, message, Modal } from 'antd'
import { Clock, UploadCloud, FileCheck2, AlertTriangle, Lock, Bell, DollarSign, CheckCircle2, XCircle, ArrowLeft, Building2, Calendar, Trophy, Save, Download } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { requiredMaterialTemplates, supplierMaterialRecords, priceRounds, supplementNotifications, closedEvaluationExample } from '../mock/evaluationData'
import { downloadDemoFile } from '../utils/demoActions'

type PortalMode = 'active' | 'closed'

const supplierOptions = [
  { id: 'S01', name: '深圳市智联科技有限公司' },
  { id: 'S02', name: '广州云图信息技术有限公司' },
  { id: 'S03', name: '北京华信科技股份公司' },
  { id: 'S04', name: '上海数擎科技有限公司' },
]

export default function SupplierPortal() {
  const [searchParams] = useSearchParams()
  const requestedSupplier = searchParams.get('supplier')
  const invitedSupplierId = supplierOptions.some(item => item.id === requestedSupplier) ? requestedSupplier! : null
  const [mode, setMode] = useState<PortalMode>('active')
  const [selectedSupplier, setSelectedSupplier] = useState(invitedSupplierId || 'S01')
  const [supplementModalOpen, setSupplementModalOpen] = useState(false)
  const [activeSupplement, setActiveSupplement] = useState<any>(null)
  const [records, setRecords] = useState<any[]>(() => supplierMaterialRecords.map(item => ({ ...item })))
  const [finalSubmissions, setFinalSubmissions] = useState<Record<string, boolean>>({})
  const [quoteValue, setQuoteValue] = useState('')
  const [submittedQuotes, setSubmittedQuotes] = useState<Record<string, string>>({})
  const [lastDraftSaved, setLastDraftSaved] = useState('')

  const currentSupplier = supplierOptions.find(s => s.id === selectedSupplier)!
  const myMaterials = records.filter(m => m.supplierId === selectedSupplier)
  const mySupplements = supplementNotifications.filter(s => s.supplierId === selectedSupplier)
  const requiredMaterials = requiredMaterialTemplates.filter(m => m.required)
  const findSubmission = (name: string) => myMaterials.find(m => m.material === name || m.material.includes(name.split('（')[0]) || name.includes(m.material.replace(/（.*?）/g, '')))
  const submittedCount = requiredMaterials.filter(item => findSubmission(item.name)?.status === 'submitted').length
  const totalCount = requiredMaterials.length
  const allSubmitted = submittedCount === totalCount

  // Demo: simulate deadline countdown
  const deadlineText = '2026-08-08 17:00'
  const remainingText = '02小时15分钟'

  const showSupplementDetail = (supplement: any) => {
    setActiveSupplement(supplement)
    setSupplementModalOpen(true)
  }

  const uploadMaterial = (record: any, file: File) => {
    const existing = findSubmission(record.name)
    const next = {
      id: existing?.id || `SMR-${Date.now()}-${record.id}`,
      supplierId: selectedSupplier,
      supplierName: currentSupplier.name,
      material: record.name,
      fileName: file.name,
      fileSize: `${Math.max(file.size / 1024 / 1024, 0.1).toFixed(1)}MB`,
      submitTime: new Date().toLocaleString('zh-CN', { hour12: false }),
      status: 'submitted',
      round: 1,
    }
    setRecords(prev => existing ? prev.map(item => item.id === existing.id ? next : item) : [...prev, next])
    setFinalSubmissions(prev => ({ ...prev, [selectedSupplier]: false }))
    message.success(`${record.name} 上传成功`)
    return false
  }

  const batchUpload = (file: File) => {
    const missing = requiredMaterials.filter(item => findSubmission(item.name)?.status !== 'submitted')
    const now = new Date().toLocaleString('zh-CN', { hour12: false })
    setRecords(prev => {
      const next = [...prev]
      missing.forEach((item, index) => {
        const existingIndex = next.findIndex(row => row.id === findSubmission(item.name)?.id)
        const row = { id: `SMR-BATCH-${Date.now()}-${index}`, supplierId: selectedSupplier, supplierName: currentSupplier.name, material: item.name, fileName: `${item.name}-${file.name}`, fileSize: '1.0MB', submitTime: now, status: 'submitted', round: 1 }
        if (existingIndex >= 0) next[existingIndex] = { ...next[existingIndex], ...row, id: next[existingIndex].id }
        else next.push(row)
      })
      return next
    })
    message.success(missing.length ? `批量上传完成，已匹配 ${missing.length} 项材料` : '所有必交材料均已提交')
    return false
  }

  const submitQuote = () => {
    const value = Number(quoteValue.replace(/,/g, ''))
    if (!value || value <= 0) {
      message.warning('请输入有效报价金额')
      return
    }
    const formatted = value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    setSubmittedQuotes(prev => ({ ...prev, [selectedSupplier]: formatted }))
    setQuoteValue('')
    message.success('本轮报价已提交并留痕')
  }

  const savePortalDraft = () => {
    const savedAt = new Date().toLocaleString('zh-CN', { hour12: false })
    localStorage.setItem(`supplier-portal-draft-${selectedSupplier}`, JSON.stringify({
      supplierId: selectedSupplier,
      records: records.filter(item => item.supplierId === selectedSupplier),
      quoteValue,
      savedAt,
    }))
    setLastDraftSaved(savedAt)
    message.success('当前材料与报价草稿已保存到本机')
  }

  const confirmFinalSubmission = () => {
    if (!allSubmitted) {
      message.warning(`仍有 ${totalCount - submittedCount} 项必交材料未上传`)
      return
    }
    Modal.confirm({
      title: '确认完成材料提交？',
      content: '正式提交后采购方将收到通知；如需修改，请联系采购方重新开放提交。',
      okText: '确认提交',
      cancelText: '继续检查',
      onOk: () => {
        setFinalSubmissions(prev => ({ ...prev, [selectedSupplier]: true }))
        message.success('材料已正式提交，采购方将收到通知')
      },
    })
  }

  const downloadReceipt = () => {
    downloadDemoFile(`提交回执-${selectedSupplier}.txt`, [
      '智标云供应商材料提交回执',
      `供应商：${currentSupplier.name}`,
      '项目：2026年深圳市政务云平台采购项目',
      `提交材料：${submittedCount}/${totalCount}`,
      `生成时间：${new Date().toLocaleString('zh-CN', { hour12: false })}`,
      '说明：本文件为前端 Demo 生成的演示回执。',
    ].join('\n'))
    message.success('提交回执已下载')
  }

  // ===== Closed mode (评标结束) =====
  if (mode === 'closed') {
    return (
      <div className="min-h-[600px] flex items-center justify-center p-6">
        <div className="max-w-[480px] text-center">
          <div className="w-20 h-20 rounded-full bg-[#F1F5F9] flex items-center justify-center mx-auto mb-6">
            <Lock size={36} className="text-[#64748B]" />
          </div>
          <h1 className="text-2xl font-bold text-[#1E293B] mb-3">评标已结束</h1>
          <p className="text-[#64748B] text-base mb-2">{closedEvaluationExample.projectName}</p>
          <p className="text-[#94A3B8] text-sm mb-6">关闭时间：{closedEvaluationExample.closedAt}</p>

          <Alert
            type="info"
            showIcon
            message="所有提交通道已关闭"
            description={closedEvaluationExample.message}
            className="!rounded-lg !text-left mb-6"
          />

          <Card size="small" className="!border-[#E2E8F0] !rounded-lg mb-6" styles={{ body: { padding: 16 } }}>
            <div className="flex items-center gap-3 justify-center">
              <Trophy size={20} className="text-[#EA580C]" />
              <span className="text-sm text-[#64748B]">评标结果：</span>
              <span className="text-sm font-medium text-[#1E293B]">{closedEvaluationExample.result}</span>
            </div>
          </Card>

          <p className="text-xs text-[#94A3B8]">如有疑问，请联系采购单位。请等待最终结果通知。</p>

          <Divider className="my-6" />

          <Button type="link" onClick={() => setMode('active')} className="!text-[#2563EB]">
            <ArrowLeft size={14} className="mr-1" /> 返回查看提交记录
          </Button>
        </div>
      </div>
    )
  }

  // ===== Active mode (供应商提交) =====
  return (
    <div className="min-h-screen bg-[#F8FAFC] px-4 py-5 sm:p-6">
      <div className="max-w-[960px] mx-auto">
      <div className="flex items-center justify-between mb-4 px-1">
        <div className="flex items-center gap-2"><div className="w-8 h-8 rounded-lg bg-[#2563EB] text-white flex items-center justify-center font-semibold">标</div><div><p className="text-sm font-semibold text-[#1E293B]">智标云 · 供应商提交门户</p><p className="text-xs text-[#64748B]">{invitedSupplierId ? '受邀供应商专属入口 · 提交行为将记录' : '内部 Demo 入口 · 可切换供应商视角'}</p></div></div>
        <Tag color={invitedSupplierId ? 'green' : 'orange'}>{invitedSupplierId ? '专属邀请入口' : '内部演示入口'}</Tag>
      </div>
      {/* Supplier switcher (demo only) */}
      {invitedSupplierId ? (
        <Alert
          type="success"
          showIcon
          message={`当前受邀供应商：${currentSupplier.name}`}
          description="该邀请入口已锁定供应商身份，不能切换到其他供应商视角。Demo 使用前端令牌模拟，正式环境仍需服务端完成令牌有效期、身份和权限校验。"
          className="!rounded-lg mb-4"
        />
      ) : (
        <Card size="small" className="!border-[#EA580C] !bg-[#FFFBEB] !rounded-lg mb-4" styles={{ body: { padding: '10px 16px' } }}>
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-xs text-[#92400E] font-medium">Demo切换供应商视角：</span>
            {supplierOptions.map(s => (
              <button
                key={s.id}
                onClick={() => setSelectedSupplier(s.id)}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${selectedSupplier === s.id ? 'bg-[#EA580C] text-white' : 'bg-white text-[#92400E] hover:bg-[#FEF3C7]'}`}
              >
                {s.name}
              </button>
            ))}
            <span className="text-xs text-[#92400E] ml-auto cursor-pointer" onClick={() => setMode('closed')}>
              查看评标结束页面 →
            </span>
          </div>
        </Card>
      )}

      {/* Project header */}
      <Card className="!border-[#E2E8F0] !shadow-none mb-4" styles={{ body: { padding: 24 } }}>
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="w-9 h-9 rounded-lg bg-[#2563EB] flex items-center justify-center">
                <Building2 size={18} color="#fff" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-[#1E293B] leading-tight">2026年深圳市政务云平台采购项目</h1>
                <p className="text-xs text-[#64748B]">招标编号：SZGYY-2026-0312 · 采购单位：深圳市政务服务数据管理局</p>
              </div>
            </div>
          </div>
          <Tag color={finalSubmissions[selectedSupplier] ? 'green' : 'blue'} className="!text-sm !px-3 !py-1">{finalSubmissions[selectedSupplier] ? '已完成提交' : '材料提交中'}</Tag>
        </div>

        {/* Deadline countdown */}
        <div className="bg-[#FEF2F2] border border-[#FECACA] rounded-lg p-4 flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-[#DC2626] flex items-center justify-center flex-shrink-0">
            <Clock size={24} color="#fff" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-[#DC2626]">距提交截止还剩 {remainingText}</p>
            <p className="text-xs text-[#991B1B]">截止时间：{deadlineText} · 逾期将无法提交</p>
          </div>
          <div className="text-right">
            <p className="text-xs text-[#64748B]">已提交 / 必交</p>
            <p className="text-lg font-bold text-[#1E293B]">{submittedCount} / {totalCount}</p>
          </div>
        </div>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        <Card size="small" className="!border-[#E2E8F0] !shadow-none !rounded-lg" styles={{ body: { padding: 14 } }}>
          <div className="flex items-center gap-2 mb-1">
            <FileCheck2 size={15} className="text-[#16A34A]" />
            <span className="text-xs text-[#64748B]">已提交</span>
          </div>
          <p className="text-xl font-bold text-[#1E293B]">{submittedCount}</p>
        </Card>
        <Card size="small" className="!border-[#E2E8F0] !shadow-none !rounded-lg" styles={{ body: { padding: 14 } }}>
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle size={15} className="text-[#DC2626]" />
            <span className="text-xs text-[#64748B]">待提交</span>
          </div>
          <p className="text-xl font-bold text-[#DC2626]">{totalCount - submittedCount}</p>
        </Card>
        <Card size="small" className="!border-[#E2E8F0] !shadow-none !rounded-lg" styles={{ body: { padding: 14 } }}>
          <div className="flex items-center gap-2 mb-1">
            <Bell size={15} className="text-[#EA580C]" />
            <span className="text-xs text-[#64748B]">补充通知</span>
          </div>
          <p className="text-xl font-bold text-[#EA580C]">{mySupplements.length}</p>
        </Card>
        <Card size="small" className="!border-[#E2E8F0] !shadow-none !rounded-lg" styles={{ body: { padding: 14 } }}>
          <div className="flex items-center gap-2 mb-1">
            <DollarSign size={15} className="text-[#2563EB]" />
            <span className="text-xs text-[#64748B]">报价轮次</span>
          </div>
          <p className="text-xl font-bold text-[#1E293B]">{myMaterials.filter(m => m.material.includes('报价')).length}</p>
        </Card>
      </div>

      {/* Supplement notifications */}
      {mySupplements.length > 0 && (
        <Card className="!border-[#EA580C] !shadow-none mb-4" styles={{ body: { padding: 16 } }}>
          <div className="flex items-center gap-2 mb-3">
            <Bell size={16} className="text-[#EA580C]" />
            <h3 className="text-sm font-semibold text-[#1E293B]">材料补充通知</h3>
            <Tag color="orange">{mySupplements.length}条</Tag>
          </div>
          <div className="space-y-2">
            {mySupplements.map(sn => (
              <div
                key={sn.id}
                className="flex items-center gap-3 p-3 bg-[#FFFBEB] rounded-lg cursor-pointer hover:bg-[#FEF3C7] transition-colors"
                onClick={() => showSupplementDetail(sn)}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${sn.status === 'expired' ? 'bg-[#FEE2E2]' : sn.status === 'responded' ? 'bg-[#F0FDF4]' : 'bg-[#FFFBEB]'}`}>
                  {sn.status === 'expired' ? <XCircle size={16} className="text-[#DC2626]" /> :
                   sn.status === 'responded' ? <CheckCircle2 size={16} className="text-[#16A34A]" /> :
                   <AlertTriangle size={16} className="text-[#EA580C]" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[#1E293B]">
                    缺失材料：<span className="font-medium">{sn.missingMaterials.join('、')}</span>
                  </p>
                  <p className="text-xs text-[#64748B] mt-0.5">
                    {sn.note}
                  </p>
                </div>
                <div className="text-right flex-shrink-0">
                  {sn.status === 'sent' && (
                    <Tag color="orange">待响应 · 剩{sn.remainingMinutes}分钟</Tag>
                  )}
                  {sn.status === 'expired' && (
                    <Tag color="red">已超时</Tag>
                  )}
                  {sn.status === 'responded' && (
                    <Tag color="green">已响应</Tag>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Material submission */}
      <Card className="!border-[#E2E8F0] !shadow-none mb-4" styles={{ body: { padding: 24 } }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <UploadCloud size={18} className="text-[#2563EB]" />
            <h3 className="text-base font-semibold text-[#1E293B]">材料提交</h3>
          </div>
          <span className="text-sm text-[#64748B]">当前供应商：<span className="font-medium text-[#1E293B]">{currentSupplier.name}</span></span>
        </div>

        <Progress
          percent={Math.round((submittedCount / totalCount) * 100)}
          strokeColor="#2563EB"
          className="!mb-4"
          format={() => `${submittedCount}/${totalCount}`}
        />

        <div className="overflow-x-auto">
        <Table
          dataSource={requiredMaterials}
          rowKey="id"
          pagination={false}
          size="middle"
          columns={[
            {
              title: '材料名称',
              dataIndex: 'name',
              width: '30%',
              render: (name: string) => <span className="font-medium text-[#1E293B]">{name}</span>,
            },
            {
              title: '类别',
              dataIndex: 'category',
              width: 80,
              render: (cat: string) => {
                const colors: Record<string, string> = { 资质: 'blue', 商务: 'orange', 技术: 'green' }
                return <Tag color={colors[cat] || 'default'}>{cat}</Tag>
              },
            },
            {
              title: '状态',
              width: 100,
              render: (_: any, record: any) => {
                const submitted = findSubmission(record.name)
                if (submitted?.status === 'submitted') {
                  return <Tag color="green">已提交</Tag>
                }
                return <Tag color="red">未提交</Tag>
              },
            },
            {
              title: '提交时间',
              width: 160,
              render: (_: any, record: any) => {
                const submitted = findSubmission(record.name)
                return <span className="text-xs text-[#64748B]">{submitted?.submitTime || '—'}</span>
              },
            },
            {
              title: '操作',
              width: 120,
              render: (_: any, record: any) => {
                const submitted = findSubmission(record.name)
                if (submitted?.status === 'submitted') {
                  return (
                    <div className="flex items-center gap-2">
                      <Button type="link" onClick={() => Modal.info({ title: record.name, content: `已提交文件：${submitted.fileName}\n提交时间：${submitted.submitTime}` })} size="small" className="!px-0">查看</Button>
                      <Upload showUploadList={false} beforeUpload={(file) => uploadMaterial(record, file)}><Button type="link" size="small" className="!px-0">替换</Button></Upload>
                    </div>
                  )
                }
                return (
                  <Upload showUploadList={false} beforeUpload={(file) => uploadMaterial(record, file)}>
                    <Button type="primary" size="small" icon={<UploadCloud size={13} />} className="!rounded-lg !bg-[#2563EB]">
                      上传
                    </Button>
                  </Upload>
                )
              },
            },
          ]}
        />
        </div>

        {/* Upload zone */}
        <Upload.Dragger multiple showUploadList={false} beforeUpload={batchUpload} className="!mt-4">
          <UploadCloud size={32} className="text-[#94A3B8] mx-auto mb-2" />
          <p className="text-sm text-[#64748B]">点击或拖拽文件到此处批量上传</p>
          <p className="text-xs text-[#94A3B8] mt-1">Demo 会自动将文件匹配到所有待提交项目</p>
        </Upload.Dragger>

        <div className="mt-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-lg bg-[#F8FAFC] p-4">
          <div><p className="text-sm font-medium text-[#1E293B]">确认完成全部材料提交</p><p className="text-xs text-[#64748B]">{allSubmitted ? '材料已齐全，可完成本次提交。' : `仍有 ${totalCount - submittedCount} 项必交材料未上传。`}{lastDraftSaved && ` · 草稿保存于 ${lastDraftSaved}`}</p></div>
          <div className="flex gap-2 flex-wrap">
            <Button icon={<Save size={14} />} onClick={savePortalDraft}>保存草稿</Button>
            {finalSubmissions[selectedSupplier] && <Button icon={<Download size={14} />} onClick={downloadReceipt}>下载提交回执</Button>}
            <Button type="primary" disabled={!allSubmitted || finalSubmissions[selectedSupplier]} onClick={confirmFinalSubmission} className="!bg-[#2563EB]">{finalSubmissions[selectedSupplier] ? '已正式提交' : '完成材料提交'}</Button>
          </div>
        </div>
      </Card>

      {/* Multi-round pricing */}
      <Card className="!border-[#E2E8F0] !shadow-none mb-4" styles={{ body: { padding: 24 } }}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <DollarSign size={18} className="text-[#2563EB]" />
            <h3 className="text-base font-semibold text-[#1E293B]">报价提交</h3>
          </div>
          <Tag color="blue">共 {priceRounds.length} 轮</Tag>
        </div>

        <div className="space-y-3">
          {priceRounds.map((round, idx) => {
            const myPrice = round.suppliers.find(s => s.supplierId === selectedSupplier)
            const isCurrent = idx === priceRounds.length - 1 && round.status === 'completed'
            return (
              <div key={round.round} className="border border-[#E2E8F0] rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold ${round.status === 'completed' ? 'bg-[#F0FDF4] text-[#16A34A]' : 'bg-[#EFF6FF] text-[#2563EB]'}`}>
                      {round.round}
                    </div>
                    <span className="font-medium text-[#1E293B] text-sm">{round.title}</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-[#64748B]">
                    <span className="flex items-center gap-1"><Calendar size={12} /> {round.startTime} ~ {round.deadline}</span>
                    {round.status === 'completed' ? <Tag color="green">已完成</Tag> : <Tag color="blue">进行中</Tag>}
                  </div>
                </div>

                {myPrice ? (
                  <div className="flex items-center gap-4 pl-9">
                    <div className="flex-1">
                      <p className="text-xs text-[#64748B]">您的报价</p>
                      <p className="text-lg font-bold text-[#2563EB]">¥ {myPrice.price}</p>
                      {myPrice.note && <p className="text-xs text-[#EA580C] mt-0.5">{myPrice.note}</p>}
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-[#64748B]">提交时间</p>
                      <p className="text-xs text-[#1E293B]">{myPrice.submitTime || '—'}</p>
                    </div>
                    {myPrice.isLowest && <Tag color="green">最低价</Tag>}
                  </div>
                ) : (
                  <div className="pl-9">
                    {isCurrent ? (
                      <div className="flex items-center gap-3">
                        <Input value={quoteValue} onChange={event => setQuoteValue(event.target.value)} placeholder="请输入报价金额（元）" size="large" prefix="¥" className="!rounded-lg !max-w-[280px]" />
                        <Button onClick={submitQuote} type="primary" size="large" className="!rounded-lg !bg-[#2563EB]">
                          提交报价
                        </Button>
                      </div>
                    ) : (
                      <p className="text-sm text-[#94A3B8]">未参与本轮报价</p>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <Alert
          type="info"
          showIcon
          message="每轮报价截止后，您可看到自己的价格排名（不显示其他供应商报价）"
          className="!rounded-lg mt-3"
        />

        <div className="mt-4 border border-[#BFDBFE] bg-[#EFF6FF] rounded-lg p-4">
          <div className="flex flex-col sm:flex-row sm:items-end gap-3">
            <div className="flex-1"><p className="text-sm font-medium text-[#1E293B] mb-2">演示进行中报价</p><Input value={quoteValue} onChange={e => setQuoteValue(e.target.value)} placeholder="请输入本轮报价金额（元）" prefix="¥" /></div>
            <Button type="primary" onClick={submitQuote} className="!bg-[#2563EB]">提交本轮报价</Button>
          </div>
          {submittedQuotes[selectedSupplier] && <p className="text-xs text-[#16A34A] mt-2">已提交：¥ {submittedQuotes[selectedSupplier]}（本次会话留痕）</p>}
        </div>
      </Card>

      {/* Audit trail */}
      <Card className="!border-[#E2E8F0] !shadow-none mb-4" styles={{ body: { padding: 24 } }}>
        <div className="flex items-center gap-2 mb-4">
          <Clock size={18} className="text-[#2563EB]" />
          <h3 className="text-base font-semibold text-[#1E293B]">提交记录留痕</h3>
        </div>
        <Timeline
          items={myMaterials
            .filter(m => m.submitTime)
            .sort((a, b) => b.submitTime.localeCompare(a.submitTime))
            .map(m => ({
              dot: <div className="w-2.5 h-2.5 rounded-full bg-[#2563EB]" />,
              children: (
                <div className="flex items-start gap-2">
                  <div className="flex-1">
                    <p className="text-sm text-[#1E293B]">
                      提交 <span className="font-medium">{m.material}</span>
                      {m.note && <span className="text-xs text-[#EA580C] ml-2">({m.note})</span>}
                    </p>
                    <p className="text-xs text-[#64748B] mt-0.5">
                      {m.submitTime} · {m.fileName} ({m.fileSize})
                    </p>
                  </div>
                </div>
              ),
            }))}
        />
      </Card>

      {/* Close evaluation button (demo) */}
      <div className="text-center pb-6">
        <Button type="link" onClick={() => setMode('closed')} className="!text-[#64748B]">
          <Lock size={14} className="mr-1" /> 查看评标结束页面（Demo）
        </Button>
      </div>

      {/* Supplement modal */}
      <Modal
        open={supplementModalOpen}
        onCancel={() => setSupplementModalOpen(false)}
        footer={null}
        title="材料补充通知详情"
        width={520}
      >
        {activeSupplement && (
          <div className="space-y-4">
            <Alert
              type={activeSupplement.status === 'expired' ? 'error' : activeSupplement.status === 'responded' ? 'success' : 'warning'}
              showIcon
              message={activeSupplement.note}
              className="!rounded-lg"
            />
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-xs text-[#64748B] mb-1">发送时间</p>
                <p className="text-[#1E293B]">{activeSupplement.sentTime}</p>
              </div>
              <div>
                <p className="text-xs text-[#64748B] mb-1">补充截止</p>
                <p className="text-[#DC2626]">{activeSupplement.deadline}</p>
              </div>
              <div>
                <p className="text-xs text-[#64748B] mb-1">缺失材料</p>
                <div className="flex flex-wrap gap-1">
                  {activeSupplement.missingMaterials.map((m: string) => (
                    <Tag key={m} color="red">{m}</Tag>
                  ))}
                </div>
              </div>
              <div>
                <p className="text-xs text-[#64748B] mb-1">响应状态</p>
                <Tag color={activeSupplement.status === 'expired' ? 'red' : activeSupplement.status === 'responded' ? 'green' : 'orange'}>
                  {activeSupplement.status === 'expired' ? '已超时' : activeSupplement.status === 'responded' ? '已响应' : '待响应'}
                </Tag>
              </div>
            </div>
            {activeSupplement.status !== 'expired' && activeSupplement.status !== 'responded' && (
              <Button type="primary" block className="!rounded-lg !bg-[#2563EB]" onClick={() => { message.success('已跳转到材料上传页面'); setSupplementModalOpen(false) }}>
                立即补充材料
              </Button>
            )}
          </div>
        )}
      </Modal>
      </div>
    </div>
  )
}
