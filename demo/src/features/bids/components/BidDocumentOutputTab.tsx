import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Alert,
  Button,
  Checkbox,
  Collapse,
  Input,
  InputNumber,
  Modal,
  Progress,
  Select,
  Switch,
  Tag,
  Upload as AntUpload,
  message,
} from 'antd'
import {
  Bot,
  Download as DownloadIcon,
  FileCheck2,
  FileImage,
  FileOutput,
  FileText,
  History,
  ImagePlus,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react'
import { getBidApi } from '../adapters/getBidApi'
import { newIdempotencyKey } from '../adapters/cryptoUtils'
import { waitForBidJob } from '../adapters/bidJobPolling'
import {
  createDefaultTechnicalDocument,
  createTechnicalSection,
  normalizeTechnicalDocument,
  validateTechnicalDocument,
  type TechnicalDocumentDraft,
} from '../adapters/technicalDocumentConfig'
import type {
  DocumentVersion,
  JobRef,
  TechnicalDocumentImage,
  TechnicalDocumentSectionTemplate,
} from '../adapters/schemaTypes'
import { useResumableUpload } from '../hooks/useResumableUpload'
import { BID_TEST_IDS } from '../constants'

const IMAGE_MAX_BYTES = 20 * 1024 * 1024

function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 0)
}

type OutputMode = 'split' | 'merged'

export function BidDocumentOutputTab({ taskId, projectName }: { taskId: string; projectName: string }) {
  const [draft, setDraft] = useState<TechnicalDocumentDraft>(() => createDefaultTechnicalDocument())
  const [outputMode, setOutputMode] = useState<OutputMode>('split')
  const [includeWatermark, setIncludeWatermark] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [generationJob, setGenerationJob] = useState<JobRef | null>(null)
  const [versions, setVersions] = useState<DocumentVersion[]>([])
  const [loading, setLoading] = useState(false)
  const [uploadingSection, setUploadingSection] = useState<string | null>(null)
  const [imageNames, setImageNames] = useState<Record<string, string>>({})
  const customSectionCounter = useRef(1)
  const {
    progress: imageUploadProgress,
    upload: uploadImage,
    cancel: cancelImageUpload,
    error: imageUploadError,
  } = useResumableUpload()

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const page = await getBidApi().listDocumentVersions(taskId, {
        page: 1,
        pageSize: 50,
        sortOrder: 'desc',
      })
      setVersions(page.data)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '加载文档版本失败')
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    const timer = window.setTimeout(() => void reload(), 0)
    return () => window.clearTimeout(timer)
  }, [reload])

  const latestId = versions[0]?.id
  const totalParagraphs = useMemo(
    () => draft.sections.reduce((total, section) => total + section.targetParagraphs, 0),
    [draft.sections],
  )
  const estimatedWords = useMemo(
    () => draft.sections.reduce(
      (total, section) => total + section.targetParagraphs * section.targetWordsPerParagraph,
      0,
    ),
    [draft.sections],
  )

  const updateSection = (key: string, patch: Partial<TechnicalDocumentSectionTemplate>) => {
    setDraft(previous => ({
      ...previous,
      sections: previous.sections.map(section => section.key === key ? { ...section, ...patch } : section),
    }))
  }

  const addSection = () => {
    let section = createTechnicalSection(customSectionCounter.current)
    while (draft.sections.some(item => item.key === section.key)) {
      customSectionCounter.current += 1
      section = createTechnicalSection(customSectionCounter.current)
    }
    customSectionCounter.current += 1
    setDraft(previous => ({ ...previous, sections: [...previous.sections, section] }))
  }

  const removeSection = (key: string) => {
    if (draft.sections.length === 1) {
      message.warning('技术文档至少保留一个章节')
      return
    }
    setDraft(previous => ({
      ...previous,
      sections: previous.sections.filter(section => section.key !== key),
      referenceImages: previous.referenceImages.filter(image => image.sectionKey !== key),
    }))
  }

  const updateImage = (fileId: string, patch: Partial<TechnicalDocumentImage>) => {
    setDraft(previous => ({
      ...previous,
      referenceImages: previous.referenceImages.map(image => {
        if (image.fileId !== fileId) return image
        const next = { ...image, ...patch }
        if (next.placement !== 'after_paragraph') delete next.afterParagraphIndex
        return next
      }),
    }))
  }

  const removeImage = (fileId: string) => {
    setDraft(previous => ({
      ...previous,
      referenceImages: previous.referenceImages.filter(image => image.fileId !== fileId),
    }))
    setImageNames(previous => {
      const next = { ...previous }
      delete next[fileId]
      return next
    })
  }

  const handleImageUpload = async (sectionKey: string, file: File) => {
    const supported = ['image/png', 'image/jpeg'].includes(file.type)
      || /\.(png|jpe?g)$/i.test(file.name)
    if (!supported) {
      message.error('技术文档图片仅支持 PNG 或 JPEG')
      return
    }
    if (file.size > IMAGE_MAX_BYTES) {
      message.error('单张参考图片不能超过 20 MiB')
      return
    }
    setUploadingSection(sectionKey)
    try {
      const fileRef = await uploadImage(file, 'bidIllustration', taskId)
      setImageNames(previous => ({ ...previous, [fileRef.id]: file.name }))
      setDraft(previous => ({
        ...previous,
        referenceImages: [
          ...previous.referenceImages,
          {
            fileId: fileRef.id,
            sectionKey,
            caption: file.name.replace(/\.[^.]+$/, ''),
            altText: `${projectName} - ${file.name}`,
            placement: 'after_section',
          },
        ],
      }))
      message.success(`参考图片“${file.name}”已上传`)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '参考图片上传失败')
    } finally {
      setUploadingSection(null)
    }
  }

  const generateDocuments = async () => {
    const validationErrors = validateTechnicalDocument(draft)
    if (validationErrors.length) {
      Modal.warning({
        title: '生成配置尚不完整',
        content: (
          <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-[#475569]">
            {validationErrors.map(error => <li key={error}>{error}</li>)}
          </ul>
        ),
      })
      return
    }

    setGenerating(true)
    setGenerationJob(null)
    try {
      const initial = await getBidApi().generateDocuments(
        taskId,
        {
          mode: outputMode,
          sections: ['qualification', 'commercial', 'technical'],
          templateMode: 'tender_requirement',
          includeWatermark,
          technicalDocument: normalizeTechnicalDocument(draft),
        },
        newIdempotencyKey('generate-document'),
      )
      const completed = await waitForBidJob(initial, { onChange: setGenerationJob })
      await reload()
      const versionNumber = (completed.result as { versionNumber?: number } | undefined)?.versionNumber
      message.success(versionNumber
        ? `投标文档 v${versionNumber} 已生成`
        : `逐段生成已完成（任务 ${completed.id}）`)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '文档生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const downloadVersion = async (version: DocumentVersion) => {
    try {
      const blob = await getBidApi().downloadDocumentBlob(taskId, version.documentId)
      downloadBlob(blob, version.file.fileName || `${projectName}-投标文件.docx`)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '文档下载失败')
    }
  }

  const downloadLatest = async () => {
    if (!versions[0]) {
      message.warning('暂无可下载版本')
      return
    }
    await downloadVersion(versions[0])
  }

  const compareWithLatest = async (version: DocumentVersion) => {
    if (!latestId || version.id === latestId) {
      message.info('请选择非最新版本进行对比')
      return
    }
    try {
      const diff = await getBidApi().compareDocumentVersions(taskId, version.id, latestId)
      Modal.info({
        title: `版本对比 v${diff.from.versionNumber} → v${diff.to.versionNumber}`,
        width: 680,
        content: (
          <div className="mt-3 max-h-[420px] space-y-2 overflow-y-auto">
            {diff.changes.length === 0 && <Alert type="info" showIcon message="两个版本没有结构化差异" />}
            {diff.changes.map((change, index) => (
              <div key={`${change.section}-${index}`} className="rounded-lg border border-[#E2E8F0] p-3 text-xs">
                <div className="mb-1 font-medium text-[#1E293B]">
                  {change.section}
                  <Tag
                    className="ml-2 !text-[10px]"
                    color={change.type === 'added' ? 'green' : change.type === 'removed' ? 'red' : 'blue'}
                  >
                    {change.type}
                  </Tag>
                </div>
                {change.before && <div className="text-[#94A3B8]">修改前：{change.before}</div>}
                {change.after && <div className="text-[#334155]">修改后：{change.after}</div>}
              </div>
            ))}
          </div>
        ),
      })
    } catch (error) {
      message.error(error instanceof Error ? error.message : '版本对比失败')
    }
  }

  const rollback = (version: DocumentVersion) => {
    Modal.confirm({
      title: `回滚到 v${version.versionNumber}？`,
      content: '系统会基于所选版本创建一个新版本，原有版本不会被覆盖。',
      okText: '确认回滚',
      cancelText: '取消',
      onOk: async () => {
        try {
          const initial = await getBidApi().rollbackDocumentVersion(
            taskId,
            version.id,
            `回滚到 v${version.versionNumber}`,
            newIdempotencyKey('rollback-document'),
          )
          await waitForBidJob(initial, { onChange: setGenerationJob })
          await reload()
          message.success(`已基于 v${version.versionNumber} 创建新版本`)
        } catch (error) {
          message.error(error instanceof Error ? error.message : '回滚失败')
          throw error
        }
      },
    })
  }

  const outputCards = [
    { name: '资格标', icon: FileCheck2, color: '#2563EB', bg: '#EFF6FF', description: '资质与符合性响应' },
    { name: '商务标', icon: FileText, color: '#D97706', bg: '#FFFBEB', description: '商务条款与报价响应' },
    { name: '技术标', icon: Bot, color: '#16A34A', bg: '#F0FDF4', description: `${totalParagraphs} 段，约 ${estimatedWords.toLocaleString()} 字` },
  ]

  return (
    <div className="space-y-4 pb-4">
      <div className="rounded-xl border border-[#BFDBFE] bg-gradient-to-r from-[#EFF6FF] to-[#F8FAFC] p-4">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div className="mb-1 flex items-center gap-2 text-sm font-semibold text-[#1E293B]">
              <Bot size={17} className="text-[#2563EB]" />
              大模型逐段生成技术文档
              <Tag color="blue" className="!m-0">格式锁定</Tag>
            </div>
            <p className="max-w-3xl text-xs leading-5 text-[#64748B]">
              系统先按下方格式规划章节，再逐章、逐段调用模型。每次调用只携带招标要求、当前章节、最近段落和图片说明，
              避免长文档超出上下文；已完成段落会形成检查点，可在任务重试时继续生成。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button loading={loading} icon={<RefreshCw size={14} />} onClick={() => void reload()}>
              刷新版本
            </Button>
            <Button icon={<DownloadIcon size={14} />} disabled={!versions.length} onClick={() => void downloadLatest()}>
              下载最新版本
            </Button>
            <Button
              type="primary"
              loading={generating}
              icon={<FileOutput size={14} />}
              data-testid={BID_TEST_IDS.outputGenerate}
              onClick={() => void generateDocuments()}
            >
              按当前格式生成全部标书
            </Button>
          </div>
        </div>
        {generationJob && (
          <div className="mt-4 rounded-lg bg-white/80 px-3 py-2">
            <div className="mb-1 flex items-center justify-between text-xs">
              <span className="text-[#475569]">{generationJob.currentStep || '任务处理中'}</span>
              <span className="font-mono text-[#64748B]">{generationJob.id}</span>
            </div>
            <Progress
              percent={generationJob.progressPercent}
              size="small"
              status={generationJob.status === 'failed' ? 'exception' : generationJob.status === 'succeeded' ? 'success' : 'active'}
            />
          </div>
        )}
      </div>

      <div className="rounded-xl border border-[#E2E8F0] bg-white p-4">
        <div className="mb-4 grid gap-3 lg:grid-cols-3">
          <label className="space-y-1 text-xs text-[#64748B]">
            <span className="font-medium text-[#334155]">给定格式 / 模板名称</span>
            <Input
              value={draft.templateName}
              maxLength={200}
              onChange={event => setDraft(previous => ({ ...previous, templateName: event.target.value }))}
            />
          </label>
          <label className="space-y-1 text-xs text-[#64748B]">
            <span className="font-medium text-[#334155]">输出方式</span>
            <Select<OutputMode>
              className="w-full"
              value={outputMode}
              onChange={setOutputMode}
              options={[
                { value: 'split', label: '资格标、商务标、技术标分别输出' },
                { value: 'merged', label: '合并为一份完整标书' },
              ]}
            />
          </label>
          <div className="flex items-end gap-5 pb-1 text-xs text-[#475569]">
            <label className="flex items-center gap-2">
              <Switch size="small" checked={includeWatermark} onChange={setIncludeWatermark} />
              添加内部水印
            </label>
            <label className="flex items-center gap-2">
              <Switch
                size="small"
                checked={draft.requireEvidence}
                onChange={requireEvidence => setDraft(previous => ({ ...previous, requireEvidence }))}
              />
              要求引用依据
            </label>
          </div>
        </div>

        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-sm font-semibold text-[#1E293B]">技术文档章节格式</h3>
            <p className="mt-0.5 text-xs text-[#94A3B8]">顺序即最终 Word 目录顺序；每段独立调用一次大模型。</p>
          </div>
          <Button size="small" icon={<Plus size={13} />} onClick={addSection}>新增章节</Button>
        </div>

        <div className="space-y-3">
          {draft.sections.map((section, index) => {
            const sectionImages = draft.referenceImages.filter(image => image.sectionKey === section.key)
            return (
              <div key={section.key} className="rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-3">
                <div className="mb-3 flex items-center gap-2">
                  <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[#DBEAFE] text-xs font-semibold text-[#1D4ED8]">
                    {index + 1}
                  </span>
                  <Input
                    className="flex-1"
                    value={section.heading}
                    maxLength={200}
                    placeholder="章节标题"
                    onChange={event => updateSection(section.key, { heading: event.target.value })}
                  />
                  <label className="flex items-center gap-1.5 whitespace-nowrap text-xs text-[#64748B]">
                    <Switch
                      size="small"
                      checked={section.required}
                      onChange={required => updateSection(section.key, { required })}
                    />
                    必须生成
                  </label>
                  <Button
                    type="text"
                    danger
                    aria-label={`删除章节 ${section.heading}`}
                    icon={<Trash2 size={14} />}
                    onClick={() => removeSection(section.key)}
                  />
                </div>
                <Input.TextArea
                  rows={2}
                  maxLength={4000}
                  showCount
                  value={section.instructions}
                  placeholder="说明该章节必须响应的招标要求、写作口径和证据要求"
                  onChange={event => updateSection(section.key, { instructions: event.target.value })}
                />
                <div className="mt-3 flex flex-wrap items-center gap-4">
                  <label className="flex items-center gap-2 text-xs text-[#64748B]">
                    标题级别
                    <Select
                      className="w-24"
                      size="small"
                      value={section.headingLevel}
                      onChange={headingLevel => updateSection(section.key, { headingLevel })}
                      options={[1, 2, 3].map(value => ({ value, label: `${value} 级` }))}
                    />
                  </label>
                  <label className="flex items-center gap-2 text-xs text-[#64748B]">
                    目标段落
                    <InputNumber
                      size="small"
                      min={1}
                      max={30}
                      value={section.targetParagraphs}
                      onChange={value => updateSection(section.key, { targetParagraphs: Number(value || 1) })}
                    />
                  </label>
                  <label className="flex items-center gap-2 text-xs text-[#64748B]">
                    每段目标字数
                    <InputNumber
                      size="small"
                      min={80}
                      max={1500}
                      step={50}
                      value={section.targetWordsPerParagraph}
                      onChange={value => updateSection(section.key, { targetWordsPerParagraph: Number(value || 80) })}
                    />
                  </label>
                  <AntUpload
                    accept=".png,.jpg,.jpeg,image/png,image/jpeg"
                    showUploadList={false}
                    beforeUpload={file => {
                      void handleImageUpload(section.key, file)
                      return AntUpload.LIST_IGNORE
                    }}
                  >
                    <Button
                      size="small"
                      loading={uploadingSection === section.key}
                      icon={<ImagePlus size={13} />}
                    >
                      添加参考图片
                    </Button>
                  </AntUpload>
                </div>

                {uploadingSection === section.key && (
                  <div className="mt-3 rounded-lg bg-white px-3 py-2">
                    <div className="mb-1 flex items-center justify-between text-xs text-[#64748B]">
                      <span>正在上传并校验图片</span>
                      <Button type="link" size="small" onClick={() => void cancelImageUpload()}>取消</Button>
                    </div>
                    <Progress percent={imageUploadProgress.percent} size="small" />
                    {imageUploadError && <div className="text-xs text-[#DC2626]">{imageUploadError}</div>}
                  </div>
                )}

                {sectionImages.length > 0 && (
                  <div className="mt-3 space-y-2 border-t border-[#E2E8F0] pt-3">
                    {sectionImages.map(image => (
                      <div key={image.fileId} className="grid items-center gap-2 rounded-lg bg-white p-2 md:grid-cols-[minmax(160px,1fr)_150px_120px_32px]">
                        <div className="min-w-0">
                          <div className="mb-1 flex items-center gap-1 text-[11px] text-[#94A3B8]">
                            <FileImage size={12} />
                            <span className="truncate">{imageNames[image.fileId] || image.fileId}</span>
                          </div>
                          <Input
                            size="small"
                            value={image.caption}
                            placeholder="图片标题"
                            onChange={event => updateImage(image.fileId, { caption: event.target.value })}
                          />
                        </div>
                        <Select
                          size="small"
                          value={image.placement}
                          onChange={placement => updateImage(image.fileId, {
                            placement,
                            afterParagraphIndex: placement === 'after_paragraph' ? 1 : undefined,
                          })}
                          options={[
                            { value: 'before_section', label: '章节标题前' },
                            { value: 'after_paragraph', label: '指定段落后' },
                            { value: 'after_section', label: '章节末尾' },
                          ]}
                        />
                        {image.placement === 'after_paragraph' ? (
                          <InputNumber
                            size="small"
                            className="w-full"
                            min={1}
                            max={section.targetParagraphs}
                            addonBefore="第"
                            addonAfter="段"
                            value={image.afterParagraphIndex || 1}
                            onChange={value => updateImage(image.fileId, { afterParagraphIndex: Number(value || 1) })}
                          />
                        ) : <span className="text-center text-xs text-[#CBD5E1]">无需段落锚点</span>}
                        <Button
                          type="text"
                          danger
                          aria-label={`删除图片 ${image.caption}`}
                          icon={<Trash2 size={13} />}
                          onClick={() => removeImage(image.fileId)}
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        <Collapse
          ghost
          className="mt-3 !rounded-lg !bg-[#F8FAFC]"
          items={[{
            key: 'advanced',
            label: <span className="text-xs font-medium text-[#475569]">长文档上下文与一致性设置</span>,
            children: (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <label className="space-y-1 text-xs text-[#64748B]">
                  <span>单次上下文字符上限</span>
                  <InputNumber
                    className="w-full"
                    min={2000}
                    max={200000}
                    step={2000}
                    value={draft.contextWindowCharacters}
                    onChange={contextWindowCharacters => setDraft(previous => ({
                      ...previous,
                      contextWindowCharacters: Number(contextWindowCharacters || 2000),
                    }))}
                  />
                </label>
                <label className="space-y-1 text-xs text-[#64748B]">
                  <span>携带前文段落数</span>
                  <InputNumber
                    className="w-full"
                    min={0}
                    max={10}
                    value={draft.carryForwardParagraphs}
                    onChange={carryForwardParagraphs => setDraft(previous => ({
                      ...previous,
                      carryForwardParagraphs: Number(carryForwardParagraphs || 0),
                    }))}
                  />
                </label>
                <label className="flex items-center gap-2 pt-6 text-xs text-[#475569]">
                  <Checkbox
                    checked={draft.preserveHeadingNumbering}
                    onChange={event => setDraft(previous => ({
                      ...previous,
                      preserveHeadingNumbering: event.target.checked,
                    }))}
                  />
                  保持章节编号连续
                </label>
                <div className="pt-5 text-xs leading-5 text-[#64748B]">
                  共 {draft.sections.length} 章 / {totalParagraphs} 段<br />
                  预计约 {estimatedWords.toLocaleString()} 字 / {draft.referenceImages.length} 张图片
                </div>
              </div>
            ),
          }]}
        />
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        {outputCards.map(card => {
          const Icon = card.icon
          return (
            <div key={card.name} className="rounded-xl border border-[#E2E8F0] bg-white p-4">
              <div className="flex items-center gap-2">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg" style={{ background: card.bg }}>
                  <Icon size={20} color={card.color} />
                </div>
                <div>
                  <div className="text-sm font-medium text-[#1E293B]">{card.name}</div>
                  <div className="text-xs text-[#94A3B8]">{card.description}</div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="rounded-xl bg-[#F8FAFC] p-4">
        <div className="mb-3 flex items-center gap-1.5 text-sm font-medium text-[#1E293B]">
          <History size={15} /> 版本历史
          <Tag className="!ml-1">{versions.length}</Tag>
        </div>
        <div className="space-y-2">
          {versions.map((version, index) => {
            const isLatest = index === 0
            return (
              <div key={version.id} className="flex items-start gap-3 rounded-lg border border-[#F1F5F9] bg-white p-3">
                <div className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg ${isLatest ? 'bg-[#F0FDF4]' : 'bg-[#F8FAFC]'}`}>
                  <FileText size={15} color={isLatest ? '#16A34A' : '#94A3B8'} />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="mb-0.5 flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-medium text-[#1E293B]">v{version.versionNumber}</span>
                    {isLatest && <Tag color="green" className="rounded border-0 text-xs">最新</Tag>}
                    <span className="text-xs text-[#94A3B8]">{version.file.fileName}</span>
                    <span className="text-xs text-[#94A3B8]">{version.createdBy.name}</span>
                  </div>
                  <div className="truncate text-xs text-[#64748B]">{version.changeSummary}</div>
                  <div className="text-xs text-[#CBD5E1]">
                    {new Date(version.createdAt).toLocaleString('zh-CN', { hour12: false })}
                  </div>
                </div>
                <div className="flex flex-wrap justify-end gap-1">
                  {!isLatest && (
                    <Button
                      data-testid={BID_TEST_IDS.outputRollback}
                      size="small"
                      type="text"
                      className="text-xs"
                      onClick={() => rollback(version)}
                    >
                      回滚
                    </Button>
                  )}
                  {!isLatest && (
                    <Button
                      data-testid={BID_TEST_IDS.outputCompare}
                      size="small"
                      type="text"
                      className="text-xs"
                      onClick={() => void compareWithLatest(version)}
                    >
                      对比
                    </Button>
                  )}
                  <Button size="small" type="text" className="text-xs" onClick={() => void downloadVersion(version)}>
                    下载
                  </Button>
                </div>
              </div>
            )
          })}
          {!versions.length && !loading && (
            <div className="rounded-lg border border-dashed border-[#CBD5E1] bg-white py-8 text-center text-xs text-[#94A3B8]">
              暂无版本。确认上方章节格式后，点击“按当前格式生成全部标书”。
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
