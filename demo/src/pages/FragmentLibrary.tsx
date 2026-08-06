import { useState } from 'react'
import { Button, Tag, Input, Empty, Modal, Form, Select, Upload, message, Segmented } from 'antd'
import {
  Plus, Search, FileText, Clock, TrendingUp, Zap, FileStack,
  BookOpen, Wrench, GraduationCap, Lightbulb, Package, MoreHorizontal, Download
} from 'lucide-react'
import { fragmentCategories } from '../mock/data'
import { useDemo } from '../context/DemoContext'

const categoryIcons: Record<string, any> = {
  '产品手册': Package,
  '功能手册': Wrench,
  '实施方案': FileStack,
  '培训方案': GraduationCap,
  '解决方案': Lightbulb,
  '商务文件': BookOpen
}

export default function FragmentLibrary() {
  const { fragments, setFragments } = useDemo()
  const [category, setCategory] = useState('全部')
  const [keyword, setKeyword] = useState('')
  const [searchMode, setSearchMode] = useState<'keyword' | 'semantic'>('keyword')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [selectedFile, setSelectedFile] = useState('')
  const [form] = Form.useForm()

  const aiMatchedIds = ['FRAG-003', 'FRAG-004', 'FRAG-005', 'FRAG-006', 'FRAG-007']
  const matchScores: Record<string, number> = { 'FRAG-003': 96, 'FRAG-004': 93, 'FRAG-005': 91, 'FRAG-006': 88, 'FRAG-007': 84 }

  const filtered = fragments.filter(f => {
    const matchCat = category === '全部' || f.category === category
    const matchKw = !keyword || f.title.includes(keyword) || f.preview.includes(keyword) || f.tags.some((t: string) => t.includes(keyword))
    const matchMode = searchMode === 'keyword' || aiMatchedIds.includes(f.id)
    return matchCat && matchKw && matchMode
  })

  const saveFragment = async () => {
    const values = await form.validateFields()
    setFragments(prev => [{
      id: `FRAG-${Date.now()}`,
      title: values.title,
      category: values.category,
      preview: values.preview,
      tags: String(values.tags || '').split(/[，,]/).map(value => value.trim()).filter(Boolean),
      useCount: 0,
      updatedAt: new Date().toLocaleDateString('zh-CN'),
      fileName: selectedFile || `${values.title}.docx`,
      version: 'v1.0',
      source: selectedFile ? '上传源文档' : '手工录入',
    }, ...prev])
    setUploadOpen(false)
    setSelectedFile('')
    form.resetFields()
    message.success('文档片段已上传并完成索引')
  }

  const referenceFragment = (item: any) => {
    setFragments(prev => prev.map(row => row.id === item.id ? { ...row, useCount: row.useCount + 1 } : row))
    message.success(`已引用“${item.title}”到当前演示标书`)
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-[#1E293B]">文档片段库</h1>
          <p className="text-sm text-[#64748B] mt-0.5">管理产品手册、实施方案、解决方案等文档片段，AI生成标书时自动引用匹配</p>
        </div>
        <Button onClick={() => setUploadOpen(true)} type="primary" icon={<Plus size={14} />}>上传文档片段</Button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <div className="bg-white rounded-xl border border-[#E2E8F0] p-4">
          <div className="text-2xl font-semibold text-[#1E293B]">{fragments.length}</div>
          <div className="text-xs text-[#64748B]">文档片段总数</div>
        </div>
        <div className="bg-white rounded-xl border border-[#E2E8F0] p-4">
          <div className="text-2xl font-semibold text-[#2563EB]">{new Set(fragments.map(f => f.category)).size}</div>
          <div className="text-xs text-[#64748B]">分类数</div>
        </div>
        <div className="bg-white rounded-xl border border-[#E2E8F0] p-4">
          <div className="text-2xl font-semibold text-[#16A34A]">{fragments.reduce((sum, f) => sum + f.useCount, 0)}</div>
          <div className="text-xs text-[#64748B]">总引用次数</div>
        </div>
        <div className="bg-white rounded-xl border border-[#E2E8F0] p-4">
          <div className="text-2xl font-semibold text-[#EA580C]">{aiMatchedIds.length}</div>
          <div className="text-xs text-[#64748B]">AI推荐匹配</div>
        </div>
      </div>

      {/* Category tabs + search */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3 mb-4">
        <div className="flex items-center gap-2 overflow-x-auto">
          {fragmentCategories.map(c => (
            <button
              key={c}
              onClick={() => setCategory(c)}
              className={`px-3 py-1.5 text-xs rounded-lg transition-colors whitespace-nowrap ${
                category === c
                  ? 'bg-[#2563EB] text-white font-medium'
                  : 'bg-white text-[#64748B] border border-[#E2E8F0] hover:bg-[#F8FAFC]'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-2">
          <Segmented
            size="small"
            value={searchMode}
            onChange={value => setSearchMode(value as 'keyword' | 'semantic')}
            options={[{ label: '关键词', value: 'keyword' }, { label: 'AI语义推荐', value: 'semantic' }]}
          />
          <Input
            allowClear
            size="small"
            prefix={<Search size={14} className="text-[#94A3B8]" />}
            placeholder={searchMode === 'keyword' ? '全文搜索' : '输入当前项目需求'}
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            className="w-56"
          />
        </div>
      </div>

      {/* Fragment cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {filtered.map(f => {
          const Icon = categoryIcons[f.category] || FileText
          const isAiMatched = aiMatchedIds.includes(f.id)
          return (
            <div
              key={f.id}
              className="bg-white rounded-xl border border-[#E2E8F0] p-4 hover:shadow-md hover:border-[#2563EB] transition-all cursor-pointer group"
            >
              {/* Card header */}
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-lg bg-[#EFF6FF] flex items-center justify-center flex-shrink-0">
                    <Icon size={16} color="#2563EB" />
                  </div>
                  <div>
                    <Tag className="border-0 bg-[#F1F5F9] text-[#64748B] text-xs rounded">{f.category}</Tag>
                  </div>
                </div>
                {isAiMatched && (
                  <Tag className="border-0 bg-[#FFFBEB] text-[#EA580C] text-xs rounded flex items-center gap-1">
                    <Zap size={10} /> AI推荐 {matchScores[f.id]}%
                  </Tag>
                )}
              </div>

              {/* Title */}
              <div className="text-sm font-medium text-[#1E293B] mb-2 group-hover:text-[#2563EB] transition-colors">
                {f.title}
              </div>

              {/* Preview */}
              <div className="text-xs text-[#64748B] leading-relaxed mb-3 line-clamp-3">
                {f.preview}
              </div>

              {/* Tags */}
              <div className="flex flex-wrap gap-1 mb-3">
                {f.tags.map((tag: string) => (
                  <span key={tag} className="text-xs text-[#94A3B8] bg-[#F8FAFC] px-1.5 py-0.5 rounded">
                    {tag}
                  </span>
                ))}
              </div>

              {/* Footer */}
              <div className="mb-3 rounded-lg bg-[#F8FAFC] px-2.5 py-2 text-xs text-[#64748B] flex items-center justify-between gap-2">
                <span className="truncate">来源：{f.source || f.fileName || '片段库迁移'}</span>
                <Tag className="!m-0 !text-xs">{f.version || 'v1.0'}</Tag>
              </div>
              <div className="flex items-center justify-between pt-3 border-t border-[#F8FAFC]">
                <div className="flex items-center gap-3 text-xs text-[#94A3B8]">
                  <span className="flex items-center gap-1">
                    <TrendingUp size={11} />
                    引用 {f.useCount} 次
                  </span>
                  <span className="flex items-center gap-1">
                    <Clock size={11} />
                    {f.updatedAt}
                  </span>
                </div>
                <div className="flex items-center gap-1 opacity-100 lg:opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button onClick={() => Modal.info({ title: f.title, width: 680, okText: '关闭', content: <div className="space-y-3 text-sm"><div className="grid grid-cols-2 gap-2 rounded-lg bg-[#F8FAFC] p-3 text-xs text-[#64748B]"><span>来源：{f.source || f.fileName || '片段库迁移'}</span><span>版本：{f.version || 'v1.0'}</span><span>更新时间：{f.updatedAt}</span><span>引用次数：{f.useCount}</span></div>{isAiMatched && <div className="rounded-lg border border-[#FDE68A] bg-[#FFFBEB] p-3 text-xs text-[#92400E]">AI 推荐匹配度 {matchScores[f.id]}%：与当前项目的技术方向、交付内容及关键词高度相关，引用前仍建议人工确认适用范围。</div>}<div className="flex gap-1">{f.tags.map((tag: string) => <Tag key={tag}>{tag}</Tag>)}</div><p className="leading-7 text-[#475569]">{f.preview}</p></div> })} type="text" size="small" className="text-xs h-6">预览</Button>
                  <Button onClick={() => referenceFragment(f)} type="text" size="small" className="text-xs h-6">引用</Button>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {filtered.length === 0 && (
        <div className="py-16">
          <Empty description="未找到匹配的文档片段" />
        </div>
      )}

      <Modal title="上传文档片段" open={uploadOpen} onCancel={() => { setUploadOpen(false); form.resetFields(); setSelectedFile('') }} onOk={saveFragment} okText="上传并索引" cancelText="取消">
        <Form form={form} layout="vertical" className="pt-3">
          <Form.Item name="title" label="片段标题" rules={[{ required: true, message: '请输入片段标题' }]}><Input /></Form.Item>
          <Form.Item name="category" label="分类" rules={[{ required: true }]}><Select options={fragmentCategories.filter(item => item !== '全部').map(value => ({ value, label: value }))} /></Form.Item>
          <Form.Item name="tags" label="标签"><Input placeholder="云平台，实施，政务" /></Form.Item>
          <Form.Item name="preview" label="内容摘要" rules={[{ required: true, message: '请输入内容摘要' }]}><Input.TextArea rows={4} /></Form.Item>
          <Upload showUploadList={false} beforeUpload={(file) => { setSelectedFile(file.name); return false }}><Button icon={<Plus size={14} />}>{selectedFile || '选择源文档'}</Button></Upload>
        </Form>
      </Modal>
    </div>
  )
}
