import { useEffect, useRef, useState } from 'react'
import { Card, Steps, Button, Input, InputNumber, DatePicker, Form, Switch, Select, Table, Tag, Alert, Divider, Space, message, Modal } from 'antd'
import { Megaphone, ClipboardList, Scale, Settings2, Rocket, Plus, Minus, Copy, CheckCircle2, Clock, FileText, Link2, ArrowLeft, ArrowRight, Save, Eye, Import, X } from 'lucide-react'
import dayjs from 'dayjs'
import { requiredMaterialTemplates, scoringCriteria, evalCategoryLabels } from '../mock/evaluationData'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useDemo } from '../context/DemoContext'
import { copyText } from '../utils/demoActions'

const { TextArea } = Input
const { RangePicker } = DatePicker
const DRAFT_KEY = 'bid-platform-evaluation-draft-v2'

export default function EvaluationCreate() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const { addEvaluationTask, bidTasks, getTaskMaterials } = useDemo()
  const [current, setCurrent] = useState(0)
  const [materials, setMaterials] = useState(requiredMaterialTemplates)
  const [scoringItems, setScoringItems] = useState(() => scoringCriteria.map(item => item.id === 'SC01' ? { ...item, weight: 25, maxScore: 25, desc: item.desc.replace(/× 30/g, '× 25') } : item))
  const [published, setPublished] = useState(false)
  const [publishedTaskId, setPublishedTaskId] = useState('')
  const [supplierEmails, setSupplierEmails] = useState<string[]>(['supplier-a@example.com', 'supplier-b@example.com'])
  const [reviewers, setReviewers] = useState<string[]>(['刘德海'])
  const [importProjectId, setImportProjectId] = useState<string>()
  const [importedFrom, setImportedFrom] = useState<string>()
  const [hasDraft, setHasDraft] = useState(() => Boolean(localStorage.getItem(DRAFT_KEY)))
  const [lastSaved, setLastSaved] = useState('')
  const [dirty, setDirty] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)
  const initialSourceLoaded = useRef(false)
  const [form] = Form.useForm()
  const [reviewConfig, setReviewConfig] = useState({
    multiRoundPricing: true,
    maxRounds: 3,
    supplementDeadline: 120,
    allowModify: false,
    notifyOnMissing: true,
    closeAfterDeadline: true,
  })

  const markDirty = () => setDirty(true)

  const importProject = (taskId: string, notify = true) => {
    const task = bidTasks.find(item => item.id === taskId)
    if (!task) {
      message.warning('未找到可导入的投标项目')
      return
    }
    const categoryMap: Record<string, string> = { qualification: '资质', commercial: '商务', technical: '技术' }
    const importedMaterials = getTaskMaterials(taskId).map((item, index) => ({
      id: `RM${String(index + 1).padStart(2, '0')}`,
      name: item.name,
      category: categoryMap[item.part] || '技术',
      required: item.status !== 'optional',
      isDefault: false,
    }))
    const submitDeadline = dayjs(task.deadline).hour(17).minute(0)
    form.setFieldsValue({
      projectName: task.projectName,
      tenderNo: task.tenderNo,
      tenderEntity: task.tenderEntity,
      submitDeadline,
      evalRange: [submitDeadline.add(1, 'day'), submitDeadline.add(3, 'day')],
      description: `由投标项目 ${task.id} 导入，沿用项目基础信息与材料清单。`,
    })
    setMaterials(importedMaterials)
    setImportProjectId(taskId)
    setImportedFrom(taskId)
    markDirty()
    if (notify) message.success(`已导入“${task.projectName}”及 ${importedMaterials.length} 项材料`)
  }

  useEffect(() => {
    const sourceTaskId = searchParams.get('sourceTask')
    if (sourceTaskId && !initialSourceLoaded.current) {
      initialSourceLoaded.current = true
      importProject(sourceTaskId, false)
      message.success('已从投标项目带入基础信息和材料清单')
    }
  }, [])

  const serializeDraft = () => {
    const values = form.getFieldsValue(true)
    return {
      current,
      values: {
        ...values,
        submitDeadline: values.submitDeadline ? dayjs(values.submitDeadline).toISOString() : null,
        evalRange: values.evalRange?.map((value: any) => dayjs(value).toISOString()) || null,
      },
      materials,
      scoringItems,
      reviewConfig,
      supplierEmails,
      reviewers,
      importedFrom,
      savedAt: new Date().toISOString(),
    }
  }

  const saveDraft = (notify = true) => {
    localStorage.setItem(DRAFT_KEY, JSON.stringify(serializeDraft()))
    const time = dayjs().format('HH:mm:ss')
    setLastSaved(time)
    setHasDraft(true)
    setDirty(false)
    if (notify) message.success('评标任务草稿已保存')
  }

  const restoreDraft = () => {
    try {
      const draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || '')
      form.setFieldsValue({
        ...draft.values,
        submitDeadline: draft.values?.submitDeadline ? dayjs(draft.values.submitDeadline) : null,
        evalRange: draft.values?.evalRange?.map((value: string) => dayjs(value)) || null,
      })
      if (draft.materials) setMaterials(draft.materials)
      if (draft.scoringItems) setScoringItems(draft.scoringItems)
      if (draft.reviewConfig) setReviewConfig(draft.reviewConfig)
      if (draft.supplierEmails) setSupplierEmails(draft.supplierEmails)
      if (draft.reviewers) setReviewers(draft.reviewers)
      if (draft.importedFrom) {
        setImportedFrom(draft.importedFrom)
        setImportProjectId(draft.importedFrom)
      }
      setCurrent(Math.min(draft.current || 0, 4))
      setLastSaved(dayjs(draft.savedAt).format('HH:mm:ss'))
      setDirty(false)
      message.success('已恢复上次保存的草稿')
    } catch {
      localStorage.removeItem(DRAFT_KEY)
      setHasDraft(false)
      message.error('草稿内容无效，已清理')
    }
  }

  useEffect(() => {
    if (!dirty || published) return
    const timer = window.setTimeout(() => saveDraft(false), 900)
    return () => window.clearTimeout(timer)
  }, [dirty, published, current, materials, scoringItems, reviewConfig, supplierEmails, reviewers])

  const steps = [
    { title: '项目信息', icon: Megaphone },
    { title: '材料清单', icon: ClipboardList },
    { title: '评分办法', icon: Scale },
    { title: '评审设置', icon: Settings2 },
    { title: '发布', icon: Rocket },
  ]

  const toggleMaterialRequired = (id: string) => {
    setMaterials(prev => prev.map(m => m.id === id ? { ...m, required: !m.required } : m))
    markDirty()
  }

  const addMaterial = () => {
    const newId = `RM${String(materials.length + 1).padStart(2, '0')}`
    setMaterials(prev => [...prev, { id: newId, name: '新材料项', category: '技术', required: true, isDefault: false }])
    markDirty()
  }

  const removeMaterial = (id: string) => {
    setMaterials(prev => prev.filter(m => m.id !== id))
    markDirty()
  }

  const updateMaterialName = (id: string, name: string) => {
    setMaterials(prev => prev.map(m => m.id === id ? { ...m, name } : m))
    markDirty()
  }

  const updateScoreWeight = (id: string, weight: number) => {
    setScoringItems(prev => prev.map(s => s.id === id ? { ...s, weight, maxScore: weight } : s))
    markDirty()
  }

  const updateReviewConfig = (patch: Partial<typeof reviewConfig>) => {
    setReviewConfig(prev => ({ ...prev, ...patch }))
    markDirty()
  }

  const totalWeight = scoringItems.reduce((sum, s) => sum + s.weight, 0)
  const requiredCount = materials.filter(m => m.required).length

  const portalLink = `${window.location.origin}/evaluation/portal/${publishedTaskId || 'EVAL-DEMO'}`

  const validateCurrentStep = async () => {
    if (current === 0) {
      try {
        await form.validateFields()
      } catch {
        message.warning('请先填写所有必填项目信息')
        return false
      }
    }
    if (current === 2 && totalWeight !== 100) {
      message.warning('评分总权重必须等于 100')
      return false
    }
    if (current === 3 && (!supplierEmails.length || !reviewers.length)) {
      message.warning('请至少配置 1 家受邀供应商和 1 位评审人')
      return false
    }
    return true
  }

  const nextStep = async () => {
    if (await validateCurrentStep()) setCurrent(value => Math.min(value + 1, steps.length - 1))
  }

  const changeStep = async (next: number) => {
    if (next <= current) {
      setCurrent(next)
      return
    }
    if (next !== current + 1) {
      message.info('请按顺序完成配置')
      return
    }
    if (await validateCurrentStep()) setCurrent(next)
  }

  const handlePublish = async () => {
    if (totalWeight !== 100 || !supplierEmails.length || !reviewers.length) {
      message.warning('请检查评分权重、供应商与评审人配置')
      return
    }
    const values = form.getFieldsValue(true)
    if (!values.projectName || !values.tenderNo || !values.tenderEntity || !values.submitDeadline) {
      setCurrent(0)
      message.warning('项目信息不完整，请补充后发布')
      return
    }
    const taskId = `EVAL-${dayjs().format('YYYYMMDD-HHmmss')}`
    addEvaluationTask({
      id: taskId,
      projectName: values.projectName,
      tenderNo: values.tenderNo,
      tenderEntity: values.tenderEntity,
      budget: Number(values.budget || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 }),
      deadline: dayjs(values.submitDeadline).format('YYYY-MM-DD'),
      status: 'collecting',
      currentStep: 2,
      progress: 15,
      assignee: reviewers[0],
      bidderCount: supplierEmails.length,
      createdAt: dayjs().format('YYYY-MM-DD'),
      tags: ['新发布', '材料收集中'],
    })
    setPublishedTaskId(taskId)
    setPublished(true)
    localStorage.removeItem(DRAFT_KEY)
    setHasDraft(false)
    setDirty(false)
    message.success('评标任务已发布，供应商入口链接已生成')
  }

  const confirmPublish = async () => {
    try {
      await form.validateFields()
    } catch {
      setCurrent(0)
      message.warning('请先补全项目信息后再发布')
      return
    }
    Modal.confirm({
      title: '确认发布评标任务？',
      content: `发布后将邀请 ${supplierEmails.length} 家供应商，并进入材料收集阶段。`,
      okText: '确认发布',
      cancelText: '返回检查',
      onOk: handlePublish,
    })
  }

  const cancelCreate = () => {
    Modal.confirm({
      title: '退出创建评标任务？',
      content: dirty ? '当前修改尚未保存，可先取消并点击“保存草稿”。' : '已保存的草稿仍会保留，下次可继续编辑。',
      okText: '退出',
      cancelText: '继续编辑',
      okButtonProps: { danger: true },
      onOk: () => navigate('/evaluation'),
    })
  }

  const copyLink = async () => {
    await copyText(portalLink)
    message.success('链接已复制到剪贴板')
  }

  return (
    <div className="p-6 max-w-[1100px] mx-auto">
      {/* Header */}
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-[#1E293B] mb-1">创建评标任务</h1>
          <p className="text-sm text-[#64748B]">配置项目信息、材料清单和评分办法，发布前可保存草稿并预览</p>
          <div className="flex items-center gap-2 mt-2 text-xs text-[#64748B]">
            {importedFrom && <Tag color="blue">来源：{importedFrom}</Tag>}
            <span>{dirty ? '有未保存修改' : lastSaved ? `已自动保存 ${lastSaved}` : '尚未保存'}</span>
          </div>
        </div>
        <Space wrap>
          {hasDraft && <Button icon={<Clock size={14} />} onClick={restoreDraft}>恢复草稿</Button>}
          <Button icon={<Save size={14} />} onClick={() => saveDraft()}>保存草稿</Button>
          <Button icon={<Eye size={14} />} onClick={() => setPreviewOpen(true)}>预览</Button>
          <Button icon={<X size={14} />} onClick={cancelCreate}>取消</Button>
        </Space>
      </div>

      {/* Steps */}
      <Card className="!border-[#E2E8F0] !shadow-none mb-4" styles={{ body: { padding: '20px 24px' } }}>
        <Steps
          current={current}
          onChange={changeStep}
          items={steps.map((s, i) => ({
            title: s.title,
            icon: <s.icon size={16} />,
            status: i < current ? 'finish' : i === current ? 'process' : 'wait',
          }))}
        />
      </Card>

      {/* Step Content */}
      <Card className="!border-[#E2E8F0] !shadow-none" styles={{ body: { padding: 24 } }}>
        {/* Step 1: Project Info */}
        {current === 0 && (
          <div className="max-w-[680px]">
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2"><Megaphone size={18} className="text-[#2563EB]" /><h2 className="text-base font-semibold text-[#1E293B]">项目基本信息</h2></div>
              <Button size="small" onClick={() => { form.setFieldsValue({ projectName: '智慧园区一体化平台采购项目', tenderNo: 'ZHYQ-2026-0806', tenderEntity: '深圳市智慧园区建设中心', budget: 6800000, submitDeadline: dayjs().add(7, 'day').hour(17).minute(0), evalRange: [dayjs().add(8, 'day'), dayjs().add(10, 'day')], description: '用于演示供应商提交、AI 初审与人工复审完整流程。' }); markDirty() }}>填入示例</Button>
            </div>

            <div className="rounded-lg border border-[#BFDBFE] bg-[#EFF6FF] p-4 mb-5">
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-white flex items-center justify-center text-[#2563EB] flex-shrink-0"><Import size={17} /></div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-[#1E293B] mb-1">从已有投标项目导入</div>
                  <div className="text-xs text-[#64748B] mb-3">自动带入项目编号、采购单位、截止时间及材料清单，减少重复配置。</div>
                  <div className="flex gap-2">
                    <Select
                      value={importProjectId}
                      onChange={value => importProject(value)}
                      placeholder="选择投标项目"
                      className="flex-1"
                      showSearch
                      optionFilterProp="label"
                      options={bidTasks.map(task => ({ value: task.id, label: `${task.projectName}（${task.tenderNo}）` }))}
                    />
                    {importedFrom && <Button onClick={() => { setImportProjectId(undefined); setImportedFrom(undefined); markDirty() }}>解除关联</Button>}
                  </div>
                </div>
              </div>
            </div>
            <Form layout="vertical" form={form} initialValues={{
              projectName: '',
              tenderNo: '',
              tenderEntity: '',
              budget: undefined,
              submitDeadline: null,
              evalRange: null,
              description: '',
            }} onValuesChange={markDirty}>
              <div className="grid grid-cols-2 gap-x-4">
                <Form.Item label="项目名称" name="projectName" rules={[{ required: true }]}>
                  <Input placeholder="请输入项目名称" size="large" />
                </Form.Item>
                <Form.Item label="招标编号" name="tenderNo" rules={[{ required: true }]}>
                  <Input placeholder="请输入招标编号" size="large" />
                </Form.Item>
                <Form.Item label="采购单位" name="tenderEntity" rules={[{ required: true }]}>
                  <Input placeholder="请输入采购单位名称" size="large" />
                </Form.Item>
                <Form.Item label="项目预算（元）" name="budget">
                  <InputNumber placeholder="请输入预算金额" size="large" className="!w-full" formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')} />
                </Form.Item>
                <Form.Item label="供应商提交截止时间" name="submitDeadline" rules={[
                  { required: true, message: '请选择供应商提交截止时间' },
                  { validator: (_, value) => !value || dayjs(value).isAfter(dayjs()) ? Promise.resolve() : Promise.reject(new Error('截止时间必须晚于当前时间')) },
                ]}>
                  <DatePicker showTime format="YYYY-MM-DD HH:mm" size="large" className="!w-full" placeholder="选择截止时间" />
                </Form.Item>
                <Form.Item label="评标时间范围" name="evalRange" dependencies={['submitDeadline']} rules={[
                  { required: true, message: '请选择评标时间范围' },
                  { validator: (_, value) => {
                    if (!value?.length) return Promise.resolve()
                    const submitDeadline = form.getFieldValue('submitDeadline')
                    if (submitDeadline && !dayjs(value[0]).isAfter(dayjs(submitDeadline))) return Promise.reject(new Error('评标开始时间需晚于供应商提交截止时间'))
                    return dayjs(value[1]).isAfter(dayjs(value[0])) ? Promise.resolve() : Promise.reject(new Error('评标结束时间需晚于开始时间'))
                  } },
                ]}>
                  <RangePicker size="large" className="!w-full" />
                </Form.Item>
              </div>
              <Form.Item label="项目说明" name="description">
                <TextArea rows={3} placeholder="项目背景、评标要求等补充说明" />
              </Form.Item>
            </Form>

            <Alert
              type="info"
              showIcon
              message="截止时间到达后，供应商将无法提交任何材料"
              description="系统会在截止时间自动关闭材料提交通道，并向未提交的供应商发送通知"
              className="!rounded-lg"
            />
          </div>
        )}

        {/* Step 2: Material Checklist */}
        {current === 1 && (
          <div>
            <div className="flex items-center justify-between mb-5">
              <div className="flex items-center gap-2">
                <ClipboardList size={18} className="text-[#2563EB]" />
                <h2 className="text-base font-semibold text-[#1E293B]">必交材料清单配置</h2>
              </div>
              <Button type="primary" icon={<Plus size={15} />} onClick={addMaterial} className="!rounded-lg !bg-[#2563EB]">
                添加材料项
              </Button>
            </div>

            <div className="flex items-center gap-3 mb-4 text-sm">
              <span className="text-[#64748B]">共 <span className="font-semibold text-[#1E293B]">{materials.length}</span> 项</span>
              <span className="text-[#64748B]">必交 <span className="font-semibold text-[#DC2626]">{requiredCount}</span> 项</span>
              <span className="text-[#64748B]">选交 <span className="font-semibold text-[#16A34A]">{materials.length - requiredCount}</span> 项</span>
            </div>

            <Table
              dataSource={materials}
              rowKey="id"
              pagination={false}
              size="middle"
              columns={[
                {
                  title: '材料名称',
                  dataIndex: 'name',
                  width: '35%',
                  render: (name: string, record: any) => (
                    <Input
                      value={name}
                      onChange={e => updateMaterialName(record.id, e.target.value)}
                      variant="borderless"
                      className="!px-0"
                    />
                  ),
                },
                {
                  title: '类别',
                  dataIndex: 'category',
                  width: 100,
                  render: (cat: string) => {
                    const colors: Record<string, string> = { 资质: 'blue', 商务: 'orange', 技术: 'green' }
                    return <Tag color={colors[cat] || 'default'}>{cat}</Tag>
                  },
                },
                {
                  title: '是否必交',
                  dataIndex: 'required',
                  width: 100,
                  render: (required: boolean, record: any) => (
                    <Switch
                      checked={required}
                      onChange={() => toggleMaterialRequired(record.id)}
                      checkedChildren="必交"
                      unCheckedChildren="选交"
                    />
                  ),
                },
                {
                  title: '默认项',
                  dataIndex: 'isDefault',
                  width: 80,
                  render: (isDefault: boolean) => isDefault ? <Tag>默认</Tag> : <span className="text-[#94A3B8] text-xs">自定义</span>,
                },
                {
                  title: '',
                  width: 60,
                  render: (_: any, record: any) => (
                    <Button type="text" danger icon={<Minus size={14} />} onClick={() => removeMaterial(record.id)} size="small" />
                  ),
                },
              ]}
            />

            <Alert
              type="info"
              showIcon
              message="供应商提交页面将根据此清单展示必交材料"
              description="必交材料未提交将触发补充通知；选交材料不影响提交完整性"
              className="!rounded-lg mt-4"
            />
          </div>
        )}

        {/* Step 3: Scoring Method */}
        {current === 2 && (
          <div>
            <div className="flex items-center gap-2 mb-5">
              <Scale size={18} className="text-[#2563EB]" />
              <h2 className="text-base font-semibold text-[#1E293B]">评分办法配置</h2>
            </div>

            <div className="flex items-center gap-3 mb-4">
              <div className={`px-3 py-1.5 rounded-lg text-sm font-medium ${totalWeight === 100 ? 'bg-[#F0FDF4] text-[#16A34A]' : 'bg-[#FEF2F2] text-[#DC2626]'}`}>
                总权重：{totalWeight} / 100 {totalWeight === 100 ? '✓' : '(必须等于100)'}
              </div>
            </div>

            <Table
              dataSource={scoringItems}
              rowKey="id"
              pagination={false}
              size="middle"
              columns={[
                {
                  title: '评分项',
                  dataIndex: 'name',
                  width: '25%',
                  render: (name: string) => <span className="font-medium text-[#1E293B]">{name}</span>,
                },
                {
                  title: '类别',
                  dataIndex: 'category',
                  width: 100,
                  render: (cat: string) => <Tag>{evalCategoryLabels[cat] || cat}</Tag>,
                },
                {
                  title: '评分方式',
                  dataIndex: 'method',
                  width: 120,
                  render: (method: string) => <span className="text-[#64748B] text-sm">{method}</span>,
                },
                {
                  title: '权重（分）',
                  dataIndex: 'weight',
                  width: 140,
                  render: (weight: number, record: any) => (
                    <InputNumber
                      value={weight}
                      min={0}
                      max={100}
                      onChange={v => updateScoreWeight(record.id, v || 0)}
                      className="!w-24"
                    />
                  ),
                },
                {
                  title: '评分说明',
                  dataIndex: 'desc',
                  render: (desc: string) => <span className="text-[#64748B] text-xs">{desc}</span>,
                },
              ]}
            />
          </div>
        )}

        {/* Step 4: Review Settings */}
        {current === 3 && (
          <div className="max-w-[680px]">
            <div className="flex items-center gap-2 mb-5">
              <Settings2 size={18} className="text-[#2563EB]" />
              <h2 className="text-base font-semibold text-[#1E293B]">评审流程设置</h2>
            </div>

            <Card size="small" className="!border-[#E2E8F0] !rounded-lg mb-4" styles={{ body: { padding: 16 } }}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-[#1E293B] mb-2">受邀供应商</label>
                  <Select
                    mode="tags"
                    value={supplierEmails}
                    onChange={value => { setSupplierEmails(value); markDirty() }}
                    tokenSeparators={[',', '；', ';']}
                    placeholder="输入邮箱后回车"
                    className="w-full"
                    options={[]}
                  />
                  <p className="text-xs text-[#64748B] mt-1">发布后可为每家供应商复制独立邀请链接；统一入口仅用于内部演示。</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-[#1E293B] mb-2">评审人</label>
                  <Select
                    mode="multiple"
                    value={reviewers}
                    onChange={value => { setReviewers(value); markDirty() }}
                    placeholder="选择评审人"
                    className="w-full"
                    options={['刘德海', '周天宇', '陈审核', '李雪琴'].map(value => ({ value, label: value }))}
                  />
                  <p className="text-xs text-[#94A3B8] mt-1">评审人可在 AI 初审后复核资格与评分。</p>
                </div>
              </div>
            </Card>

            {/* Multi-round pricing */}
            <Card size="small" className="!border-[#E2E8F0] !rounded-lg mb-4" styles={{ body: { padding: 16 } }}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Clock size={16} className="text-[#EA580C]" />
                  <span className="font-medium text-[#1E293B]">多轮报价</span>
                </div>
                <Switch
                  checked={reviewConfig.multiRoundPricing}
                  onChange={v => updateReviewConfig({ multiRoundPricing: v })}
                />
              </div>
              {reviewConfig.multiRoundPricing && (
                <div className="pl-6 space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-[#64748B] w-28">最多报价轮次</span>
                    <InputNumber
                      value={reviewConfig.maxRounds}
                      min={2}
                      max={5}
                      onChange={v => updateReviewConfig({ maxRounds: v || 3 })}
                      className="!w-24"
                    />
                    <span className="text-xs text-[#94A3B8]">供应商可在每轮中重新提交报价</span>
                  </div>
                  <Alert
                    type="info"
                    showIcon
                    message="启用后，每轮报价截止后供应商可看到自己的排名（不显示其他供应商价格）"
                    className="!rounded-lg"
                  />
                </div>
              )}
            </Card>

            {/* Supplement notification */}
            <Card size="small" className="!border-[#E2E8F0] !rounded-lg mb-4" styles={{ body: { padding: 16 } }}>
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <FileText size={16} className="text-[#2563EB]" />
                  <span className="font-medium text-[#1E293B]">材料缺失补充通知</span>
                </div>
                <Switch
                  checked={reviewConfig.notifyOnMissing}
                  onChange={v => updateReviewConfig({ notifyOnMissing: v })}
                />
              </div>
              {reviewConfig.notifyOnMissing && (
                <div className="pl-6 space-y-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-[#64748B] w-28">补充时限（分钟）</span>
                    <InputNumber
                      value={reviewConfig.supplementDeadline}
                      min={30}
                      max={240}
                      step={30}
                      onChange={v => updateReviewConfig({ supplementDeadline: v || 120 })}
                      className="!w-24"
                    />
                    <span className="text-xs text-[#94A3B8]">建议 60-120 分钟</span>
                  </div>
                  <Alert
                    type="warning"
                    showIcon
                    message="到期未补充将视为放弃，材料缺失项将在评标中扣分或触发废标"
                    className="!rounded-lg"
                  />
                </div>
              )}
            </Card>

            {/* Other settings */}
            <Card size="small" className="!border-[#E2E8F0] !rounded-lg" styles={{ body: { padding: 16 } }}>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium text-[#1E293B] text-sm">允许供应商修改已提交材料</span>
                    <p className="text-xs text-[#94A3B8] mt-0.5">在截止时间前，供应商可替换已上传的文件</p>
                  </div>
                  <Switch
                    checked={reviewConfig.allowModify}
                    onChange={v => updateReviewConfig({ allowModify: v })}
                  />
                </div>
                <Divider className="!my-2" />
                <div className="flex items-center justify-between">
                  <div>
                    <span className="font-medium text-[#1E293B] text-sm">截止后自动关闭提交通道</span>
                    <p className="text-xs text-[#94A3B8] mt-0.5">到达截止时间自动关闭，逾期不可提交</p>
                  </div>
                  <Switch
                    checked={reviewConfig.closeAfterDeadline}
                    onChange={v => updateReviewConfig({ closeAfterDeadline: v })}
                  />
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Step 5: Publish */}
        {current === 4 && (
          <div className="max-w-[680px]">
            {!published ? (
              <>
                <div className="flex items-center gap-2 mb-5">
                  <Rocket size={18} className="text-[#2563EB]" />
                  <h2 className="text-base font-semibold text-[#1E293B]">确认发布评标任务</h2>
                </div>

                <div className="space-y-3 mb-6">
                  <div className="bg-[#F8FAFC] rounded-lg p-4">
                    <h3 className="text-sm font-medium text-[#1E293B] mb-3">配置摘要</h3>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="flex justify-between">
                        <span className="text-[#64748B]">材料项总数</span>
                        <span className="font-medium text-[#1E293B]">{materials.length} 项</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#64748B]">必交项</span>
                        <span className="font-medium text-[#DC2626]">{requiredCount} 项</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#64748B]">评分项</span>
                        <span className="font-medium text-[#1E293B]">{scoringItems.length} 项</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#64748B]">总权重</span>
                        <span className={`font-medium ${totalWeight === 100 ? 'text-[#16A34A]' : 'text-[#DC2626]'}`}>{totalWeight} / 100</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#64748B]">多轮报价</span>
                        <span className="font-medium text-[#1E293B]">{reviewConfig.multiRoundPricing ? `启用（最多${reviewConfig.maxRounds}轮）` : '未启用'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-[#64748B]">补充时限</span>
                        <span className="font-medium text-[#1E293B]">{reviewConfig.notifyOnMissing ? `${reviewConfig.supplementDeadline}分钟` : '未启用'}</span>
                      </div>
                    </div>
                  </div>

                  {totalWeight !== 100 && (
                    <Alert type="error" showIcon message="评分总权重不等于100，请返回评分办法步骤调整" className="!rounded-lg" />
                  )}
                </div>

                <div className="flex justify-center gap-3">
                  <Button
                    size="large"
                    icon={<Eye size={16} />}
                    onClick={() => setPreviewOpen(true)}
                    className="!rounded-lg !h-11 !px-6"
                  >
                    发布预览
                  </Button>
                  <Button
                    type="primary"
                    size="large"
                    icon={<Rocket size={16} />}
                    onClick={confirmPublish}
                    disabled={totalWeight !== 100}
                    className="!rounded-lg !bg-[#2563EB] !h-11 !px-8"
                  >
                    发布评标任务
                  </Button>
                </div>
              </>
            ) : (
              <div className="text-center py-8">
                <div className="w-16 h-16 rounded-full bg-[#F0FDF4] flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 size={32} className="text-[#16A34A]" />
                </div>
                <h2 className="text-lg font-semibold text-[#1E293B] mb-2">评标任务已发布</h2>
                <p className="text-sm text-[#64748B] mb-6">供应商入口链接已生成，可发送给受邀供应商</p>

                <Card size="small" className="!border-[#E2E8F0] !rounded-lg max-w-[520px] mx-auto mb-6" styles={{ body: { padding: 16 } }}>
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-[#EFF6FF] flex items-center justify-center flex-shrink-0">
                      <Link2 size={16} className="text-[#2563EB]" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-[#64748B] mb-0.5">供应商提交入口</p>
                      <p className="text-sm text-[#2563EB] truncate text-left">{portalLink}</p>
                    </div>
                    <Button type="default" size="small" icon={<Copy size={14} />} onClick={copyLink} className="!rounded-lg">
                      复制
                    </Button>
                  </div>
                </Card>

                <Space>
                  <Button type="default" onClick={() => { setPublished(false); setCurrent(0) }} className="!rounded-lg">
                    创建新任务
                  </Button>
                  <Button type="primary" onClick={() => navigate('/evaluation')} className="!rounded-lg !bg-[#2563EB]">
                    返回评标工作台
                  </Button>
                </Space>
              </div>
            )}
          </div>
        )}
      </Card>

      {/* Navigation buttons */}
      {!published && (
        <div className="flex justify-between mt-4">
          <Button
            disabled={current === 0}
            onClick={() => setCurrent(c => c - 1)}
            icon={<ArrowLeft size={15} />}
            className="!rounded-lg"
          >
            上一步
          </Button>
          {current < steps.length - 1 && (
            <Button
              type="primary"
              onClick={nextStep}
              className="!rounded-lg !bg-[#2563EB]"
            >
              下一步
              <ArrowRight size={15} />
            </Button>
          )}
        </div>
      )}

      <Modal
        open={previewOpen}
        onCancel={() => setPreviewOpen(false)}
        title="评标任务发布预览"
        width={720}
        footer={<Button type="primary" onClick={() => setPreviewOpen(false)} className="!bg-[#2563EB]">返回编辑</Button>}
      >
        <div className="space-y-4 pt-2">
          <Alert
            type={form.getFieldValue('projectName') && totalWeight === 100 ? 'success' : 'warning'}
            showIcon
            message={form.getFieldValue('projectName') && totalWeight === 100 ? '核心配置检查通过' : '仍有未完成配置，请返回对应步骤补充'}
          />
          <div className="rounded-lg bg-[#F8FAFC] p-4 grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <div><span className="text-[#64748B]">项目名称：</span><span className="text-[#1E293B] font-medium">{form.getFieldValue('projectName') || '未填写'}</span></div>
            <div><span className="text-[#64748B]">招标编号：</span><span className="text-[#1E293B]">{form.getFieldValue('tenderNo') || '未填写'}</span></div>
            <div><span className="text-[#64748B]">提交截止：</span><span className="text-[#1E293B]">{form.getFieldValue('submitDeadline') ? dayjs(form.getFieldValue('submitDeadline')).format('YYYY-MM-DD HH:mm') : '未设置'}</span></div>
            <div><span className="text-[#64748B]">关联投标项目：</span><span className="text-[#1E293B]">{importedFrom || '无'}</span></div>
            <div><span className="text-[#64748B]">材料清单：</span><span className="text-[#1E293B]">{materials.length} 项（必交 {requiredCount} 项）</span></div>
            <div><span className="text-[#64748B]">评分权重：</span><span className={totalWeight === 100 ? 'text-[#16A34A]' : 'text-[#DC2626]'}>{totalWeight} / 100</span></div>
            <div><span className="text-[#64748B]">受邀供应商：</span><span className="text-[#1E293B]">{supplierEmails.length} 家</span></div>
            <div><span className="text-[#64748B]">评审人：</span><span className="text-[#1E293B]">{reviewers.join('、') || '未配置'}</span></div>
          </div>
          <div>
            <div className="text-sm font-medium text-[#1E293B] mb-2">供应商将看到的必交材料</div>
            <div className="flex flex-wrap gap-2">{materials.filter(item => item.required).slice(0, 10).map(item => <Tag key={item.id}>{item.name}</Tag>)}{requiredCount > 10 && <Tag>另 {requiredCount - 10} 项</Tag>}</div>
          </div>
        </div>
      </Modal>
    </div>
  )
}
