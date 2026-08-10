import { useCallback, useEffect, useMemo, useState } from 'react'
import { Alert, Button, DatePicker, Form, Input, Modal, Pagination, Select, Space, Switch, Table, Tag, message } from 'antd'
import { AlertCircle, AlertTriangle, Calendar, CheckCircle, Download, FileCheck2, FileText, History, Plus, Search, Trash2 } from 'lucide-react'
import dayjs from 'dayjs'
import { useDemo } from '../context/DemoContext'
import { downloadDemoFile } from '../utils/demoActions'
import { AppUpload, ConfirmAction, EmptyState, FilePreview, FilterBar, JobProgress, PermissionGate } from '../components/common'
import { appendLibraryVersion, deriveQualificationStatus, nextDocumentVersion, paginate, qualificationRemainingDays } from '../features/libraries/utils'
import type { QualificationRecord } from '../features/libraries/types'
import { platformApi, saveBlob, type Qualification } from '../api/platformApi'
import { shouldUseMocks } from '../api/runtime'
import { createHttpBidApi } from '../features/bids/adapters/httpBidApi'

const categories = ['全部', '营业执照', 'ISO证书', '行业资质', '安全资质', '财务文件']
const statusMap = {
  valid: { label: '有效', color: '#16A34A', bg: '#F0FDF4', icon: CheckCircle },
  expiring: { label: '即将过期', color: '#D97706', bg: '#FFFBEB', icon: AlertTriangle },
  expired: { label: '已失效', color: '#DC2626', bg: '#FEF2F2', icon: AlertCircle },
  revoked: { label: '已撤销', color: '#DC2626', bg: '#FEF2F2', icon: AlertCircle },
  permanent: { label: '长期有效', color: '#2563EB', bg: '#EFF6FF', icon: CheckCircle },
} as const

export default function QualificationLibrary() {
  const { qualifications, setQualifications, permissions } = useDemo()
  const mockMode = shouldUseMocks()
  const [loading, setLoading] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [category, setCategory] = useState('全部')
  const [keyword, setKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [warningDays, setWarningDays] = useState(60)
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<QualificationRecord | null>(null)
  const [versionRecord, setVersionRecord] = useState<QualificationRecord | null>(null)
  const [importJob, setImportJob] = useState<'idle' | 'running' | 'succeeded'>('idle')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(8)
  const [form] = Form.useForm()

  const normalizeQualification = useCallback((record: Qualification): QualificationRecord => ({
    id: record.id,
    name: record.name,
    category: record.category,
    certNumber: record.certNumber,
    issuer: record.issuer,
    expiryDate: record.expiryDate || '-',
    status: record.expiryDate ? record.status : 'permanent',
    fileName: record.file.fileName,
    fileId: record.file.id,
    source: '企业资质库',
    version: record.documentVersion,
    apiVersion: record.version,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
    versions: [{
      version: record.documentVersion,
      fileName: record.file.fileName,
      changeNote: '当前生效版本',
      createdAt: new Date(record.updatedAt).toLocaleString('zh-CN', { hour12: false }),
      createdBy: '系统',
    }],
  }), [])

  const refreshQualifications = useCallback(async () => {
    if (mockMode) return
    setLoading(true)
    try {
      const result = await platformApi.listQualifications({ page: 1, pageSize: 100, sortBy: 'updatedAt', sortOrder: 'desc' })
      setQualifications(result.data.map(normalizeQualification))
    } catch (error) {
      message.error(error instanceof Error ? error.message : '资质列表加载失败')
    } finally {
      setLoading(false)
    }
  }, [mockMode, normalizeQualification, setQualifications])

  useEffect(() => {
    const timeout = window.setTimeout(() => void refreshQualifications(), 0)
    return () => window.clearTimeout(timeout)
  }, [refreshQualifications])

  const records = useMemo(() => (qualifications as QualificationRecord[]).map(record => ({
    ...record,
    issuer: record.issuer || '示例发证机构',
    source: record.source || '企业资质库',
    version: record.version || 'v1.0',
    status: deriveQualificationStatus(record.expiryDate, warningDays),
  })), [qualifications, warningDays])

  const filtered = records.filter(record => {
    const haystack = `${record.name} ${record.certNumber} ${record.issuer} ${record.source}`.toLowerCase()
    return (category === '全部' || record.category === category)
      && (!keyword.trim() || haystack.includes(keyword.trim().toLowerCase()))
      && (statusFilter === 'all' || record.status === statusFilter || (statusFilter === 'warning' && ['expiring', 'expired'].includes(record.status || '')))
  })
  const paged = paginate(filtered, page, pageSize)
  const expiringCount = records.filter(record => record.status === 'expiring').length
  const expiredCount = records.filter(record => record.status === 'expired').length

  const resetFilters = () => {
    setCategory('全部')
    setKeyword('')
    setStatusFilter('all')
    setPage(1)
  }

  const openForm = (record?: QualificationRecord, forceNewVersion = false) => {
    setEditing(record || null)
    setSelectedFile(null)
    form.setFieldsValue(record ? {
      ...record,
      expiryDate: record.expiryDate === '-' ? null : dayjs(record.expiryDate),
      createNewVersion: forceNewVersion,
      changeNote: forceNewVersion ? '更新证书文件与有效期' : '',
    } : {
      category: '行业资质',
      expiryDate: dayjs().add(1, 'year'),
      issuer: '',
      source: '企业上传',
      version: 'v1.0',
      createNewVersion: true,
    })
    setModalOpen(true)
  }

  const saveQualification = async () => {
    const values = await form.validateFields()
    const shouldVersion = Boolean(editing && values.createNewVersion)
    const version = shouldVersion ? nextDocumentVersion(editing?.version) : editing?.version || 'v1.0'
    const expiryDate = values.expiryDate ? values.expiryDate.format('YYYY-MM-DD') : '-'
    if (!mockMode) {
      setLoading(true)
      try {
        let result: Qualification
        if (editing) {
          result = await platformApi.updateQualification(editing.id, editing.apiVersion || 1, {
            name: values.name,
            category: values.category,
            certNumber: values.certNumber,
            issuer: values.issuer,
            expiryDate: expiryDate === '-' ? undefined : expiryDate,
            documentVersion: shouldVersion ? editing.version : version,
            reminderDays: [30, 60, 90],
            tags: [],
          })
          if (shouldVersion) {
            if (!selectedFile) throw new Error('生成新版本时必须选择新的资质文件')
            const fileRef = await createHttpBidApi().uploadFile(selectedFile, 'qualification')
            result = await platformApi.addQualificationVersion(editing.id, {
              fileId: fileRef.id,
              documentVersion: version,
              changeNote: values.changeNote || '更新资质版本',
            })
          }
        } else {
          if (!selectedFile) throw new Error('新增资质时必须选择并上传资质文件')
          const fileRef = await createHttpBidApi().uploadFile(selectedFile, 'qualification')
          result = await platformApi.createQualification({
            name: values.name,
            category: values.category,
            certNumber: values.certNumber,
            issuer: values.issuer,
            expiryDate: expiryDate === '-' ? undefined : expiryDate,
            fileId: fileRef.id,
            documentVersion: version,
            reminderDays: [30, 60, 90],
            tags: [],
          })
        }
        const normalized = normalizeQualification(result)
        setQualifications(previous => editing ? previous.map(item => item.id === editing.id ? normalized : item) : [normalized, ...previous])
        setModalOpen(false)
        setEditing(null)
        setSelectedFile(null)
        form.resetFields()
        message.success(shouldVersion ? `已生成 ${version} 新版本` : editing ? '资质信息已更新' : '资质已添加')
      } catch (error) {
        message.error(error instanceof Error ? error.message : '资质保存失败')
      } finally {
        setLoading(false)
      }
      return
    }
    const row: QualificationRecord = {
      ...editing,
      ...values,
      id: editing?.id || `QUAL-${Date.now()}`,
      expiryDate,
      fileName: values.fileName || editing?.fileName || `${values.name}.pdf`,
      version,
      status: deriveQualificationStatus(expiryDate, warningDays),
      updatedAt: new Date().toLocaleString('zh-CN', { hour12: false }),
      versions: shouldVersion || !editing
        ? appendLibraryVersion(editing?.versions, {
            version,
            fileName: values.fileName || editing?.fileName || `${values.name}.pdf`,
            changeNote: values.changeNote || (editing ? '更新资质信息' : '首次入库'),
          })
        : editing.versions,
    }
    delete (row as QualificationRecord & { createNewVersion?: boolean }).createNewVersion
    setQualifications(previous => editing ? previous.map(item => item.id === editing.id ? row : item) : [row, ...previous])
    setModalOpen(false)
    setEditing(null)
    form.resetFields()
    message.success(shouldVersion ? `已生成 ${version} 新版本` : editing ? '资质信息已更新' : '资质已添加')
  }

  const deleteQualification = async (record: QualificationRecord) => {
    if (!mockMode) {
      try {
        await platformApi.deleteQualification(record.id, '管理员从资质库页面删除')
      } catch (error) {
        message.error(error instanceof Error ? error.message : '资质删除失败')
        throw error
      }
    }
    setQualifications(previous => previous.filter(item => item.id !== record.id))
    message.success(`已删除“${record.name}”并保留操作记录`)
  }

  const importFiles = async (files: File[]) => {
    if (!mockMode) {
      const file = files[0]
      if (!file) return
      setImportJob('running')
      try {
        const fileRef = await createHttpBidApi().uploadFile(file, 'qualification')
        const job = await platformApi.importQualifications(fileRef.id)
        if (job.status === 'failed') throw new Error(job.error?.message || '资质导入失败')
        setImportJob(job.status === 'succeeded' ? 'succeeded' : 'running')
        await refreshQualifications()
        message.success(job.status === 'succeeded' ? '资质已导入并完成校验' : '资质导入任务已创建，可稍后刷新查看结果')
      } catch (error) {
        setImportJob('idle')
        message.error(error instanceof Error ? error.message : '资质导入失败')
      }
      return
    }
    setImportJob('running')
    const created = files.map((file, index): QualificationRecord => ({
      id: `QUAL-IMPORT-${Date.now()}-${index}`,
      name: file.name.replace(/\.[^.]+$/, ''),
      category: '行业资质',
      certNumber: `IMPORT-${Date.now().toString().slice(-6)}-${index + 1}`,
      expiryDate: dayjs().add(1, 'year').format('YYYY-MM-DD'),
      status: 'valid',
      fileName: file.name,
      issuer: '待补充发证机构',
      source: '批量导入',
      version: 'v1.0',
      versions: appendLibraryVersion(undefined, { version: 'v1.0', fileName: file.name, changeNote: '批量导入' }),
    }))
    window.setTimeout(() => {
      setQualifications(previous => [...created, ...previous])
      setImportJob('succeeded')
      message.success(`已导入 ${created.length} 条资质，待人工核对证书编号与有效期`)
    }, 650)
  }

  return (
    <main className="p-4 sm:p-6" data-testid="qualification-library-page">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[#1E293B]">资质库管理</h1>
          <p className="mt-1 text-sm text-[#64748B]">管理来源、有效期和文件版本，按 30/60/90 天动态预警</p>
        </div>
        <PermissionGate permissions={permissions} require="library:write">
          <div className="flex flex-wrap items-center gap-2">
            <Button icon={<Download size={14} />} onClick={() => {
              if (mockMode) {
                downloadDemoFile('资质批量导入模板.csv', '资质名称,分类,证书编号,发证机构,有效期,文件名\nISO 9001,ISO证书,DEMO-001,认证中心,2027-12-31,iso.pdf', 'text/csv;charset=utf-8')
              } else {
                void platformApi.downloadQualificationTemplate().then(blob => saveBlob(blob, '资质批量导入模板.xlsx')).catch(error => message.error(error instanceof Error ? error.message : '模板下载失败'))
              }
            }}>下载导入模板</Button>
            <AppUpload compact multiple accept=".pdf,.doc,.docx,.xls,.xlsx,.csv" label="批量导入" onFiles={importFiles} />
            <Button type="primary" icon={<Plus size={14} />} onClick={() => openForm()}>添加资质</Button>
          </div>
        </PermissionGate>
      </div>

      {(expiringCount > 0 || expiredCount > 0) && (
        <Alert
          className="mb-4"
          type={expiredCount ? 'error' : 'warning'}
          showIcon
          message={`${expiredCount} 项已失效，${expiringCount} 项将在 ${warningDays} 天内到期`}
          description="到期状态根据当前日期实时计算，不依赖历史缓存状态。"
          action={<Button size="small" onClick={() => { setStatusFilter('warning'); setPage(1) }}>查看预警项</Button>}
        />
      )}

      {importJob !== 'idle' && <div className="mb-4"><JobProgress title="批量解析资质文件" status={importJob === 'running' ? 'running' : 'succeeded'} progress={importJob === 'running' ? 58 : 100} message={importJob === 'running' ? '正在校验文件并提取基础字段' : '导入完成，请核对字段'} /></div>}

      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          ['资质总数', records.length, '#1E293B'],
          ['有效/长期', records.filter(record => ['valid', 'permanent'].includes(record.status || '')).length, '#16A34A'],
          [`${warningDays} 天内到期`, expiringCount, '#D97706'],
          ['已失效', expiredCount, '#DC2626'],
        ].map(([label, value, color]) => <div key={String(label)} className="rounded-xl border border-[#E2E8F0] bg-white p-4"><div className="text-2xl font-semibold" style={{ color: String(color) }}>{value}</div><div className="text-xs text-[#64748B]">{label}</div></div>)}
      </div>

      <FilterBar resultCount={filtered.length} onReset={resetFilters}>
        <Input allowClear prefix={<Search size={14} />} placeholder="搜索名称、编号、机构或来源" value={keyword} onChange={event => { setKeyword(event.target.value); setPage(1) }} className="w-full sm:!w-64" />
        <Select value={category} onChange={value => { setCategory(value); setPage(1) }} options={categories.map(value => ({ value, label: value }))} className="w-32" />
        <Select value={statusFilter} onChange={value => { setStatusFilter(value); setPage(1) }} options={[{ value: 'all', label: '全部状态' }, { value: 'valid', label: '有效' }, { value: 'permanent', label: '长期有效' }, { value: 'expiring', label: '即将过期' }, { value: 'expired', label: '已失效' }]} className="w-32" />
        <Select value={warningDays} onChange={value => { setWarningDays(value); setPage(1) }} options={[30, 60, 90].map(value => ({ value, label: `提前 ${value} 天` }))} className="w-36" aria-label="到期预警周期" />
      </FilterBar>

      <div className="overflow-x-auto rounded-xl border border-[#E2E8F0] bg-white">
        <table className="w-full min-w-[1180px] text-sm">
          <thead><tr className="border-b border-[#E2E8F0] bg-[#F8FAFC]">
            {['资质名称', '分类', '证书编号', '发证机构 / 来源', '有效期', '状态', '文件版本', '操作'].map(title => <th key={title} className={`${title === '操作' ? 'text-right' : 'text-left'} px-4 py-3 text-xs font-medium text-[#64748B]`}>{title}</th>)}
          </tr></thead>
          <tbody>
            {paged.items.map(record => {
              const status = statusMap[record.status || 'valid']
              const StatusIcon = status.icon
              const remaining = qualificationRemainingDays(record.expiryDate)
              return (
                <tr key={record.id} className="border-b border-[#F1F5F9] hover:bg-[#F8FAFC]" data-testid="qualification-row">
                  <td className="px-4 py-3"><div className="flex items-center gap-2"><span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#EFF6FF]"><FileCheck2 size={17} className="text-[#2563EB]" /></span><span className="font-medium text-[#1E293B]">{record.name}</span></div></td>
                  <td className="px-4 py-3"><Tag bordered={false}>{record.category}</Tag></td>
                  <td className="px-4 py-3 font-mono text-xs text-[#475569]">{record.certNumber}</td>
                  <td className="px-4 py-3"><div className="text-xs text-[#475569]">{record.issuer}</div><div className="mt-1 text-xs text-[#64748B]">{record.source}</div></td>
                  <td className="px-4 py-3"><div className="flex items-center gap-1 text-xs text-[#475569]"><Calendar size={12} />{record.expiryDate === '-' ? '长期有效' : record.expiryDate}</div>{remaining !== null && <div className={`mt-1 text-xs ${remaining < 0 ? 'text-[#DC2626]' : remaining <= warningDays ? 'text-[#D97706]' : 'text-[#64748B]'}`}>{remaining < 0 ? `已过期 ${Math.abs(remaining)} 天` : `剩余 ${remaining} 天`}</div>}</td>
                  <td className="px-4 py-3"><span className="inline-flex items-center gap-1 rounded px-2 py-1 text-xs font-medium" style={{ color: status.color, background: status.bg }}><StatusIcon size={12} />{status.label}</span></td>
                  <td className="px-4 py-3"><div className="flex items-center gap-1 text-xs text-[#2563EB]"><FileText size={13} />{record.fileName}</div><button type="button" className="mt-1 text-xs text-[#64748B] hover:text-[#2563EB]" onClick={() => setVersionRecord(record)}><History size={11} className="mr-1 inline" />{record.version} · 查看历史</button></td>
                  <td className="px-4 py-3 text-right"><div className="flex items-center justify-end gap-1">
                    <FilePreview file={{ name: record.fileName, version: record.version, source: record.source, updatedAt: record.updatedAt, content: `${record.name}\n证书编号：${record.certNumber}\n发证机构：${record.issuer}\n有效期：${record.expiryDate}` }} />
                    <Button type="link" size="small" onClick={() => {
                      if (mockMode) downloadDemoFile(record.fileName, `${record.name}\n证书编号：${record.certNumber}\n有效期：${record.expiryDate}`)
                      else void platformApi.downloadQualification(record.id).then(blob => saveBlob(blob, record.fileName)).catch(error => message.error(error instanceof Error ? error.message : '资质文件下载失败'))
                    }}>下载</Button>
                    <PermissionGate permissions={permissions} require="library:write">
                      <Button type="link" size="small" onClick={() => openForm(record, record.status === 'expired' || record.status === 'expiring')}>{record.status === 'expired' || record.status === 'expiring' ? '更新版本' : '编辑'}</Button>
                      <ConfirmAction title={`删除“${record.name}”？`} description="删除后不会再用于新任务，现有引用及操作日志仍然保留。" danger onConfirm={() => deleteQualification(record)} buttonProps={{ type: 'text', size: 'small', icon: <Trash2 size={13} />, 'aria-label': `删除 ${record.name}` }}>删除</ConfirmAction>
                    </PermissionGate>
                  </div></td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {!paged.items.length && <EmptyState title="未找到匹配资质" description="调整关键词、分类或到期状态后再试。" action={<Button onClick={resetFilters}>清除筛选</Button>} />}
        {filtered.length > 0 && <div className="flex justify-end border-t border-[#F1F5F9] p-3"><Pagination current={paged.page} pageSize={pageSize} total={filtered.length} showSizeChanger pageSizeOptions={[8, 16, 24]} showTotal={total => `共 ${total} 条`} onChange={(nextPage, nextSize) => { setPage(nextPage); setPageSize(nextSize) }} /></div>}
      </div>

      <Modal title={editing ? '编辑/更新资质' : '添加资质'} open={modalOpen} confirmLoading={loading} onCancel={() => { setModalOpen(false); setEditing(null); setSelectedFile(null); form.resetFields() }} onOk={saveQualification} okText="保存" cancelText="取消" width={680}>
        <Form form={form} layout="vertical" className="pt-3" requiredMark={false}>
          <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
            <Form.Item name="name" label="资质名称" rules={[{ required: true, message: '请输入资质名称' }]}><Input /></Form.Item>
            <Form.Item name="category" label="分类" rules={[{ required: true }]}><Select options={categories.filter(value => value !== '全部').map(value => ({ value, label: value }))} /></Form.Item>
            <Form.Item name="certNumber" label="证书编号" rules={[{ required: true, message: '请输入证书编号' }]}><Input /></Form.Item>
            <Form.Item name="issuer" label="发证机构" rules={[{ required: true, message: '请输入发证机构' }]}><Input /></Form.Item>
            <Form.Item name="source" label="来源" rules={[{ required: true }]}><Input placeholder="企业上传 / 历史迁移" /></Form.Item>
            <Form.Item name="expiryDate" label="有效期至"><DatePicker className="w-full" placeholder="留空表示长期有效" /></Form.Item>
            <Form.Item label="资质文件" required>
              <Space.Compact className="w-full">
                <Form.Item name="fileName" noStyle rules={[{ required: true, message: '请输入或选择文件' }]}><Input placeholder="输入文件名或选择本地文件" /></Form.Item>
                <AppUpload compact accept=".pdf,.doc,.docx,.jpg,.jpeg,.png" maxSizeMb={50} label="选择文件" onFiles={files => { if (files[0]) { setSelectedFile(files[0]); form.setFieldValue('fileName', files[0].name) } }} />
              </Space.Compact>
            </Form.Item>
            {editing && <Form.Item name="createNewVersion" label="生成新版本" valuePropName="checked"><Switch /></Form.Item>}
          </div>
          <Form.Item name="changeNote" label="变更说明" rules={[{ required: Boolean(editing), message: '请填写变更说明' }]}><Input.TextArea rows={2} placeholder="说明本次新增或更新内容" /></Form.Item>
        </Form>
      </Modal>

      <Modal title={`${versionRecord?.name || ''} · 版本历史`} open={Boolean(versionRecord)} onCancel={() => setVersionRecord(null)} footer={<Button onClick={() => setVersionRecord(null)}>关闭</Button>} width={720}>
        <Table
          rowKey={(record) => `${record.version}-${record.createdAt}`}
          pagination={false}
          dataSource={versionRecord?.versions?.length ? versionRecord.versions : [{ version: versionRecord?.version || 'v1.0', fileName: versionRecord?.fileName, changeNote: '初始版本', createdAt: versionRecord?.updatedAt || '历史导入', createdBy: '系统' }]}
          columns={[{ title: '版本', dataIndex: 'version' }, { title: '文件', dataIndex: 'fileName' }, { title: '变更说明', dataIndex: 'changeNote' }, { title: '时间', dataIndex: 'createdAt' }, { title: '操作人', dataIndex: 'createdBy' }]}
        />
      </Modal>
    </main>
  )
}
