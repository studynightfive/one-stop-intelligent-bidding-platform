import { useState } from 'react'
import { Button, Tag, Input, Empty, Upload as AntUpload, Modal, Form, Select, DatePicker, message } from 'antd'
import {
  Plus, Search, Download, Upload, FileText, AlertTriangle, AlertCircle,
  CheckCircle, Clock, FileCheck2, Calendar, RefreshCw, MoreHorizontal, FileWarning
} from 'lucide-react'
import { qualStatusMap } from '../mock/data'
import { useDemo } from '../context/DemoContext'
import { downloadDemoFile } from '../utils/demoActions'
import dayjs from 'dayjs'

const categories = ['全部', '营业执照', 'ISO证书', '行业资质', '安全资质', '财务文件']

export default function QualificationLibrary() {
  const { qualifications, setQualifications } = useDemo()
  const [category, setCategory] = useState('全部')
  const [keyword, setKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [modalOpen, setModalOpen] = useState(false)
  const [editing, setEditing] = useState<any>(null)
  const [form] = Form.useForm()

  const filtered = qualifications.filter(q => {
    const matchCat = category === '全部' || q.category === category
    const matchKw = !keyword || q.name.includes(keyword) || q.certNumber.includes(keyword)
    const matchStatus = statusFilter === 'all' || (statusFilter === 'warning' ? q.status !== 'valid' : q.status === statusFilter)
    return matchCat && matchKw && matchStatus
  })

  const expiringCount = qualifications.filter(q => q.status === 'expiring').length
  const expiredCount = qualifications.filter(q => q.status === 'expired').length

  const openForm = (item?: any) => {
    setEditing(item || null)
    form.setFieldsValue(item ? { ...item, expiryDate: item.expiryDate === '-' ? null : dayjs(item.expiryDate), issuer: item.issuer || '示例发证机构', version: item.version || 'v1.0' } : { category: '行业资质', status: 'valid', version: 'v1.0' })
    setModalOpen(true)
  }

  const saveQualification = async () => {
    const values = await form.validateFields()
    const row = {
      ...values,
      id: editing?.id || `QUAL-${Date.now()}`,
      expiryDate: values.expiryDate ? values.expiryDate.format('YYYY-MM-DD') : '-',
      fileName: values.fileName || `${values.name}.pdf`,
      issuer: values.issuer || '未填写',
      version: values.version || 'v1.0',
    }
    setQualifications(prev => editing ? prev.map(item => item.id === editing.id ? row : item) : [row, ...prev])
    setModalOpen(false)
    form.resetFields()
    message.success(editing ? '资质信息已更新' : '资质已添加')
  }

  const importFile = (file: File) => {
    setQualifications(prev => [{ id: `QUAL-${Date.now()}`, name: '批量导入示例资质', category: '行业资质', certNumber: `IMPORT-${Date.now().toString().slice(-6)}`, expiryDate: dayjs().add(1, 'year').format('YYYY-MM-DD'), status: 'valid', fileName: file.name, issuer: '批量导入', version: 'v1.0' }, ...prev])
    message.success('已解析导入文件并新增 1 条演示资质')
    return false
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#1E293B]">资质库管理</h1>
          <p className="text-sm text-[#64748B] mt-0.5">管理企业资质文件，支持失效预警和跨任务共享</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={() => downloadDemoFile('资质批量导入模板.csv', '资质名称,分类,证书编号,有效期,文件名\nISO 9001,ISO证书,DEMO-001,2027-12-31,iso.pdf', 'text/csv;charset=utf-8')} icon={<Download size={14} />}>下载导入模板</Button>
          <AntUpload showUploadList={false} beforeUpload={importFile}><Button icon={<Upload size={14} />}>批量导入</Button></AntUpload>
          <Button onClick={() => openForm()} type="primary" icon={<Plus size={14} />}>添加资质</Button>
        </div>
      </div>

      {/* Warning banner */}
      {expiringCount + expiredCount > 0 && (
        <div className="bg-[#FFFBEB] border border-[#FDE68A] rounded-xl p-4 mb-4 flex items-center gap-3">
          <AlertTriangle size={20} color="#D97706" />
          <div className="flex-1 text-sm text-[#92400E]">
            {expiringCount > 0 && <span>有 <strong>{expiringCount}</strong> 项资质即将过期</span>}
            {expiringCount > 0 && expiredCount > 0 && <span>，</span>}
            {expiredCount > 0 && <span>有 <strong>{expiredCount}</strong> 项资质已失效</span>}
            <span>，请及时更新以免影响投标</span>
          </div>
          <Button onClick={() => { setCategory('全部'); setStatusFilter('warning') }} size="small" type="primary" danger={expiredCount > 0}>查看详情</Button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <div className="bg-white rounded-xl border border-[#E2E8F0] p-4">
          <div className="text-2xl font-semibold text-[#1E293B]">{qualifications.length}</div>
          <div className="text-xs text-[#64748B]">资质总数</div>
        </div>
        <div className="bg-white rounded-xl border border-[#E2E8F0] p-4">
          <div className="text-2xl font-semibold text-[#16A34A]">{qualifications.filter(q => q.status === 'valid').length}</div>
          <div className="text-xs text-[#64748B]">有效</div>
        </div>
        <div className="bg-white rounded-xl border border-[#E2E8F0] p-4">
          <div className="text-2xl font-semibold text-[#D97706]">{expiringCount}</div>
          <div className="text-xs text-[#64748B]">即将过期</div>
        </div>
        <div className="bg-white rounded-xl border border-[#E2E8F0] p-4">
          <div className="text-2xl font-semibold text-[#DC2626]">{expiredCount}</div>
          <div className="text-xs text-[#64748B]">已失效</div>
        </div>
      </div>

      {/* Filter + Search */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 mb-4">
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {categories.map(c => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${
                category === c
                  ? 'bg-[#2563EB] text-white font-medium'
                  : 'bg-white text-[#64748B] border border-[#E2E8F0] hover:bg-[#F8FAFC]'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2"><Select size="small" value={statusFilter} onChange={setStatusFilter} options={[{ value: 'all', label: '全部状态' }, { value: 'valid', label: '有效' }, { value: 'expiring', label: '即将过期' }, { value: 'expired', label: '已失效' }]} className="w-28" /><Input
          size="small"
          prefix={<Search size={14} className="text-[#94A3B8]" />}
          placeholder="搜索资质名称或编号"
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          className="w-56"
        /></div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-[#E2E8F0] overflow-x-auto">
        <table className="w-full min-w-[1080px] text-sm">
          <thead>
            <tr className="bg-[#F8FAFC] border-b border-[#E2E8F0]">
              <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">资质名称</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">分类</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">证书编号</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">发证机构 / 版本</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">有效期至</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">状态</th>
              <th className="text-left px-4 py-3 text-xs font-medium text-[#64748B]">文件</th>
              <th className="text-right px-4 py-3 text-xs font-medium text-[#64748B]">操作</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(q => {
              const status = qualStatusMap[q.status]
              const expiringSoon = q.status === 'expiring'
              const expired = q.status === 'expired'
              const remainingDays = q.expiryDate === '-' ? null : dayjs(q.expiryDate).startOf('day').diff(dayjs().startOf('day'), 'day')
              return (
                <tr key={q.id} className="border-b border-[#F8FAFC] hover:bg-[#F8FAFC]">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${
                        expired ? 'bg-[#FEF2F2]' : expiringSoon ? 'bg-[#FFFBEB]' : 'bg-[#EFF6FF]'
                      }`}>
                        <FileCheck2 size={16} color={expired ? '#DC2626' : expiringSoon ? '#D97706' : '#2563EB'} />
                      </div>
                      <span className="text-[#1E293B] font-medium">{q.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <Tag className="border-0 bg-[#F1F5F9] text-[#64748B] text-xs rounded">{q.category}</Tag>
                  </td>
                  <td className="px-4 py-3 text-[#64748B] font-mono text-xs">{q.certNumber}</td>
                  <td className="px-4 py-3"><div className="text-xs text-[#475569]">{q.issuer || '示例发证机构'}</div><Tag className="!mt-1 !text-xs">{q.version || 'v1.0'}</Tag></td>
                  <td className="px-4 py-3">
                    <div className={`flex items-center gap-1 text-xs ${expiringSoon ? 'text-[#D97706] font-medium' : expired ? 'text-[#DC2626]' : 'text-[#64748B]'}`}>
                      {q.expiryDate !== '-' && <Calendar size={12} />}
                      {q.expiryDate}
                      {remainingDays !== null && <span className="text-xs">({remainingDays < 0 ? `已过期${Math.abs(remainingDays)}天` : `剩余${remainingDays}天`})</span>}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${expiringSoon ? 'pulse-red' : ''}`}
                      style={{ color: status.color, background: status.bg }}
                    >
                      {q.status === 'valid' && <CheckCircle size={11} />}
                      {q.status === 'expiring' && <AlertTriangle size={11} />}
                      {q.status === 'expired' && <AlertCircle size={11} />}
                      {status.label}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1 text-xs text-[#2563EB] cursor-pointer hover:underline">
                      <FileText size={13} />
                      <span className="truncate max-w-[120px]">{q.fileName}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button onClick={() => Modal.info({ title: q.name, content: <div className="space-y-2 text-sm"><p>证书编号：{q.certNumber}</p><p>发证机构：{q.issuer || '示例发证机构'}</p><p>当前版本：{q.version || 'v1.0'}</p><p>有效期至：{q.expiryDate}</p><p>文件：{q.fileName}</p></div> })} type="link" size="small" className="text-xs p-0 h-6">预览</Button>
                      <Button onClick={() => downloadDemoFile(q.fileName, `${q.name}\n证书编号：${q.certNumber}\n有效期：${q.expiryDate}`)} type="link" size="small" className="text-xs p-0 h-6">下载</Button>
                      {(expiringSoon || expired) && (
                        <Button onClick={() => openForm(q)} type="link" size="small" className="text-xs p-0 h-6 text-[#EA580C]">更新</Button>
                      )}
                      {!expiringSoon && !expired && <Button onClick={() => openForm(q)} type="link" size="small" className="text-xs p-0 h-6">编辑</Button>}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="py-16">
            <Empty description="未找到匹配的资质" />
          </div>
        )}
      </div>

      <Modal title={editing ? '更新资质' : '添加资质'} open={modalOpen} onCancel={() => { setModalOpen(false); form.resetFields() }} onOk={saveQualification} okText="保存" cancelText="取消">
        <Form form={form} layout="vertical" className="pt-3">
          <Form.Item name="name" label="资质名称" rules={[{ required: true, message: '请输入资质名称' }]}><Input /></Form.Item>
          <div className="grid grid-cols-2 gap-3">
            <Form.Item name="category" label="分类" rules={[{ required: true }]}><Select options={categories.filter(item => item !== '全部').map(value => ({ value, label: value }))} /></Form.Item>
            <Form.Item name="certNumber" label="证书编号" rules={[{ required: true }]}><Input /></Form.Item>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Form.Item name="issuer" label="发证机构" rules={[{ required: true, message: '请输入发证机构' }]}><Input /></Form.Item>
            <Form.Item name="version" label="文件版本" rules={[{ required: true, message: '请输入版本号' }]}><Input placeholder="例如 v1.0" /></Form.Item>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Form.Item name="expiryDate" label="有效期至"><DatePicker className="w-full" /></Form.Item>
            <Form.Item name="status" label="状态"><Select options={[{ value: 'valid', label: '有效' }, { value: 'expiring', label: '即将过期' }, { value: 'expired', label: '已失效' }]} /></Form.Item>
          </div>
          <Form.Item name="fileName" label="文件名"><Input placeholder="例如：营业执照.pdf" /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
