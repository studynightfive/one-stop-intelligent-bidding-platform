import { useMemo, useState } from 'react'
import { Button, Form, Input, Modal, Pagination, Segmented, Select, Switch, Table, Tag, message } from 'antd'
import { BookOpen, Clock, FileStack, FileText, GraduationCap, History, Lightbulb, Package, Plus, Quote, Search, Sparkles, Trash2, TrendingUp, Wrench } from 'lucide-react'
import { fragmentCategories } from '../mock/data'
import { useDemo } from '../context/DemoContext'
import { ConfirmAction, EmptyState, FilePreview, FilterBar, PermissionGate } from '../components/common'
import { appendLibraryVersion, nextDocumentVersion, paginate, rankFragmentsSemantic } from '../features/libraries/utils'
import type { FragmentRecord } from '../features/libraries/types'

const categoryIcons: Record<string, typeof FileText> = {
  产品手册: Package,
  功能手册: Wrench,
  实施方案: FileStack,
  培训方案: GraduationCap,
  解决方案: Lightbulb,
  商务文件: BookOpen,
}

export default function FragmentLibrary() {
  const { fragments, setFragments, permissions } = useDemo()
  const [category, setCategory] = useState('全部')
  const [query, setQuery] = useState('')
  const [searchMode, setSearchMode] = useState<'keyword' | 'semantic'>('keyword')
  const [editorOpen, setEditorOpen] = useState(false)
  const [editing, setEditing] = useState<FragmentRecord | null>(null)
  const [historyRecord, setHistoryRecord] = useState<FragmentRecord | null>(null)
  const [referenceRecord, setReferenceRecord] = useState<FragmentRecord | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(9)
  const [form] = Form.useForm()

  const normalized = useMemo(() => (fragments as FragmentRecord[]).map(record => ({
    ...record,
    source: record.source || record.fileName || '历史片段库迁移',
    version: record.version || 'v1.0',
    content: record.content || record.preview,
    references: record.references || [],
  })), [fragments])

  const searched = useMemo(() => {
    if (searchMode === 'semantic') return rankFragmentsSemantic(normalized, query)
    const keyword = query.trim().toLowerCase()
    return normalized.filter(record => !keyword || `${record.title} ${record.preview} ${record.tags.join(' ')} ${record.source}`.toLowerCase().includes(keyword))
  }, [normalized, query, searchMode])
  const filtered = searched.filter(record => category === '全部' || record.category === category)
  const paged = paginate(filtered, page, pageSize)

  const resetFilters = () => {
    setCategory('全部')
    setQuery('')
    setSearchMode('keyword')
    setPage(1)
  }

  const openEditor = (record?: FragmentRecord, createNewVersion = false) => {
    setEditing(record || null)
    form.setFieldsValue(record ? {
      ...record,
      tags: record.tags.join('，'),
      createNewVersion,
      changeNote: createNewVersion ? '更新片段内容与源文档' : '',
    } : {
      category: '解决方案',
      source: '手工录入',
      createNewVersion: true,
    })
    setEditorOpen(true)
  }

  const saveFragment = async () => {
    const values = await form.validateFields()
    const tags = String(values.tags || '').split(/[，,]/).map(value => value.trim()).filter(Boolean)
    const shouldVersion = Boolean(editing && values.createNewVersion)
    const version = shouldVersion ? nextDocumentVersion(editing?.version) : editing?.version || 'v1.0'
    const now = new Date().toLocaleString('zh-CN', { hour12: false })
    const record: FragmentRecord = {
      ...editing,
      ...values,
      id: editing?.id || `FRAG-${Date.now()}`,
      title: values.title.trim(),
      preview: values.preview.trim(),
      content: (values.content || values.preview).trim(),
      tags,
      useCount: editing?.useCount || 0,
      updatedAt: now,
      fileName: values.fileName || editing?.fileName,
      version,
      references: editing?.references || [],
      versions: shouldVersion || !editing
        ? appendLibraryVersion(editing?.versions, {
            version,
            fileName: values.fileName || editing?.fileName,
            changeNote: values.changeNote || (editing ? '更新片段' : '首次入库'),
          })
        : editing.versions,
    }
    delete (record as FragmentRecord & { createNewVersion?: boolean }).createNewVersion
    setFragments(previous => editing ? previous.map(item => item.id === editing.id ? record : item) : [record, ...previous])
    setEditorOpen(false)
    setEditing(null)
    form.resetFields()
    message.success(shouldVersion ? `片段已更新为 ${version}` : editing ? '片段已保存' : '片段已上传并完成索引')
  }

  const referenceFragment = (record: FragmentRecord) => {
    const reference = {
      id: `REF-${record.id}-${record.useCount + 1}`,
      projectName: '2026年深圳市政务云平台采购项目',
      materialName: '技术方案-总体架构',
      referencedAt: new Date().toLocaleString('zh-CN', { hour12: false }),
      referencedBy: '张明远',
    }
    setFragments(previous => previous.map(item => item.id === record.id ? {
      ...item,
      useCount: item.useCount + 1,
      references: [reference, ...(item.references || [])],
    } : item))
    message.success(`已引用“${record.title}”，引用记录已写入审计轨迹`)
  }

  const deleteFragment = (record: FragmentRecord) => {
    setFragments(previous => previous.filter(item => item.id !== record.id))
    message.success(`已删除“${record.title}”`)
  }

  return (
    <main className="p-4 sm:p-6" data-testid="fragment-library-page">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-[#1E293B]">文档片段库</h1>
          <p className="mt-1 text-sm text-[#64748B]">按关键词或语义检索可复用内容，完整记录版本与项目引用</p>
        </div>
        <PermissionGate permissions={permissions} require="library:write">
          <Button type="primary" icon={<Plus size={14} />} onClick={() => openEditor()}>新增文档片段</Button>
        </PermissionGate>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {[
          ['片段总数', normalized.length, '#1E293B'],
          ['内容分类', new Set(normalized.map(record => record.category)).size, '#2563EB'],
          ['累计引用', normalized.reduce((sum, record) => sum + record.useCount, 0), '#16A34A'],
          ['已记录版本', normalized.reduce((sum, record) => sum + Math.max(1, record.versions?.length || 0), 0), '#7C3AED'],
        ].map(([label, value, color]) => <div key={String(label)} className="rounded-xl border border-[#E2E8F0] bg-white p-4"><div className="text-2xl font-semibold" style={{ color: String(color) }}>{value}</div><div className="text-xs text-[#64748B]">{label}</div></div>)}
      </div>

      <FilterBar resultCount={filtered.length} onReset={resetFilters}>
        <Segmented value={searchMode} onChange={value => { setSearchMode(value as 'keyword' | 'semantic'); setPage(1) }} options={[{ value: 'keyword', label: '关键词检索' }, { value: 'semantic', label: 'AI 语义检索', icon: <Sparkles size={13} /> }]} />
        <Input allowClear prefix={<Search size={14} />} placeholder={searchMode === 'semantic' ? '描述需要生成的内容，如“政务云等保安全方案”' : '搜索标题、正文、标签或来源'} value={query} onChange={event => { setQuery(event.target.value); setPage(1) }} className="w-full md:!w-96" />
        <Select value={category} onChange={value => { setCategory(value); setPage(1) }} options={fragmentCategories.map(value => ({ value, label: value }))} className="w-32" />
      </FilterBar>

      {searchMode === 'semantic' && !query.trim() && <div className="mb-4 rounded-xl border border-[#BFDBFE] bg-[#EFF6FF] p-3 text-sm text-[#1D4ED8]">输入一段业务需求后，系统会显示匹配度、命中主题和推荐理由。</div>}

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {paged.items.map(record => {
          const Icon = categoryIcons[record.category] || FileText
          return (
            <article key={record.id} className="group flex min-h-[310px] flex-col rounded-xl border border-[#E2E8F0] bg-white p-4 transition-all hover:border-[#93C5FD] hover:shadow-md" data-testid="fragment-card">
              <div className="mb-3 flex items-start justify-between gap-2">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#EFF6FF]"><Icon size={17} className="text-[#2563EB]" /></span>
                <div className="flex items-center gap-1"><Tag bordered={false}>{record.category}</Tag>{searchMode === 'semantic' && record.matchScore !== undefined && <Tag color={record.matchScore >= 80 ? 'green' : 'blue'} icon={<Sparkles size={10} />}>{record.matchScore}%</Tag>}</div>
              </div>
              <h2 className="mb-2 text-sm font-semibold text-[#1E293B] group-hover:text-[#2563EB]">{record.title}</h2>
              <p className="mb-3 line-clamp-3 text-xs leading-6 text-[#64748B]">{record.preview}</p>
              {searchMode === 'semantic' && record.matchReason && <div className="mb-3 rounded-lg border border-[#FDE68A] bg-[#FFFBEB] p-2 text-xs leading-5 text-[#92400E]">推荐理由：{record.matchReason}</div>}
              <div className="mb-3 flex flex-wrap gap-1">{record.tags.map(tag => <span key={tag} className="rounded bg-[#F1F5F9] px-2 py-0.5 text-xs text-[#64748B]">{tag}</span>)}</div>
              <div className="mt-auto rounded-lg bg-[#F8FAFC] p-2.5 text-xs text-[#64748B]"><div className="flex justify-between gap-2"><span className="truncate">来源：{record.source}</span><Tag className="!m-0">{record.version}</Tag></div><div className="mt-2 flex items-center justify-between"><span className="flex items-center gap-1"><TrendingUp size={11} />引用 {record.useCount} 次</span><span className="flex items-center gap-1"><Clock size={11} />{record.updatedAt}</span></div></div>
              <div className="mt-3 flex flex-wrap items-center justify-end gap-1 border-t border-[#F1F5F9] pt-3">
                <FilePreview file={{ name: record.title, version: record.version, source: record.source, updatedAt: record.updatedAt, content: record.content }} />
                <Button type="link" size="small" icon={<Quote size={12} />} onClick={() => referenceFragment(record)}>引用</Button>
                <Button type="text" size="small" icon={<TrendingUp size={12} />} onClick={() => setReferenceRecord(record)}>引用记录</Button>
                <Button type="text" size="small" icon={<History size={12} />} onClick={() => setHistoryRecord(record)}>版本</Button>
                <PermissionGate permissions={permissions} require="library:write">
                  <Button type="text" size="small" onClick={() => openEditor(record)}>编辑</Button>
                  <ConfirmAction title={`删除“${record.title}”？`} description="删除后历史项目仍保留已引用内容，但不能再次引用该片段。" danger onConfirm={() => deleteFragment(record)} buttonProps={{ type: 'text', size: 'small', icon: <Trash2 size={12} />, 'aria-label': `删除 ${record.title}` }}>删除</ConfirmAction>
                </PermissionGate>
              </div>
            </article>
          )
        })}
      </div>

      {!paged.items.length && <div className="rounded-xl border border-[#E2E8F0] bg-white"><EmptyState title="未找到匹配片段" description="换一个检索描述或清除分类条件后再试。" action={<Button onClick={resetFilters}>清除筛选</Button>} /></div>}
      {filtered.length > 0 && <div className="mt-4 flex justify-end"><Pagination current={paged.page} pageSize={pageSize} total={filtered.length} showSizeChanger pageSizeOptions={[6, 9, 18]} showTotal={total => `共 ${total} 条`} onChange={(nextPage, nextSize) => { setPage(nextPage); setPageSize(nextSize) }} /></div>}

      <Modal title={editing ? '编辑文档片段' : '新增文档片段'} open={editorOpen} onCancel={() => { setEditorOpen(false); setEditing(null); form.resetFields() }} onOk={saveFragment} okText="保存并索引" cancelText="取消" width={720}>
        <Form form={form} layout="vertical" className="pt-3" requiredMark={false}>
          <div className="grid grid-cols-1 gap-x-4 sm:grid-cols-2">
            <Form.Item name="title" label="片段标题" rules={[{ required: true, message: '请输入片段标题' }]}><Input /></Form.Item>
            <Form.Item name="category" label="分类" rules={[{ required: true }]}><Select options={fragmentCategories.filter(value => value !== '全部').map(value => ({ value, label: value }))} /></Form.Item>
            <Form.Item name="source" label="来源" rules={[{ required: true, message: '请输入来源' }]}><Input placeholder="产品白皮书 / 手工录入" /></Form.Item>
            <Form.Item name="fileName" label="源文件"><Input placeholder="可选：solution.docx" /></Form.Item>
          </div>
          <Form.Item name="tags" label="标签"><Input placeholder="使用逗号分隔，例如：云平台，安全，等保" /></Form.Item>
          <Form.Item name="preview" label="内容摘要" rules={[{ required: true, message: '请输入内容摘要' }]}><Input.TextArea rows={3} maxLength={240} showCount /></Form.Item>
          <Form.Item name="content" label="片段正文" rules={[{ required: true, message: '请输入片段正文' }]}><Input.TextArea rows={6} /></Form.Item>
          {editing && <Form.Item name="createNewVersion" label="保存为新版本" valuePropName="checked"><Switch /></Form.Item>}
          <Form.Item name="changeNote" label="变更说明" rules={[{ required: Boolean(editing), message: '请填写变更说明' }]}><Input placeholder="说明内容调整原因" /></Form.Item>
        </Form>
      </Modal>

      <Modal title={`${historyRecord?.title || ''} · 版本历史`} open={Boolean(historyRecord)} onCancel={() => setHistoryRecord(null)} footer={<Button onClick={() => setHistoryRecord(null)}>关闭</Button>} width={760}>
        <Table rowKey={(record) => `${record.version}-${record.createdAt}`} pagination={false} dataSource={historyRecord?.versions?.length ? historyRecord.versions : [{ version: historyRecord?.version || 'v1.0', fileName: historyRecord?.fileName || '-', changeNote: '初始版本', createdAt: historyRecord?.updatedAt || '历史导入', createdBy: '系统' }]} columns={[{ title: '版本', dataIndex: 'version' }, { title: '源文件', dataIndex: 'fileName' }, { title: '变更说明', dataIndex: 'changeNote' }, { title: '更新时间', dataIndex: 'createdAt' }, { title: '操作人', dataIndex: 'createdBy' }]} />
        <Button className="mt-4" type="primary" onClick={() => { const record = historyRecord; setHistoryRecord(null); if (record) openEditor(record, true) }}>上传新版本</Button>
      </Modal>

      <Modal title={`${referenceRecord?.title || ''} · 引用记录`} open={Boolean(referenceRecord)} onCancel={() => setReferenceRecord(null)} footer={<Button onClick={() => setReferenceRecord(null)}>关闭</Button>} width={760}>
        <Table rowKey="id" pagination={{ pageSize: 5 }} locale={{ emptyText: '暂无详细引用记录；历史累计次数已保留' }} dataSource={referenceRecord?.references || []} columns={[{ title: '项目', dataIndex: 'projectName' }, { title: '材料', dataIndex: 'materialName' }, { title: '引用时间', dataIndex: 'referencedAt' }, { title: '操作人', dataIndex: 'referencedBy' }]} />
      </Modal>
    </main>
  )
}
