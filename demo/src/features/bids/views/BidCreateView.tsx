import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Alert, Button, Card, DatePicker, Form, Input, InputNumber, Progress, Result, Steps, Upload, message } from 'antd'
import { ArrowLeft, ArrowRight, CheckCircle2, FileSearch, FileText, Plus, Save, Sparkles, UploadCloud } from 'lucide-react'
import dayjs from 'dayjs'
import { currentUser } from '../../../mock/data'
import { useDemo } from '../../../context/DemoContext'
import { BID_ACCEPT_UPLOAD_TYPES, BID_MAX_UPLOAD_BYTES, BID_TEST_IDS } from '../constants'
import { clearBidCreateDraft, loadBidCreateDraft, saveBidCreateDraft } from '../adapters/createDraftStorage'
import { useResumableUpload } from '../hooks/useResumableUpload'
import { extractTenderFieldsFromFile, toFormValuesFromExtract } from '../hooks/extractTenderFields'
import type { BidParseOutcome } from '../types'
import { useBidUiState } from '../hooks/useBidUiState'
import {
  BidConflictState,
  BidErrorState,
  BidForbiddenState,
  BidLoadingState,
  BidTimeoutState,
} from '../components/BidPageStates'
import { BidUiStateSwitcher } from '../components/BidUiStateSwitcher'

const { Dragger } = Upload

export default function BidCreateView() {
  const navigate = useNavigate()
  const { bidTasks, addBidTask } = useDemo()
  const [form] = Form.useForm()
  const [current, setCurrent] = useState(0)
  const [fileList, setFileList] = useState<any[]>(() => {
    const draft = loadBidCreateDraft()
    return draft?.fileName
      ? [{ uid: 'draft-file', name: draft.fileName, status: 'done', size: draft.fileSize || 0 }]
      : []
  })
  const [parseOutcome, setParseOutcome] = useState<BidParseOutcome>('idle')
  const [tenderFileId, setTenderFileId] = useState<string | undefined>(() => loadBidCreateDraft()?.tenderFileId)
  const failNextParse = useRef(false)
  const draftNoticeShown = useRef(false)
  const { progress: uploadProgress, upload: resumableUpload, cancel: cancelUpload, reset: resetUpload } = useResumableUpload()
  const { status: uiStatus, override, setUiOverride, retry } = useBidUiState({ bootstrapMs: 200 })

  useEffect(() => {
    if (draftNoticeShown.current) return
    draftNoticeShown.current = true
    const draft = loadBidCreateDraft()
    if (!draft) return
    const draftDeadline = draft.deadline ? dayjs(draft.deadline) : null
    form.setFieldsValue({
      projectName: draft.projectName ?? '',
      tenderNo: draft.tenderNo ?? '',
      tenderEntity: draft.tenderEntity ?? '',
      deadline: draftDeadline?.isValid() ? draftDeadline : null,
      budget: draft.budget ?? null,
    })
    const timer = window.setTimeout(() => message.info('已恢复本地草稿'), 0)
    return () => window.clearTimeout(timer)
  }, [form])

  const persistDraft = async () => {
    const values = form.getFieldsValue(true)
    saveBidCreateDraft({
      projectName: values.projectName,
      tenderNo: values.tenderNo,
      tenderEntity: values.tenderEntity,
      deadline: values.deadline?.toISOString?.() || values.deadline,
      budget: values.budget,
      fileName: fileList[0]?.name,
      fileSize: fileList[0]?.size,
      tenderFileId,
    })
    message.success('草稿已保存到本机')
  }

  const fillExample = () => {
    form.setFieldsValue({
      projectName: '某市政务云扩容采购项目',
      tenderNo: `DEMO-${new Date().getFullYear()}-001`,
      tenderEntity: '某市政务服务数据管理局',
      deadline: dayjs().add(14, 'day'),
      budget: 9800000,
    })
    setFileList([{ uid: 'demo-file', name: '政务云扩容项目招标文件.pdf', status: 'done', size: 4.8 * 1024 * 1024 }])
    setTenderFileId('file-demo-example')
    resetUpload()
    message.success('已填入示例招标文件和项目信息')
  }

  const startParsing = async (forceFail = false) => {
    try {
      await form.validateFields()
    } catch {
      message.warning('请先填写完整的项目信息')
      return
    }
    if (!fileList.length) {
      message.warning('请先上传招标文件')
      return
    }
    if (!tenderFileId) {
      message.warning('招标文件仍在上传或未完成续传，请稍候')
      return
    }
    setCurrent(1)
    setParseOutcome('running')
    const shouldFail = forceFail || failNextParse.current
    failNextParse.current = false
    window.setTimeout(() => {
      if (shouldFail) {
        setParseOutcome('failed')
        message.error('招标文件解析失败，请重试或更换文件')
        return
      }
      setParseOutcome('success')
    }, 1200)
  }

  const createTask = () => {
    const values = form.getFieldsValue(true)
    const nextNumber = String(bidTasks.length + 1).padStart(3, '0')
    const id = `TASK-2026-${nextNumber}`
    addBidTask({
      id,
      projectName: values.projectName,
      tenderNo: values.tenderNo,
      deadline: values.deadline?.format('YYYY-MM-DD') || dayjs().add(14, 'day').format('YYYY-MM-DD'),
      status: 'material_prep',
      currentStep: 3,
      progress: 35,
      assignee: currentUser.name,
      tenderFileId,
      materialTotal: 23,
      materialHave: 13,
      materialMissing: 10,
      tenderEntity: values.tenderEntity,
      createdAt: dayjs().format('YYYY-MM-DD'),
      tags: ['Demo新建', 'AI已解析'],
    })
    clearBidCreateDraft()
    message.success('投标任务已创建，AI材料清单已生成')
    navigate(`/tasks/${id}`)
  }

  const parsing = parseOutcome === 'running'
  const parsed = parseOutcome === 'success'
  const parseFailed = parseOutcome === 'failed'

  if (uiStatus === 'loading') {
    return (
      <div className="p-4 md:p-6 max-w-[980px] mx-auto" data-testid={BID_TEST_IDS.create}>
        <div className="flex justify-end mb-3"><BidUiStateSwitcher value={override} onChange={setUiOverride} /></div>
        <BidLoadingState tip="正在准备新建投标表单…" />
      </div>
    )
  }
  if (uiStatus === 'error') {
    return (
      <div className="p-4 md:p-6 max-w-[980px] mx-auto" data-testid={BID_TEST_IDS.create}>
        <div className="flex justify-end mb-3"><BidUiStateSwitcher value={override} onChange={setUiOverride} /></div>
        <BidErrorState onRetry={retry} message="创建页依赖数据加载失败。" />
      </div>
    )
  }
  if (uiStatus === 'forbidden') {
    return (
      <div className="p-4 md:p-6 max-w-[980px] mx-auto" data-testid={BID_TEST_IDS.create}>
        <div className="flex justify-end mb-3"><BidUiStateSwitcher value={override} onChange={setUiOverride} /></div>
        <BidForbiddenState onBack={() => navigate('/dashboard')} />
      </div>
    )
  }
  if (uiStatus === 'timeout') {
    return (
      <div className="p-4 md:p-6 max-w-[980px] mx-auto" data-testid={BID_TEST_IDS.create}>
        <div className="flex justify-end mb-3"><BidUiStateSwitcher value={override} onChange={setUiOverride} /></div>
        <BidTimeoutState onRetry={retry} />
      </div>
    )
  }
  if (uiStatus === 'conflict') {
    return (
      <div className="p-4 md:p-6 max-w-[980px] mx-auto" data-testid={BID_TEST_IDS.create}>
        <div className="flex justify-end mb-3"><BidUiStateSwitcher value={override} onChange={setUiOverride} /></div>
        <BidConflictState onRetry={retry} message="草稿版本冲突，请刷新后重新填写。" />
      </div>
    )
  }

  return (
    <div className="p-4 md:p-6 max-w-[980px] mx-auto" data-testid={BID_TEST_IDS.create}>
      <div className="flex items-center justify-between gap-3 mb-5">
        <div className="flex items-center gap-3">
          <Button type="text" icon={<ArrowLeft size={16} />} onClick={() => navigate('/dashboard')}>返回工作台</Button>
          <div>
            <h1 className="text-xl font-semibold text-[#1E293B]">新建投标任务</h1>
            <p className="text-sm text-[#64748B] mt-0.5">上传招标文件，由 AI 解析并生成首版材料清单</p>
          </div>
        </div>
        <BidUiStateSwitcher value={override} onChange={setUiOverride} />
      </div>

      <Card className="!border-[#E2E8F0] !shadow-none mb-4">
        <Steps
          current={current}
          items={[
            { title: '上传与项目信息', icon: <UploadCloud size={16} /> },
            { title: 'AI解析', icon: <FileSearch size={16} /> },
            { title: '确认创建', icon: <CheckCircle2 size={16} /> },
          ]}
        />
      </Card>

      <Card className="!border-[#E2E8F0] !shadow-none">
        {current === 0 && (
          <div>
            <div className="flex items-center justify-between mb-4 gap-2 flex-wrap">
              <h2 className="text-base font-semibold text-[#1E293B]">招标文件与项目信息</h2>
              <div className="flex gap-2">
                <Button icon={<Save size={14} />} onClick={persistDraft} data-testid={BID_TEST_IDS.createSaveDraft}>保存草稿</Button>
                <Button icon={<Sparkles size={14} />} onClick={fillExample}>填入示例数据</Button>
              </div>
            </div>
            <Dragger
              accept={BID_ACCEPT_UPLOAD_TYPES}
              maxCount={1}
              fileList={fileList}
              disabled={uploadProgress.status === 'hashing' || uploadProgress.status === 'uploading' || uploadProgress.status === 'verifying' || uploadProgress.status === 'scanning'}
              beforeUpload={file => {
                if (file.size > BID_MAX_UPLOAD_BYTES) {
                  message.error('单文件不能超过 200MB')
                  return Upload.LIST_IGNORE
                }
                setFileList([file as any])
                setTenderFileId(undefined)
                void (async () => {
                  try {
                    const ref = await resumableUpload(file, 'tender')
                    setTenderFileId(ref.id)
                    message.success(`续传完成：${ref.fileName}`)
                  } catch (err) {
                    if (err instanceof Error && err.message === 'UPLOAD_ABORTED') {
                      message.info('已取消上传')
                    } else {
                      message.error('文件续传失败，请重试')
                    }
                    return
                  }
                  const extract = await extractTenderFieldsFromFile(file)
                  form.setFieldsValue(toFormValuesFromExtract(extract))
                  form.setFields([
                    { name: 'projectName', errors: [] },
                    { name: 'tenderNo', errors: [] },
                    { name: 'tenderEntity', errors: [] },
                    { name: 'deadline', errors: [] },
                    { name: 'budget', errors: [] },
                  ])
                  const filled = Object.values(extract).filter(value => value !== undefined && value !== '').length
                  if (filled > 0) {
                    message.success(`已从文件中识别 ${filled} 项信息，未识别字段保持为空`)
                  } else {
                    message.info('未从文件中识别到结构化字段，表单保持为空（PDF/Word 需后续 AI 解析）')
                  }
                })()
                return false
              }}
              onRemove={() => {
                void cancelUpload()
                resetUpload()
                setFileList([])
                setTenderFileId(undefined)
                form.setFieldsValue(toFormValuesFromExtract({}))
              }}
              className="!mb-5"
            >
              <UploadCloud size={36} className="mx-auto text-[#2563EB] mb-2" />
              <p className="text-sm text-[#1E293B]">点击或拖拽招标文件到此处</p>
              <p className="text-xs text-[#94A3B8] mt-1">支持 PDF、Word、Excel、PPT、图片和压缩包，最大 200MB；按分片续传协议上传，仅填充文件内可识别字段</p>
            </Dragger>
            {(uploadProgress.status !== 'idle' || tenderFileId) && (
              <div className="mb-5 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] p-3" data-testid={BID_TEST_IDS.createUploadProgress}>
                <div className="flex items-center justify-between text-xs text-[#64748B] mb-2">
                  <span>
                    {uploadProgress.status === 'completed' || tenderFileId
                      ? `已就绪 fileId=${tenderFileId || ''}`
                      : `续传中：${uploadProgress.status}（${uploadProgress.uploadedParts}/${uploadProgress.totalParts || '?'} 分片）`}
                  </span>
                  {(uploadProgress.status === 'uploading' || uploadProgress.status === 'hashing') && (
                    <Button type="link" size="small" className="!px-0 !h-auto text-xs" onClick={() => void cancelUpload()}>取消</Button>
                  )}
                </div>
                <Progress percent={uploadProgress.status === 'completed' || tenderFileId ? 100 : uploadProgress.percent} size="small" status={uploadProgress.status === 'failed' ? 'exception' : undefined} />
              </div>
            )}

            <Form form={form} layout="vertical">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4">
                <Form.Item name="projectName" label="项目名称" rules={[{ required: true, message: '请输入项目名称' }]}>
                  <Input placeholder="请输入项目名称" />
                </Form.Item>
                <Form.Item name="tenderNo" label="招标编号" rules={[{ required: true, message: '请输入招标编号' }]}>
                  <Input placeholder="请输入招标编号" />
                </Form.Item>
                <Form.Item name="tenderEntity" label="招标方" rules={[{ required: true, message: '请输入招标方' }]}>
                  <Input placeholder="请输入招标方名称" />
                </Form.Item>
                <Form.Item
                  name="deadline"
                  label="投标截止时间"
                  rules={[{ required: true, message: '请选择截止时间' }]}
                  getValueProps={(value) => {
                    if (!value) return { value: null }
                    const parsed = dayjs.isDayjs(value) ? value : dayjs(value)
                    return { value: parsed.isValid() ? parsed : null }
                  }}
                  normalize={(value) => {
                    if (!value) return null
                    const parsed = dayjs.isDayjs(value) ? value : dayjs(value)
                    return parsed.isValid() ? parsed : null
                  }}
                >
                  <DatePicker
                    showTime
                    format="YYYY-MM-DD HH:mm"
                    className="!w-full"
                    placeholder="请选择截止时间"
                    allowClear
                    inputReadOnly
                    getPopupContainer={() => document.body}
                  />
                </Form.Item>
                <Form.Item name="budget" label="预算金额（元）" className="md:col-span-2">
                  <InputNumber min={0} className="!w-full" placeholder="请输入预算金额" />
                </Form.Item>
              </div>
            </Form>
          </div>
        )}

        {current === 1 && (
          <div className="py-5 max-w-[680px] mx-auto">
            {parsing && (
              <div className="text-center">
                <div className="w-14 h-14 rounded-2xl bg-[#EFF6FF] flex items-center justify-center mx-auto mb-4">
                  <FileSearch size={28} className="text-[#2563EB] animate-pulse" />
                </div>
                <h2 className="text-lg font-semibold text-[#1E293B] mb-2">AI 正在解析招标文件</h2>
                <p className="text-sm text-[#64748B] mb-5">提取评分项、废标条款、资质要求并生成材料清单</p>
                <Progress percent={76} status="active" strokeColor="#2563EB" />
              </div>
            )}
            {parseFailed && (
              <Result
                status="error"
                title="招标文件解析失败"
                subTitle="可能是文件损坏、格式不支持或解析服务超时。可重试或返回更换文件。"
                extra={[
                  <Button key="retry" type="primary" data-testid={BID_TEST_IDS.createRetryParse} onClick={() => startParsing(false)}>重试解析</Button>,
                  <Button key="back" onClick={() => { setCurrent(0); setParseOutcome('idle') }}>返回修改</Button>,
                ]}
              />
            )}
            {parsed && (
              <Result
                status="success"
                title="招标文件解析完成"
                subTitle="已提取 8 项评分标准、6 项废标条款，并生成 23 项材料清单"
                extra={<Button type="primary" onClick={() => setCurrent(2)}>查看解析结果 <ArrowRight size={14} /></Button>}
              />
            )}
          </div>
        )}

        {current === 2 && (
          <div>
            <div className="flex items-center gap-2 mb-4">
              <FileText size={18} className="text-[#2563EB]" />
              <h2 className="text-base font-semibold text-[#1E293B]">解析结果确认</h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
              {[
                ['材料清单', '23 项'],
                ['资质库匹配', '13 项'],
                ['待准备材料', '10 项'],
                ['废标条款', '6 项'],
              ].map(([label, value]) => (
                <div key={label} className="rounded-lg bg-[#F8FAFC] p-4">
                  <div className="text-xl font-semibold text-[#1E293B]">{value}</div>
                  <div className="text-xs text-[#64748B] mt-1">{label}</div>
                </div>
              ))}
            </div>
            <Alert type="info" showIcon message="创建后可在任务详情中编辑清单、上传材料并重新发起 AI 审核" />
          </div>
        )}
      </Card>

      <div className="flex justify-between mt-4">
        <Button disabled={current === 0 || parsing} onClick={() => setCurrent(value => value - 1)} icon={<ArrowLeft size={14} />}>上一步</Button>
        {current === 0 && <Button type="primary" data-testid={BID_TEST_IDS.createStartParse} onClick={() => startParsing(false)}>开始 AI 解析 <ArrowRight size={14} /></Button>}
        {current === 1 && parsed && <Button type="primary" onClick={() => setCurrent(2)}>下一步 <ArrowRight size={14} /></Button>}
        {current === 2 && <Button type="primary" icon={<Plus size={14} />} data-testid={BID_TEST_IDS.createSubmit} onClick={createTask}>创建投标任务</Button>}
      </div>
    </div>
  )
}
