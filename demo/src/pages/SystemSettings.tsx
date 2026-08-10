import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Button,
  Card,
  Divider,
  Form,
  Input,
  InputNumber,
  Modal,
  Select,
  Slider,
  Space,
  Switch,
  Table,
  Tag,
  message,
} from 'antd'
import {
  Bell,
  Bot,
  Clock,
  Cloud,
  Cpu,
  FileText,
  HardDrive,
  Plus,
  RefreshCw,
  RotateCcw,
  Save,
  Server,
  Shield,
} from 'lucide-react'
import { aiModelConfig, docTemplateConfig, modelOptions, operationLogs, systemConfig } from '../mock/data'
import {
  platformApi,
  saveBlob,
  type AgentStatus,
  type AuditEvent,
  type DeploymentSettings,
  type DocumentTemplateSettings,
  type GenerationSettings,
  type ModelProvider,
  type ModelRoute,
  type NotificationSettings,
} from '../api/platformApi'
import { shouldUseMocks } from '../api/runtime'
import { downloadTableAsCsv } from '../utils/demoActions'

type TabKey = 'ai' | 'deploy' | 'template' | 'notify' | 'logs'

const DEFAULT_GENERATION: GenerationSettings = {
  temperature: aiModelConfig.temperature,
  topP: 0.9,
  maxOutputTokens: aiModelConfig.maxTokens,
  requestTimeoutSeconds: aiModelConfig.timeout,
  autoRetry: true,
  circuitBreakerEnabled: aiModelConfig.enableCircuitBreaker,
}

const DEFAULT_DEPLOYMENT: DeploymentSettings = {
  mode: systemConfig.deploymentMode === 'private' ? 'private' : 'saas',
  companyName: systemConfig.companyName,
  storageQuotaBytes: systemConfig.storageQuota * 1024 * 1024 * 1024,
  maxProjects: systemConfig.maxProjects,
  maxUsers: systemConfig.maxUsers,
  autoBackup: systemConfig.enableAutoBackup,
  backupCron: '0 2 * * *',
  versionControlEnabled: systemConfig.enableVersionControl,
  version: 1,
}

const DEFAULT_TEMPLATE: DocumentTemplateSettings = {
  format: docTemplateConfig.defaultFormat === 'custom' ? 'custom' : 'standard',
  pageSize: docTemplateConfig.pageSize as DocumentTemplateSettings['pageSize'],
  bodyFont: docTemplateConfig.fontFamily,
  bodyFontSizePt: Number.parseInt(docTemplateConfig.fontSize, 10) || 12,
  lineSpacing: Number(docTemplateConfig.lineHeight) || 1.5,
  marginMode: docTemplateConfig.margin === '窄' ? 'narrow' : docTemplateConfig.margin === '宽' ? 'wide' : 'standard',
  splitBySection: docTemplateConfig.enableAutoSplit,
  watermarkEnabled: docTemplateConfig.watermark,
  watermarkText: docTemplateConfig.watermarkText,
  version: 1,
}

const DEFAULT_NOTIFICATION: NotificationSettings = {
  inAppEnabled: systemConfig.enableNotification,
  emailEnabled: systemConfig.enableEmailNotify,
  qualificationReminderDays: [systemConfig.expiryWarningDays],
  events: {
    jobCompleted: true,
    reviewCompleted: true,
    qualificationExpiring: systemConfig.enableExpiryWarning,
  },
  version: 1,
}

const SCENE_LABELS: Record<ModelRoute['scene'], string> = {
  tender_parse: '招标文件解析',
  requirement_extract: '需求与评分项提取',
  material_match: '材料智能匹配',
  bid_generate: '投标文件生成',
  bid_review: '标书内容审核',
  evaluation_check: '评标材料检查',
  risk_check: '评标风险分析',
  evaluation_score: '评标智能评分',
  report_generate: '评标报告生成',
}

const EVENT_LABELS: Record<string, string> = {
  jobCompleted: '异步任务完成',
  reviewCompleted: 'AI 审核完成',
  qualificationExpiring: '资质即将过期',
  materialUploaded: '材料上传完成',
  documentVersionCreated: '文档版本更新',
}

export default function SystemSettings() {
  const [activeTab, setActiveTab] = useState<TabKey>('ai')
  const menuItems = [
    { key: 'ai', label: 'AI模型配置', icon: Bot },
    { key: 'deploy', label: '部署与存储', icon: Server },
    { key: 'template', label: '文档模板', icon: FileText },
    { key: 'notify', label: '通知设置', icon: Bell },
    { key: 'logs', label: '操作日志', icon: Clock },
  ] as const

  return (
    <main className="p-4 sm:p-6" data-testid="system-settings-page">
      <div className="mb-6"><h1 className="text-2xl font-semibold text-[#1E293B]">系统设置</h1><p className="mt-1 text-sm text-[#64748B]">统一管理模型路由、部署、模板、通知与操作审计</p></div>
      <div className="flex flex-col gap-5 lg:flex-row">
        <div className="flex-shrink-0 lg:w-52">
          <div className="flex overflow-x-auto rounded-xl border border-[#E2E8F0] bg-white p-2 lg:block" role="tablist" aria-label="系统设置分类">
            {menuItems.map(item => {
              const Icon = item.icon
              const active = activeTab === item.key
              return <button type="button" key={item.key} role="tab" aria-selected={active} onClick={() => setActiveTab(item.key)} className={`mb-0.5 flex w-full items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm transition-colors ${active ? 'bg-[#EFF6FF] font-medium text-[#2563EB]' : 'text-[#475569] hover:bg-[#F8FAFC]'}`}><Icon size={16} />{item.label}</button>
            })}
          </div>
        </div>
        <div className="min-w-0 flex-1">
          <div hidden={activeTab !== 'ai'}><AIModelSettings /></div>
          <div hidden={activeTab !== 'deploy'}><DeploySettings /></div>
          <div hidden={activeTab !== 'template'}><TemplateSettings /></div>
          <div hidden={activeTab !== 'notify'}><NotifySettings /></div>
          <div hidden={activeTab !== 'logs'}><OperationLogs /></div>
        </div>
      </div>
    </main>
  )
}

function AIModelSettings() {
  const mockMode = shouldUseMocks()
  const [providers, setProviders] = useState<ModelProvider[]>(mockProviders())
  const [routes, setRoutes] = useState<ModelRoute[]>([])
  const [generation, setGeneration] = useState<GenerationSettings>(DEFAULT_GENERATION)
  const [agents, setAgents] = useState<AgentStatus[]>([])
  const [keyDrafts, setKeyDrafts] = useState<Record<string, string>>({})
  const [dirty, setDirty] = useState(false)
  const [loading, setLoading] = useState(false)
  const [testing, setTesting] = useState('')
  const [lastSaved, setLastSaved] = useState('')
  const [providerOpen, setProviderOpen] = useState(false)
  const [providerForm] = Form.useForm()
  useUnsavedChangesGuard(dirty)

  const load = useCallback(async () => {
    if (mockMode) {
      setAgents(mockAgents())
      return
    }
    setLoading(true)
    try {
      const [providerRows, routeRows, generationSettings, agentRows] = await Promise.all([
        platformApi.listModelProviders(),
        platformApi.getModelRoutes(),
        platformApi.getGenerationSettings(),
        platformApi.getAgentStatus(),
      ])
      setProviders(providerRows)
      setRoutes(routeRows)
      setGeneration(generationSettings)
      setAgents(agentRows)
      setDirty(false)
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'AI 配置加载失败')
    } finally {
      setLoading(false)
    }
  }, [mockMode])

  useEffect(() => {
    const timeout = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timeout)
  }, [load])

  const updateProvider = (id: string, patch: Partial<ModelProvider>) => {
    setProviders(previous => previous.map(item => item.id === id ? { ...item, ...patch } : item))
    setDirty(true)
  }

  const updateRoute = (index: number, patch: Partial<ModelRoute>) => {
    setRoutes(previous => previous.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item))
    setDirty(true)
  }

  const addRoute = () => {
    const provider = providers[0]
    if (!provider) {
      message.warning('请先添加至少一个模型服务商')
      return
    }
    const scene = (Object.keys(SCENE_LABELS) as ModelRoute['scene'][]).find(value => !routes.some(route => route.scene === value))
    if (!scene) {
      message.info('所有业务场景均已配置')
      return
    }
    setRoutes(previous => [...previous, {
      scene,
      primaryProviderId: provider.id,
      primaryModel: 'qwen-plus',
      fallbackProviderId: provider.id,
      fallbackModel: 'qwen-plus',
      timeoutSeconds: 60,
      maxRetries: 3,
      circuitBreakerFailures: 3,
    }])
    setDirty(true)
  }

  const addProvider = async () => {
    const values = await providerForm.validateFields()
    setLoading(true)
    try {
      const provider = mockMode ? mockProviderFromForm(values) : await platformApi.createModelProvider({
        provider: values.provider,
        displayName: values.displayName,
        baseUrl: values.baseUrl,
        apiKey: values.apiKey,
        enabled: true,
      })
      setProviders(previous => [...previous, provider])
      setProviderOpen(false)
      providerForm.resetFields()
      message.success('模型服务商已添加，密钥仅以脱敏形式返回')
    } catch (error) {
      message.error(error instanceof Error ? error.message : '模型服务商添加失败')
    } finally {
      setLoading(false)
    }
  }

  const testProvider = async (provider: ModelProvider) => {
    setTesting(provider.id)
    try {
      if (!mockMode) {
        const job = await platformApi.testModelProvider(provider.id)
        if (job.status === 'failed') throw new Error(job.error?.message || '连接测试失败')
        const latest = await platformApi.listModelProviders()
        setProviders(latest)
      } else {
        updateProvider(provider.id, { connectionStatus: 'connected', lastTestedAt: new Date().toISOString() })
      }
      message.success(`${provider.displayName} 连接测试通过`)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '连接测试失败')
    } finally {
      setTesting('')
    }
  }

  const save = async () => {
    setLoading(true)
    try {
      if (!mockMode) {
        const updatedProviders = await Promise.all(providers.map(provider => platformApi.updateModelProvider(provider.id, provider.version, {
          displayName: provider.displayName,
          baseUrl: provider.baseUrl,
          enabled: provider.enabled,
          apiKey: keyDrafts[provider.id] || undefined,
        })))
        const [updatedRoutes, updatedGeneration] = await Promise.all([
          platformApi.updateModelRoutes(routes),
          platformApi.updateGenerationSettings(generation),
        ])
        setProviders(updatedProviders)
        setRoutes(updatedRoutes)
        setGeneration(updatedGeneration)
        setKeyDrafts({})
      }
      setDirty(false)
      setLastSaved(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
      message.success('AI 模型与生成配置已保存')
    } catch (error) {
      message.error(error instanceof Error ? error.message : 'AI 配置保存失败')
    } finally {
      setLoading(false)
    }
  }

  return <div className="space-y-4">
    <Card loading={loading} className="!border-[#E2E8F0] !shadow-none" title={<span className="flex items-center gap-2 text-sm font-semibold"><Shield size={16} color="#2563EB" />模型服务商与加密凭据</span>} extra={<Button size="small" icon={<Plus size={13} />} onClick={() => setProviderOpen(true)}>新增服务商</Button>}>
      <Alert className="mb-4" type="info" showIcon message="API Key 由服务端加密保存；前端只能查看脱敏值，留空表示不更换密钥。" />
      <Table rowKey="id" pagination={false} size="small" dataSource={providers} locale={{ emptyText: '尚未配置模型服务商' }} columns={[
        { title: '服务商', width: 150, render: (_, row: ModelProvider) => <div><Input value={row.displayName} onChange={event => updateProvider(row.id, { displayName: event.target.value })} /><Tag className="mt-1" color={row.connectionStatus === 'connected' ? 'green' : row.connectionStatus === 'failed' ? 'red' : 'default'}>{row.connectionStatus === 'connected' ? '连接正常' : row.connectionStatus === 'failed' ? '连接失败' : '待测试'}</Tag></div> },
        { title: 'Base URL', render: (_, row: ModelProvider) => <Input value={row.baseUrl} onChange={event => updateProvider(row.id, { baseUrl: event.target.value })} /> },
        { title: 'API Key', width: 230, render: (_, row: ModelProvider) => <Input.Password value={keyDrafts[row.id] || ''} placeholder={row.apiKeyMasked} onChange={event => { setKeyDrafts(previous => ({ ...previous, [row.id]: event.target.value })); setDirty(true) }} /> },
        { title: '启用', width: 70, render: (_, row: ModelProvider) => <Switch checked={row.enabled} onChange={enabled => updateProvider(row.id, { enabled })} /> },
        { title: '测试', width: 90, render: (_, row: ModelProvider) => <Button size="small" disabled={!row.enabled} loading={testing === row.id} onClick={() => void testProvider(row)}>连接测试</Button> },
      ]} />
    </Card>

    <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="flex items-center gap-2 text-sm font-semibold"><Cpu size={16} color="#2563EB" />多模型业务路由</span>} extra={<Button size="small" onClick={addRoute}>新增场景路由</Button>}>
      <Table rowKey={row => row.scene} pagination={false} size="small" dataSource={routes} locale={{ emptyText: '添加服务商后，为业务场景配置主模型和降级模型' }} columns={[
        { title: '业务场景', width: 170, render: (_, row: ModelRoute, index) => <Select className="w-full" value={row.scene} options={(Object.keys(SCENE_LABELS) as ModelRoute['scene'][]).map(value => ({ value, label: SCENE_LABELS[value], disabled: routes.some((item, itemIndex) => itemIndex !== index && item.scene === value) }))} onChange={scene => updateRoute(index, { scene })} /> },
        { title: '主服务商', render: (_, row: ModelRoute, index) => <Select className="w-full" value={row.primaryProviderId} options={providers.map(item => ({ value: item.id, label: item.displayName }))} onChange={primaryProviderId => updateRoute(index, { primaryProviderId })} /> },
        { title: '主模型', render: (_, row: ModelRoute, index) => <Input value={row.primaryModel} onChange={event => updateRoute(index, { primaryModel: event.target.value })} /> },
        { title: '降级服务商', render: (_, row: ModelRoute, index) => <Select className="w-full" value={row.fallbackProviderId} options={providers.map(item => ({ value: item.id, label: item.displayName }))} onChange={fallbackProviderId => updateRoute(index, { fallbackProviderId })} /> },
        { title: '降级模型', render: (_, row: ModelRoute, index) => <Input value={row.fallbackModel} onChange={event => updateRoute(index, { fallbackModel: event.target.value })} /> },
        { title: '', width: 60, render: (_, _row: ModelRoute, index) => <Button type="link" danger onClick={() => { setRoutes(previous => previous.filter((_, itemIndex) => itemIndex !== index)); setDirty(true) }}>删除</Button> },
      ]} />
    </Card>

    <Card className="!border-[#E2E8F0] !shadow-none" title="统一生成参数">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        <SettingSlider label="Temperature" value={generation.temperature} min={0} max={2} step={0.1} onChange={temperature => { setGeneration(previous => ({ ...previous, temperature })); setDirty(true) }} />
        <SettingSlider label="Top P" value={generation.topP} min={0} max={1} step={0.05} onChange={topP => { setGeneration(previous => ({ ...previous, topP })); setDirty(true) }} />
        <label className="text-xs text-[#64748B]">最大输出 Token<InputNumber className="!mt-2 !w-full" min={1} max={131072} value={generation.maxOutputTokens} onChange={value => { if (value) setGeneration(previous => ({ ...previous, maxOutputTokens: value })); setDirty(true) }} /></label>
        <label className="text-xs text-[#64748B]">请求超时（秒）<InputNumber className="!mt-2 !w-full" min={1} max={600} value={generation.requestTimeoutSeconds} onChange={value => { if (value) setGeneration(previous => ({ ...previous, requestTimeoutSeconds: value })); setDirty(true) }} /></label>
      </div>
      <Divider />
      <div className="grid gap-4 md:grid-cols-2"><ToggleRow title="失败自动重试" checked={generation.autoRetry} onChange={autoRetry => { setGeneration(previous => ({ ...previous, autoRetry })); setDirty(true) }} /><ToggleRow title="启用熔断器" checked={generation.circuitBreakerEnabled} onChange={circuitBreakerEnabled => { setGeneration(previous => ({ ...previous, circuitBreakerEnabled })); setDirty(true) }} /></div>
    </Card>

    <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="flex items-center gap-2 text-sm font-semibold"><Bot size={16} color="#2563EB" />智能体实时状态</span>} extra={<Button size="small" icon={<RefreshCw size={13} />} onClick={() => void load()}>刷新</Button>}>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{agents.map(agent => <div key={agent.scene} className="rounded-lg border border-[#E2E8F0] p-3"><div className="flex justify-between"><span className="text-sm font-medium">{agent.name}</span><Tag color={agent.status === 'online' ? 'green' : agent.status === 'offline' ? 'red' : 'gold'}>{agent.status}</Tag></div><div className="mt-2 text-xs text-[#64748B]">{agent.activeProvider || '-'} / {agent.activeModel || '-'} · 队列 {agent.queueDepth}</div></div>)}</div>
    </Card>

    <SettingsFooter dirty={dirty} loading={loading} lastSaved={lastSaved} onReset={() => { setGeneration(DEFAULT_GENERATION); setDirty(true) }} onSave={() => void save()} />
    <Modal title="新增模型服务商" open={providerOpen} confirmLoading={loading} onCancel={() => setProviderOpen(false)} onOk={() => void addProvider()} okText="添加" cancelText="取消">
      <Form form={providerForm} layout="vertical" requiredMark={false} className="pt-3">
        <Form.Item name="provider" label="服务商类型" initialValue="qwen" rules={[{ required: true }]}><Select options={[{ value: 'qwen', label: '通义千问' }, { value: 'deepseek', label: 'DeepSeek' }, { value: 'zhipu', label: '智谱 AI' }, { value: 'custom_openai_compatible', label: 'OpenAI 兼容接口' }]} /></Form.Item>
        <Form.Item name="displayName" label="显示名称" rules={[{ required: true, message: '请输入显示名称' }]}><Input /></Form.Item>
        <Form.Item name="baseUrl" label="Base URL" rules={[{ required: true, type: 'url', message: '请输入有效 URL' }]}><Input placeholder="https://ai.example.com/v1" /></Form.Item>
        <Form.Item name="apiKey" label="API Key" rules={[{ required: true, min: 8, message: '请输入至少 8 位密钥' }]}><Input.Password /></Form.Item>
      </Form>
    </Modal>
  </div>
}

function DeploySettings() {
  const mockMode = shouldUseMocks()
  const [config, setConfig] = useState<DeploymentSettings>(DEFAULT_DEPLOYMENT)
  const [dirty, setDirty] = useState(false)
  const [loading, setLoading] = useState(false)
  const [lastSaved, setLastSaved] = useState('')
  useUnsavedChangesGuard(dirty)

  useEffect(() => {
    if (mockMode) return
    const timeout = window.setTimeout(() => {
      setLoading(true)
      platformApi.getDeploymentSettings().then(setConfig).catch(error => message.error(error instanceof Error ? error.message : '部署配置加载失败')).finally(() => setLoading(false))
    }, 0)
    return () => window.clearTimeout(timeout)
  }, [mockMode])

  const update = (patch: Partial<DeploymentSettings>) => { setConfig(previous => ({ ...previous, ...patch })); setDirty(true) }
  const save = async () => {
    setLoading(true)
    try {
      if (!mockMode) {
        const { version: _version, ...payload } = config
        setConfig(await platformApi.updateDeploymentSettings(payload))
      }
      setDirty(false)
      setLastSaved(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
      message.success('部署与存储配置已保存')
    } catch (error) {
      message.error(error instanceof Error ? error.message : '部署配置保存失败')
    } finally { setLoading(false) }
  }

  return <div className="space-y-4">
    <Card loading={loading} className="!border-[#E2E8F0] !shadow-none" title={<span className="flex items-center gap-2 text-sm font-semibold"><Cloud size={16} color="#2563EB" />部署模式</span>}>
      <div className="grid grid-cols-2 gap-4">
        <ModeButton active={config.mode === 'saas'} title="SaaS 多租户" description="平台统一运维，租户数据隔离" onClick={() => update({ mode: 'saas' })} />
        <ModeButton active={config.mode === 'private'} title="私有化部署" description="部署在企业内网或专属云环境" onClick={() => update({ mode: 'private' })} />
      </div>
    </Card>
    <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="flex items-center gap-2 text-sm font-semibold"><HardDrive size={16} color="#2563EB" />租户容量与限制</span>}>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="text-xs text-[#64748B]">企业名称<Input className="mt-2" value={config.companyName} onChange={event => update({ companyName: event.target.value })} /></label>
        <label className="text-xs text-[#64748B]">存储配额（GB）<InputNumber className="!mt-2 !w-full" min={1} value={Math.round(config.storageQuotaBytes / 1024 / 1024 / 1024)} onChange={value => { if (value) update({ storageQuotaBytes: value * 1024 * 1024 * 1024 }) }} /></label>
        <label className="text-xs text-[#64748B]">最大项目数<InputNumber className="!mt-2 !w-full" min={1} value={config.maxProjects} onChange={value => { if (value) update({ maxProjects: value }) }} /></label>
        <label className="text-xs text-[#64748B]">最大用户数<InputNumber className="!mt-2 !w-full" min={1} value={config.maxUsers} onChange={value => { if (value) update({ maxUsers: value }) }} /></label>
      </div>
    </Card>
    <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="flex items-center gap-2 text-sm font-semibold"><Shield size={16} color="#2563EB" />备份与版本</span>}>
      <div className="space-y-4"><ToggleRow title="自动备份" checked={config.autoBackup} onChange={autoBackup => update({ autoBackup })} /><Divider className="!my-3" /><ToggleRow title="文档版本控制" checked={config.versionControlEnabled} onChange={versionControlEnabled => update({ versionControlEnabled })} /><Divider className="!my-3" /><label className="text-xs text-[#64748B]">备份计划<Select disabled={!config.autoBackup} className="!ml-3 w-52" value={config.backupCron} onChange={backupCron => update({ backupCron })} options={[{ value: '0 * * * *', label: '每小时' }, { value: '0 2 * * *', label: '每天 02:00' }, { value: '0 2 * * 0', label: '每周日 02:00' }]} /></label></div>
    </Card>
    <SettingsFooter dirty={dirty} loading={loading} lastSaved={lastSaved} onReset={() => { setConfig(DEFAULT_DEPLOYMENT); setDirty(true) }} onSave={() => void save()} />
  </div>
}

function TemplateSettings() {
  const mockMode = shouldUseMocks()
  const [config, setConfig] = useState<DocumentTemplateSettings>(DEFAULT_TEMPLATE)
  const [dirty, setDirty] = useState(false)
  const [loading, setLoading] = useState(false)
  const [lastSaved, setLastSaved] = useState('')
  useUnsavedChangesGuard(dirty)

  useEffect(() => {
    if (mockMode) return
    const timeout = window.setTimeout(() => {
      setLoading(true)
      platformApi.getDocumentTemplateSettings().then(setConfig).catch(error => message.error(error instanceof Error ? error.message : '文档模板配置加载失败')).finally(() => setLoading(false))
    }, 0)
    return () => window.clearTimeout(timeout)
  }, [mockMode])

  const update = (patch: Partial<DocumentTemplateSettings>) => { setConfig(previous => ({ ...previous, ...patch })); setDirty(true) }
  const save = async () => {
    setLoading(true)
    try {
      if (!mockMode) {
        const { version: _version, ...payload } = config
        setConfig(await platformApi.updateDocumentTemplateSettings(payload))
      }
      setDirty(false)
      setLastSaved(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
      message.success('文档模板格式已保存')
    } catch (error) { message.error(error instanceof Error ? error.message : '文档模板配置保存失败') } finally { setLoading(false) }
  }

  return <div className="space-y-4">
    <Alert type="info" showIcon message="全局设置负责输出格式；Word 主模板与技术文档图片在生成标书时按项目上传，避免错误复用。" />
    <Card loading={loading} className="!border-[#E2E8F0] !shadow-none" title={<span className="flex items-center gap-2 text-sm font-semibold"><FileText size={16} color="#2563EB" />文档输出格式</span>}>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <SelectField label="默认格式" value={config.format} onChange={format => update({ format })} options={[{ value: 'standard', label: '标准格式' }, { value: 'custom', label: '自定义格式' }]} />
        <SelectField label="页面大小" value={config.pageSize} onChange={pageSize => update({ pageSize })} options={['A4', 'A3', 'Letter'].map(value => ({ value, label: value }))} />
        <SelectField label="正文字体" value={config.bodyFont} onChange={bodyFont => update({ bodyFont })} options={['宋体', '仿宋', '黑体', '楷体'].map(value => ({ value, label: value }))} />
        <label className="text-xs text-[#64748B]">正文字号（pt）<InputNumber className="!mt-2 !w-full" min={8} max={36} value={config.bodyFontSizePt} onChange={value => { if (value) update({ bodyFontSizePt: value }) }} /></label>
        <label className="text-xs text-[#64748B]">行距<InputNumber className="!mt-2 !w-full" min={1} max={3} step={0.1} value={config.lineSpacing} onChange={value => { if (value) update({ lineSpacing: value }) }} /></label>
        <SelectField label="页边距" value={config.marginMode} onChange={marginMode => update({ marginMode })} options={[{ value: 'standard', label: '标准' }, { value: 'narrow', label: '窄' }, { value: 'wide', label: '宽' }]} />
      </div>
    </Card>
    <Card className="!border-[#E2E8F0] !shadow-none" title="拆分与水印">
      <div className="space-y-4"><ToggleRow title="按标书章节拆分输出" checked={config.splitBySection} onChange={splitBySection => update({ splitBySection })} /><Divider className="!my-3" /><ToggleRow title="启用文档水印" checked={config.watermarkEnabled} onChange={watermarkEnabled => update({ watermarkEnabled })} /><Input disabled={!config.watermarkEnabled} value={config.watermarkText || ''} placeholder="水印文字" onChange={event => update({ watermarkText: event.target.value || undefined })} /></div>
    </Card>
    <SettingsFooter dirty={dirty} loading={loading} lastSaved={lastSaved} onReset={() => { setConfig(DEFAULT_TEMPLATE); setDirty(true) }} onSave={() => void save()} />
  </div>
}

function NotifySettings() {
  const mockMode = shouldUseMocks()
  const [config, setConfig] = useState<NotificationSettings>(DEFAULT_NOTIFICATION)
  const [dirty, setDirty] = useState(false)
  const [loading, setLoading] = useState(false)
  const [lastSaved, setLastSaved] = useState('')
  useUnsavedChangesGuard(dirty)

  useEffect(() => {
    if (mockMode) return
    const timeout = window.setTimeout(() => {
      setLoading(true)
      platformApi.getNotificationSettings().then(setConfig).catch(error => message.error(error instanceof Error ? error.message : '通知配置加载失败')).finally(() => setLoading(false))
    }, 0)
    return () => window.clearTimeout(timeout)
  }, [mockMode])

  const update = (patch: Partial<NotificationSettings>) => { setConfig(previous => ({ ...previous, ...patch })); setDirty(true) }
  const save = async () => {
    setLoading(true)
    try {
      if (!mockMode) {
        const { version: _version, ...payload } = config
        setConfig(await platformApi.updateNotificationSettings(payload))
      }
      setDirty(false)
      setLastSaved(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
      message.success('通知配置已保存')
    } catch (error) { message.error(error instanceof Error ? error.message : '通知配置保存失败') } finally { setLoading(false) }
  }

  return <div className="space-y-4">
    <Card loading={loading} className="!border-[#E2E8F0] !shadow-none" title={<span className="flex items-center gap-2 text-sm font-semibold"><Bell size={16} color="#2563EB" />通知通道</span>}>
      <div className="space-y-4"><ToggleRow title="站内通知" checked={config.inAppEnabled} onChange={inAppEnabled => update({ inAppEnabled })} /><Divider className="!my-3" /><ToggleRow title="邮件通知" checked={config.emailEnabled} onChange={emailEnabled => update({ emailEnabled })} /></div>
    </Card>
    <Card className="!border-[#E2E8F0] !shadow-none" title="资质提前提醒">
      <Select mode="multiple" className="w-full" value={config.qualificationReminderDays} onChange={qualificationReminderDays => update({ qualificationReminderDays })} options={[15, 30, 60, 90, 120].map(value => ({ value, label: `提前 ${value} 天` }))} />
    </Card>
    <Card className="!border-[#E2E8F0] !shadow-none" title="通知事件">
      <div className="space-y-3">{Object.entries(config.events).map(([event, enabled]) => <ToggleRow key={event} title={EVENT_LABELS[event] || event} checked={enabled} onChange={checked => update({ events: { ...config.events, [event]: checked } })} />)}</div>
    </Card>
    <SettingsFooter dirty={dirty} loading={loading} lastSaved={lastSaved} onReset={() => { setConfig(DEFAULT_NOTIFICATION); setDirty(true) }} onSave={() => void save()} />
  </div>
}

type AuditRow = Pick<AuditEvent, 'id' | 'actorName' | 'action' | 'summary' | 'aggregateType' | 'requestId' | 'createdAt'> & { ipAddress?: string }

function OperationLogs() {
  const mockMode = shouldUseMocks()
  const [rows, setRows] = useState<AuditRow[]>(mockAuditRows())
  const [keyword, setKeyword] = useState('')
  const [actionFilter, setActionFilter] = useState('all')
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    if (mockMode) return
    setLoading(true)
    try {
      const result = await platformApi.listAuditEvents({ page: 1, pageSize: 100, sortOrder: 'desc' })
      setRows(result.data)
    } catch (error) {
      message.error(error instanceof Error ? error.message : '审计日志加载失败')
    } finally { setLoading(false) }
  }, [mockMode])

  useEffect(() => {
    const timeout = window.setTimeout(() => void load(), 0)
    return () => window.clearTimeout(timeout)
  }, [load])
  const actions = Array.from(new Set(rows.map(row => row.action)))
  const filtered = useMemo(() => rows.filter(row => {
    const haystack = `${row.actorName} ${row.action} ${row.summary} ${row.aggregateType} ${row.ipAddress || ''}`.toLowerCase()
    return (!keyword.trim() || haystack.includes(keyword.trim().toLowerCase())) && (actionFilter === 'all' || row.action === actionFilter)
  }), [actionFilter, keyword, rows])

  const exportRows = async () => {
    if (mockMode) {
      downloadTableAsCsv('系统操作日志.csv', ['时间', '用户', '操作', '资源', '摘要', 'IP地址'], filtered.map(row => [row.createdAt, row.actorName, row.action, row.aggregateType, row.summary, row.ipAddress || '']))
      return
    }
    try {
      const blob = await platformApi.exportAuditEvents({ action: actionFilter === 'all' ? undefined : actionFilter })
      saveBlob(blob, '系统操作日志.xlsx')
    } catch (error) { message.error(error instanceof Error ? error.message : '审计日志导出失败') }
  }

  return <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="flex items-center gap-2 text-sm font-semibold"><Clock size={16} color="#2563EB" />操作日志</span>} extra={<Space><Button size="small" icon={<RefreshCw size={13} />} onClick={() => void load()}>刷新</Button><Button size="small" onClick={() => void exportRows()}>导出当前结果</Button></Space>}>
    <div className="mb-4 flex flex-wrap gap-2"><Input allowClear value={keyword} onChange={event => setKeyword(event.target.value)} placeholder="搜索用户、操作、资源、摘要或 IP" className="!w-80" /><Select value={actionFilter} onChange={setActionFilter} className="w-52" options={[{ value: 'all', label: '全部操作' }, ...actions.map(value => ({ value, label: value }))]} /><Button onClick={() => { setKeyword(''); setActionFilter('all') }}>重置</Button><span className="self-center text-xs text-[#64748B]">共 {filtered.length} 条</span></div>
    <Table loading={loading} rowKey="id" dataSource={filtered} pagination={{ pageSize: 10, showSizeChanger: false }} columns={[
      { title: '时间', dataIndex: 'createdAt', width: 180, render: value => <span className="text-xs text-[#64748B]">{formatDate(value)}</span> },
      { title: '用户', dataIndex: 'actorName', width: 120 },
      { title: '操作', dataIndex: 'action', width: 180, render: value => <Tag color="blue">{value}</Tag> },
      { title: '资源', dataIndex: 'aggregateType', width: 130 },
      { title: '摘要', dataIndex: 'summary' },
      { title: 'IP 地址', dataIndex: 'ipAddress', width: 130, render: value => value || '-' },
    ]} />
  </Card>
}

function SettingsFooter({ dirty, loading, lastSaved, onReset, onSave }: { dirty: boolean; loading: boolean; lastSaved: string; onReset: () => void; onSave: () => void }) {
  return <div className="sticky bottom-3 z-10 flex items-center justify-between gap-3 rounded-xl border border-[#E2E8F0] bg-white/95 px-4 py-3 shadow-lg backdrop-blur"><span className={`text-xs ${dirty ? 'text-[#D97706]' : 'text-[#64748B]'}`}>{dirty ? '存在未保存配置' : lastSaved ? `已保存于 ${lastSaved}` : '当前配置已同步'}</span><div className="flex gap-3"><Button icon={<RotateCcw size={15} />} onClick={onReset}>恢复默认</Button><Button type="primary" icon={<Save size={15} />} disabled={!dirty} loading={loading} onClick={onSave}>保存配置</Button></div></div>
}

function ToggleRow({ title, checked, onChange }: { title: string; checked: boolean; onChange: (checked: boolean) => void }) {
  return <div className="flex items-center justify-between"><span className="text-sm font-medium text-[#1E293B]">{title}</span><Switch checked={checked} onChange={onChange} /></div>
}

function SettingSlider({ label, value, min, max, step, onChange }: { label: string; value: number; min: number; max: number; step: number; onChange: (value: number) => void }) {
  return <div><div className="flex justify-between text-xs text-[#64748B]"><span>{label}</span><span>{value.toFixed(step < 1 ? 2 : 0)}</span></div><Slider min={min} max={max} step={step} value={value} onChange={onChange} /></div>
}

function ModeButton({ active, title, description, onClick }: { active: boolean; title: string; description: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`rounded-xl border-2 p-4 text-left ${active ? 'border-[#2563EB] bg-[#EFF6FF]' : 'border-[#E2E8F0] hover:border-[#CBD5E1]'}`}><div className="font-semibold text-[#1E293B]">{title}</div><div className="mt-1 text-xs text-[#64748B]">{description}</div></button>
}

function SelectField<T extends string>({ label, value, options, onChange }: { label: string; value: T; options: { value: string; label: string }[]; onChange: (value: T) => void }) {
  return <label className="text-xs text-[#64748B]">{label}<Select className="!mt-2 w-full" value={value} options={options} onChange={onChange} /></label>
}

function mockProviders(): ModelProvider[] {
  return [
    { id: 'mock-qwen', provider: 'qwen', displayName: '阿里云百炼', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', apiKeyMasked: 'sk-••••a81f', keyLastFour: 'a81f', enabled: true, connectionStatus: 'connected', version: 1 },
    { id: 'mock-deepseek', provider: 'deepseek', displayName: 'DeepSeek', baseUrl: 'https://api.deepseek.com', apiKeyMasked: 'sk-••••72c9', keyLastFour: '72c9', enabled: true, connectionStatus: 'connected', version: 1 },
  ]
}

function mockProviderFromForm(values: { provider: ModelProvider['provider']; displayName: string; baseUrl: string; apiKey: string }): ModelProvider {
  return { id: `mock-${Date.now()}`, provider: values.provider, displayName: values.displayName, baseUrl: values.baseUrl, apiKeyMasked: `••••${values.apiKey.slice(-4)}`, keyLastFour: values.apiKey.slice(-4), enabled: true, connectionStatus: 'unknown', version: 1 }
}

function mockAgents(): AgentStatus[] {
  return Object.entries(SCENE_LABELS).slice(0, 5).map(([scene, name]) => ({ name: `${name}智能体`, scene, status: 'online', activeProvider: 'qwen', activeModel: 'qwen-plus', queueDepth: 0 }))
}

function mockAuditRows(): AuditRow[] {
  return operationLogs.map(row => ({ id: row.id, actorName: row.user, action: row.action, aggregateType: 'demo', summary: row.target, requestId: row.id, ipAddress: row.ip, createdAt: row.time }))
}

function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('zh-CN', { hour12: false })
}

function useUnsavedChangesGuard(dirty: boolean) {
  useEffect(() => {
    if (!dirty) return undefined
    const handler = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [dirty])
}
