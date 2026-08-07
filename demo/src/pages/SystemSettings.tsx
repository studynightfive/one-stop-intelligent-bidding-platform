import { useEffect, useMemo, useState } from 'react'
import { Card, Switch, Input, Select, Slider, Button, Tag, Table, Progress, Divider, message, Alert, InputNumber, Modal, Form, Space } from 'antd'
import {
  Bot, Server, FileText, Bell, HardDrive, Cpu, Zap, Shield, AlertTriangle,
  Save, RotateCcw, Eye, EyeOff, Database, Cloud, Clock
} from 'lucide-react'
import { aiModelConfig, modelOptions, systemConfig, docTemplateConfig, operationLogs } from '../mock/data'
import { downloadTableAsCsv } from '../utils/demoActions'
import { AppUpload } from '../components/common'

type TabKey = 'ai' | 'deploy' | 'template' | 'notify' | 'logs'

export default function SystemSettings() {
  const [activeTab, setActiveTab] = useState<TabKey>('ai')

  const menuItems = [
    { key: 'ai', label: 'AI模型配置', icon: Bot },
    { key: 'deploy', label: '部署与存储', icon: Server },
    { key: 'template', label: '文档模板', icon: FileText },
    { key: 'notify', label: '通知设置', icon: Bell },
    { key: 'logs', label: '操作日志', icon: Clock },
  ]

  return (
    <main className="p-4 sm:p-6" data-testid="system-settings-page">
      <div className="mb-6"><h1 className="text-2xl font-semibold text-[#1E293B]">系统设置</h1><p className="mt-1 text-sm text-[#64748B]">统一管理模型路由、部署、模板、通知与操作审计</p></div>
      <div className="flex flex-col lg:flex-row gap-5">
        {/* Left sidebar */}
        <div className="lg:w-52 flex-shrink-0">
          <div className="rounded-xl border border-[#E2E8F0] bg-white p-2 flex lg:block overflow-x-auto" role="tablist" aria-label="系统设置分类">
            {menuItems.map(item => {
              const Icon = item.icon
              const active = activeTab === item.key
              return (
                <button
                  type="button"
                  key={item.key}
                  id={`settings-tab-${item.key}`}
                  role="tab"
                  aria-selected={active}
                  aria-controls={`settings-panel-${item.key}`}
                  onClick={() => setActiveTab(item.key as TabKey)}
                  className={`flex w-full items-center gap-2.5 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors mb-0.5 whitespace-nowrap ${
                    active
                      ? 'bg-[#EFF6FF] text-[#2563EB] font-medium'
                      : 'text-[#475569] hover:bg-[#F8FAFC] hover:text-[#1E293B]'
                  }`}
                >
                  <Icon size={16} className="flex-shrink-0" />
                  <span>{item.label}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Right content */}
        <div className="flex-1 min-w-0">
          <div id="settings-panel-ai" role="tabpanel" aria-labelledby="settings-tab-ai" hidden={activeTab !== 'ai'}><AIModelSettings /></div>
          <div id="settings-panel-deploy" role="tabpanel" aria-labelledby="settings-tab-deploy" hidden={activeTab !== 'deploy'}><DeploySettings /></div>
          <div id="settings-panel-template" role="tabpanel" aria-labelledby="settings-tab-template" hidden={activeTab !== 'template'}><TemplateSettings /></div>
          <div id="settings-panel-notify" role="tabpanel" aria-labelledby="settings-tab-notify" hidden={activeTab !== 'notify'}><NotifySettings /></div>
          <div id="settings-panel-logs" role="tabpanel" aria-labelledby="settings-tab-logs" hidden={activeTab !== 'logs'}><OperationLogs /></div>
        </div>
      </div>
    </main>
  )
}

function AIModelSettings() {
  const [temp, setTemp] = useState(aiModelConfig.temperature * 10)
  const [topP, setTopP] = useState(90)
  const [testing, setTesting] = useState('')
  const [dirty, setDirty] = useState(false)
  const [lastSaved, setLastSaved] = useState('')
  const [providerOpen, setProviderOpen] = useState(false)
  const [providerForm] = Form.useForm()
  const [providers, setProviders] = useState([
    { id: 'aliyun', name: '阿里云百炼', baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1', apiKey: 'sk-••••••••••••••••a81f', enabled: true, status: 'connected' },
    { id: 'deepseek', name: 'DeepSeek', baseUrl: 'https://api.deepseek.com', apiKey: 'sk-••••••••••••••••72c9', enabled: true, status: 'connected' },
    { id: 'zhipu', name: '智谱 AI', baseUrl: 'https://open.bigmodel.cn/api/paas/v4', apiKey: '••••••••••••••••••43b2', enabled: true, status: 'connected' },
  ])
  const [routes, setRoutes] = useState([
    { id: 'parse', scene: '招标文件解析', primary: 'qwen-plus', fallback: 'glm-4-plus' },
    { id: 'extract', scene: '需求与评分项提取', primary: 'qwen-plus', fallback: 'deepseek-v3' },
    { id: 'generate', scene: '投标文件生成', primary: 'qwen-max', fallback: 'qwen-plus' },
    { id: 'review', scene: '内容与废标风险审核', primary: 'deepseek-v3', fallback: 'qwen-plus' },
    { id: 'evaluation', scene: '评标分析', primary: 'deepseek-v3', fallback: 'glm-4-plus' },
  ])
  useUnsavedChangesGuard(dirty)

  const updateProvider = (id: string, patch: Record<string, any>) => {
    setProviders(prev => prev.map(item => item.id === id ? { ...item, ...patch } : item))
    setDirty(true)
  }

  const updateRoute = (id: string, field: 'primary' | 'fallback', value: string) => {
    setRoutes(prev => prev.map(item => item.id === id ? { ...item, [field]: value } : item))
    setDirty(true)
  }

  const testProvider = (id: string, name: string) => {
    setTesting(id)
    window.setTimeout(() => {
      setTesting('')
      updateProvider(id, { status: 'connected' })
      message.success(`${name} 连接测试通过（Demo）`)
    }, 700)
  }

  const resetAIConfig = () => {
    setTemp(aiModelConfig.temperature * 10)
    setTopP(90)
    setProviders(prev => prev.map(item => ({ ...item, enabled: true, status: 'connected' })))
    setRoutes([
      { id: 'parse', scene: '招标文件解析', primary: 'qwen-plus', fallback: 'glm-4-plus' },
      { id: 'extract', scene: '需求与评分项提取', primary: 'qwen-plus', fallback: 'deepseek-v3' },
      { id: 'generate', scene: '投标文件生成', primary: 'qwen-max', fallback: 'qwen-plus' },
      { id: 'review', scene: '内容与废标风险审核', primary: 'deepseek-v3', fallback: 'qwen-plus' },
      { id: 'evaluation', scene: '评标分析', primary: 'deepseek-v3', fallback: 'glm-4-plus' },
    ])
    setDirty(true)
    message.info('已恢复演示默认配置，请点击保存生效')
  }

  const saveAIConfig = () => {
    setDirty(false)
    setLastSaved(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
    message.success('AI 模型配置已保存')
  }

  const addProvider = async () => {
    const values = await providerForm.validateFields()
    const suffix = String(values.apiKey).slice(-4)
    setProviders(previous => [...previous, {
      id: `provider-${Date.now()}`,
      name: values.name,
      baseUrl: values.baseUrl,
      apiKey: `••••••••••••••••••${suffix}`,
      enabled: true,
      status: 'connected',
    }])
    setProviderOpen(false)
    providerForm.resetFields()
    setDirty(true)
    message.success('模型服务商已添加，密钥已脱敏显示')
  }

  return (
    <div className="space-y-4">
      {/* Model routing */}
      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><Cpu size={16} color="#2563EB" /> 多模型路由配置</span>}>
        <Alert type="info" showIcon message="按业务场景配置主模型与降级模型，避免一套模型承担所有任务。" className="!rounded-lg mb-4" />
        <Table
          dataSource={routes}
          rowKey="id"
          pagination={false}
          size="small"
          columns={[
            { title: '业务场景', dataIndex: 'scene', width: 190, render: (value: string) => <span className="font-medium text-[#1E293B]">{value}</span> },
            { title: '主模型', dataIndex: 'primary', render: (value: string, record: any) => <Select value={value} className="w-full" onChange={next => updateRoute(record.id, 'primary', next)} options={modelOptions.map(model => ({ value: model.value, label: model.label }))} /> },
            { title: '降级模型', dataIndex: 'fallback', render: (value: string, record: any) => <Select value={value} className="w-full" onChange={next => updateRoute(record.id, 'fallback', next)} options={modelOptions.map(model => ({ value: model.value, label: model.label }))} /> },
            { title: '策略', width: 110, render: () => <Tag color="blue">失败自动降级</Tag> },
          ]}
        />
      </Card>

      {/* Provider credentials */}
      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><Shield size={16} color="#2563EB" /> 模型服务商与凭据</span>} extra={<Button size="small" onClick={() => setProviderOpen(true)}>新增服务商</Button>}>
        <Alert
          type="warning"
          showIcon
          message="Demo 仅展示脱敏密钥"
          description="正式环境的 API Key 应由服务端加密保存、按权限更新并记录审计日志，前端不得读取完整密钥。"
          className="!rounded-lg mb-4"
        />
        <Table
          dataSource={providers}
          rowKey="id"
          pagination={false}
          size="small"
          columns={[
            { title: '服务商', dataIndex: 'name', width: 130, render: (value: string, record: any) => <div><div className="font-medium text-[#1E293B]">{value}</div><Tag color={record.status === 'connected' ? 'green' : 'red'} className="mt-1">{record.status === 'connected' ? '连接正常' : '连接异常'}</Tag></div> },
            { title: 'Base URL', dataIndex: 'baseUrl', render: (value: string, record: any) => <Input value={value} onChange={event => updateProvider(record.id, { baseUrl: event.target.value })} /> },
            { title: 'API Key（脱敏）', dataIndex: 'apiKey', width: 250, render: (value: string, record: any) => <Space.Compact className="w-full"><Input value={value} type="password" onChange={event => updateProvider(record.id, { apiKey: event.target.value })} /><Button onClick={() => message.info(`${record.name} 密钥更新入口（Demo）`)}>更新</Button></Space.Compact> },
            { title: '启用', dataIndex: 'enabled', width: 70, render: (value: boolean, record: any) => <Switch checked={value} onChange={checked => updateProvider(record.id, { enabled: checked })} /> },
            { title: '连接测试', width: 100, render: (_: any, record: any) => <Button size="small" loading={testing === record.id} disabled={!record.enabled} onClick={() => testProvider(record.id, record.name)}>测试连接</Button> },
          ]}
        />
      </Card>

      {/* Parameters */}
      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><Zap size={16} color="#2563EB" /> 生成参数</span>}>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs text-[#64748B]">Temperature（创造性）</label>
              <span className="text-xs font-medium text-[#1E293B]">{(temp / 10).toFixed(1)}</span>
            </div>
            <Slider
              min={0}
              max={10}
              value={temp}
              onChange={value => { setTemp(value); setDirty(true) }}
              tooltip={{ open: false }}
            />
            <div className="flex justify-between text-xs text-[#CBD5E1] mt-1">
              <span>精确</span>
              <span>创造</span>
            </div>
          </div>
          <div>
            <div className="flex items-center justify-between mb-2"><label className="text-xs text-[#64748B]">Top P</label><span className="text-xs font-medium text-[#1E293B]">{(topP / 100).toFixed(2)}</span></div>
            <Slider min={0} max={100} value={topP} onChange={value => { setTopP(value); setDirty(true) }} tooltip={{ open: false }} />
            <div className="text-xs text-[#64748B] mt-1">控制候选词采样范围</div>
          </div>
          <div>
            <label className="block text-xs text-[#64748B] mb-2">最大输出 Token 数</label>
            <Select
              className="w-full"
              defaultValue={aiModelConfig.maxTokens}
              onChange={() => setDirty(true)}
              options={[
                { value: 4096, label: '4096' },
                { value: 8192, label: '8192' },
                { value: 16384, label: '16384' },
                { value: 32768, label: '32768' },
              ]}
            />
          </div>
          <div>
            <label className="block text-xs text-[#64748B] mb-2">请求超时（秒）</label>
            <InputNumber min={10} max={300} defaultValue={aiModelConfig.timeout} onChange={() => setDirty(true)} className="!w-full" />
            <div className="text-xs text-[#64748B] mt-1.5">超时后按场景路由执行降级</div>
          </div>
        </div>

        <Divider className="!my-4" />

        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-[#1E293B] font-medium">熔断器模式</div>
              <div className="text-xs text-[#64748B] mt-0.5">连续失败时自动切换到备用模型，防止级联故障</div>
            </div>
            <Switch defaultChecked={aiModelConfig.enableCircuitBreaker} onChange={() => setDirty(true)} />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-[#1E293B] font-medium">自动重试</div>
              <div className="text-xs text-[#64748B] mt-0.5">请求失败时自动重试，最多 {aiModelConfig.retryCount} 次</div>
            </div>
            <Switch defaultChecked onChange={() => setDirty(true)} />
          </div>
        </div>
      </Card>

      {/* Agent status */}
      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><Bot size={16} color="#2563EB" /> 智能体状态</span>}>
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
          {[
            { name: '文档解析Agent', status: 'online', model: 'qwen-plus' },
            { name: '需求提取Agent', status: 'online', model: 'qwen-plus' },
            { name: '材料匹配Agent', status: 'online', model: 'qwen-plus' },
            { name: '内容审核Agent', status: 'online', model: 'deepseek-v3' },
            { name: '文档生成Agent', status: 'online', model: 'qwen-plus' },
            { name: '版本管理Agent', status: 'online', model: 'qwen-plus' },
            { name: '编排Agent', status: 'online', model: 'qwen-plus' },
            { name: '兜底Agent', status: 'standby', model: 'glm-4-plus' },
          ].map(agent => (
            <div key={agent.name} className="rounded-lg border border-[#E2E8F0] p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-medium text-[#1E293B] truncate">{agent.name}</span>
                <div className={`w-2 h-2 rounded-full ${agent.status === 'online' ? 'bg-[#16A34A]' : 'bg-[#D97706]'}`} />
              </div>
              <div className="text-xs text-[#94A3B8]">{agent.model}</div>
              <div className="text-xs mt-1" style={{ color: agent.status === 'online' ? '#16A34A' : '#D97706' }}>
                {agent.status === 'online' ? '运行中' : '待命'}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="sticky bottom-3 z-10 flex items-center justify-between gap-3 rounded-xl border border-[#E2E8F0] bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
        <span className={`text-xs ${dirty ? 'text-[#D97706]' : 'text-[#64748B]'}`}>{dirty ? '存在未保存配置' : lastSaved ? `已保存于 ${lastSaved}` : '当前配置已同步'}</span>
        <div className="flex gap-3">
          <Button onClick={resetAIConfig} icon={<RotateCcw size={15} />}>恢复默认</Button>
          <Button onClick={saveAIConfig} type="primary" icon={<Save size={15} />} disabled={!dirty}>保存配置</Button>
        </div>
      </div>

      <Modal title="新增模型服务商" open={providerOpen} onCancel={() => setProviderOpen(false)} onOk={addProvider} okText="添加" cancelText="取消">
        <Form form={providerForm} layout="vertical" requiredMark={false} className="pt-3">
          <Form.Item name="name" label="显示名称" rules={[{ required: true, message: '请输入服务商名称' }]}><Input placeholder="企业模型网关" /></Form.Item>
          <Form.Item name="baseUrl" label="Base URL" rules={[{ required: true, type: 'url', message: '请输入有效 URL' }]}><Input placeholder="https://ai.example.com/v1" /></Form.Item>
          <Form.Item name="apiKey" label="API Key" rules={[{ required: true, min: 8, message: '请输入有效密钥' }]}><Input.Password placeholder="保存后仅显示末四位" /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

function DeploySettings() {
  const defaults = {
    deploymentMode: systemConfig.deploymentMode,
    companyName: systemConfig.companyName,
    maxProjects: systemConfig.maxProjects,
    maxUsers: systemConfig.maxUsers,
    storageQuota: systemConfig.storageQuota,
    enableAutoBackup: systemConfig.enableAutoBackup,
    enableVersionControl: systemConfig.enableVersionControl,
    backupFrequency: 'daily',
  }
  const [config, setConfig] = useState(defaults)
  const [dirty, setDirty] = useState(false)
  const [lastSaved, setLastSaved] = useState('')
  const storagePercent = Math.round((systemConfig.storageUsed / config.storageQuota) * 100)
  useUnsavedChangesGuard(dirty)

  const updateConfig = (patch: Partial<typeof defaults>) => {
    setConfig(previous => ({ ...previous, ...patch }))
    setDirty(true)
  }

  const reset = () => {
    setConfig(defaults)
    setDirty(true)
    message.info('已恢复部署默认值，请保存后生效')
  }

  const save = () => {
    setDirty(false)
    setLastSaved(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
    message.success('部署、存储与备份配置已保存')
  }

  return (
    <div className="space-y-4">
      {/* Deployment mode */}
      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><Cloud size={16} color="#2563EB" /> 部署模式</span>}>
        <div className="grid grid-cols-2 gap-4">
          <button type="button" onClick={() => updateConfig({ deploymentMode: 'saas' })} className={`rounded-xl border-2 p-4 text-left transition-colors ${config.deploymentMode === 'saas' ? 'border-[#2563EB] bg-[#EFF6FF]' : 'border-[#E2E8F0]'}`}>
            <div className="flex items-center gap-2 mb-2">
              <Cloud size={18} color="#2563EB" />
              <span className="text-sm font-semibold text-[#1E293B]">SaaS 多租户</span>
              {config.deploymentMode === 'saas' && <Tag color="blue" className="!text-xs !ml-auto">当前</Tag>}
            </div>
            <p className="text-xs text-[#64748B] leading-relaxed">共享云基础设施，按租户隔离数据，开箱即用，无需运维</p>
          </button>
          <button type="button" onClick={() => updateConfig({ deploymentMode: 'private' })} className={`rounded-xl border-2 p-4 text-left transition-colors ${config.deploymentMode === 'private' ? 'border-[#2563EB] bg-[#EFF6FF]' : 'border-[#E2E8F0] hover:border-[#CBD5E1]'}`}>
            <div className="flex items-center gap-2 mb-2">
              <Server size={18} color="#64748B" />
              <span className="text-sm font-semibold text-[#1E293B]">私有化部署</span>
              {config.deploymentMode === 'private' && <Tag color="blue" className="!text-xs !ml-auto">当前</Tag>}
            </div>
            <p className="text-xs text-[#64748B] leading-relaxed">独立部署在企业内网，数据完全自主可控，支持定制化</p>
          </button>
        </div>
      </Card>

      {/* Company info */}
      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><Database size={16} color="#2563EB" /> 企业信息</span>}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-[#64748B] mb-2">企业名称</label>
            <Input value={config.companyName} onChange={event => updateConfig({ companyName: event.target.value })} />
          </div>
          <div>
            <label className="block text-xs text-[#64748B] mb-2">最大项目数</label>
            <Space.Compact className="w-full"><InputNumber min={1} value={config.maxProjects} onChange={value => updateConfig({ maxProjects: value || 1 })} className="!w-full" /><Input value="个" disabled className="!w-14 !text-center" aria-label="项目数量单位" /></Space.Compact>
          </div>
          <div>
            <label className="block text-xs text-[#64748B] mb-2">最大用户数</label>
            <Space.Compact className="w-full"><InputNumber min={1} value={config.maxUsers} onChange={value => updateConfig({ maxUsers: value || 1 })} className="!w-full" /><Input value="人" disabled className="!w-14 !text-center" aria-label="用户数量单位" /></Space.Compact>
          </div>
          <div>
            <label className="block text-xs text-[#64748B] mb-2">存储配额</label>
            <Space.Compact className="w-full"><InputNumber min={systemConfig.storageUsed} value={config.storageQuota} onChange={value => updateConfig({ storageQuota: value || systemConfig.storageUsed })} className="!w-full" /><Input value="GB" disabled className="!w-14 !text-center" aria-label="存储配额单位" /></Space.Compact>
          </div>
        </div>
      </Card>

      {/* Storage */}
      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><HardDrive size={16} color="#2563EB" /> 存储用量</span>}>
        <div className="flex items-center gap-4">
          <div className="flex-1">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-[#64748B]">已使用 {systemConfig.storageUsed} GB / {config.storageQuota} GB</span>
              <span className="text-xs font-medium text-[#1E293B]">{storagePercent}%</span>
            </div>
            <Progress percent={storagePercent} strokeColor="#2563EB" showInfo={false} />
          </div>
        </div>
        <div className="grid grid-cols-4 gap-3 mt-4">
          {[
            { label: '招标文件', size: '12 GB', color: '#2563EB' },
            { label: '投标材料', size: '85 GB', color: '#16A34A' },
            { label: '输出文档', size: '45 GB', color: '#D97706' },
            { label: '其他', size: '45 GB', color: '#94A3B8' },
          ].map(item => (
            <div key={item.label} className="rounded-lg bg-[#F8FAFC] p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <div className="w-2 h-2 rounded-full" style={{ background: item.color }} />
                <span className="text-xs text-[#64748B]">{item.label}</span>
              </div>
              <span className="text-sm font-semibold text-[#1E293B]">{item.size}</span>
            </div>
          ))}
        </div>
      </Card>

      {/* Backup */}
      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><Shield size={16} color="#2563EB" /> 数据备份</span>}>
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-[#1E293B] font-medium">自动备份</div>
              <div className="text-xs text-[#64748B] mt-0.5">定期备份所有数据，防止数据丢失</div>
            </div>
            <Switch checked={config.enableAutoBackup} onChange={checked => updateConfig({ enableAutoBackup: checked })} />
          </div>
          <Divider className="!my-3" />
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-[#1E293B] font-medium">版本控制</div>
              <div className="text-xs text-[#64748B] mt-0.5">保留所有投标文件版本，支持回溯对比</div>
            </div>
            <Switch checked={config.enableVersionControl} onChange={checked => updateConfig({ enableVersionControl: checked })} />
          </div>
          <Divider className="!my-3" />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div><div className="text-sm font-medium text-[#1E293B]">备份频率</div><div className="mt-0.5 text-xs text-[#64748B]">自动备份保留最近 30 个恢复点</div></div>
            <div className="flex items-center gap-2"><Select disabled={!config.enableAutoBackup} value={config.backupFrequency} onChange={value => updateConfig({ backupFrequency: value })} options={[{ value: 'hourly', label: '每小时' }, { value: 'daily', label: '每天' }, { value: 'weekly', label: '每周' }]} className="w-28" /><Button onClick={() => message.success('手动备份任务已创建')}>立即备份</Button></div>
          </div>
        </div>
      </Card>

      <div className="sticky bottom-3 z-10 flex items-center justify-between gap-3 rounded-xl border border-[#E2E8F0] bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
        <span className={`text-xs ${dirty ? 'text-[#D97706]' : 'text-[#64748B]'}`}>{dirty ? '存在未保存配置' : lastSaved ? `已保存于 ${lastSaved}` : '当前配置已同步'}</span>
        <div className="flex gap-3"><Button onClick={reset} icon={<RotateCcw size={15} />}>恢复默认</Button><Button disabled={!dirty} onClick={save} type="primary" icon={<Save size={15} />}>保存配置</Button></div>
      </div>
    </div>
  )
}

function TemplateSettings() {
  const defaults = { ...docTemplateConfig }
  const [config, setConfig] = useState(defaults)
  const [templateFile, setTemplateFile] = useState('标准投标文件模板.docx')
  const [logoFile, setLogoFile] = useState('企业标识.png')
  const [dirty, setDirty] = useState(false)
  const [lastSaved, setLastSaved] = useState('')
  useUnsavedChangesGuard(dirty)

  const updateConfig = (patch: Partial<typeof defaults>) => {
    setConfig(previous => ({ ...previous, ...patch }))
    setDirty(true)
  }

  const reset = () => {
    setConfig(defaults)
    setTemplateFile('标准投标文件模板.docx')
    setLogoFile('企业标识.png')
    setDirty(true)
    message.info('已恢复文档模板默认值，请保存后生效')
  }

  const save = () => {
    setDirty(false)
    setLastSaved(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
    message.success('文档模板配置已保存')
  }

  return (
    <div className="space-y-4">
      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><FileText size={16} color="#2563EB" /> 文档输出格式</span>}>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-[#64748B] mb-2">默认格式</label>
            <Select
              className="w-full"
              value={config.defaultFormat}
              onChange={value => updateConfig({ defaultFormat: value })}
              options={[
                { value: 'standard', label: '标准格式' },
                { value: 'custom', label: '自定义格式' },
              ]}
            />
          </div>
          <div>
            <label className="block text-xs text-[#64748B] mb-2">页面大小</label>
            <Select
              className="w-full"
              value={config.pageSize}
              onChange={value => updateConfig({ pageSize: value })}
              options={[
                { value: 'A4', label: 'A4' },
                { value: 'A3', label: 'A3' },
                { value: 'Letter', label: 'Letter' },
              ]}
            />
          </div>
          <div>
            <label className="block text-xs text-[#64748B] mb-2">正文字体</label>
            <Select
              className="w-full"
              value={config.fontFamily}
              onChange={value => updateConfig({ fontFamily: value })}
              options={[
                { value: '宋体', label: '宋体' },
                { value: '仿宋', label: '仿宋' },
                { value: '黑体', label: '黑体' },
                { value: '楷体', label: '楷体' },
              ]}
            />
          </div>
          <div>
            <label className="block text-xs text-[#64748B] mb-2">字号</label>
            <Select
              className="w-full"
              value={config.fontSize}
              onChange={value => updateConfig({ fontSize: value })}
              options={[
                { value: '10pt', label: '10pt' },
                { value: '12pt', label: '12pt' },
                { value: '14pt', label: '14pt' },
              ]}
            />
          </div>
          <div>
            <label className="block text-xs text-[#64748B] mb-2">行距</label>
            <Select
              className="w-full"
              value={config.lineHeight}
              onChange={value => updateConfig({ lineHeight: value })}
              options={[
                { value: '1.0', label: '单倍行距' },
                { value: '1.15', label: '1.15倍' },
                { value: '1.5', label: '1.5倍' },
                { value: '2.0', label: '双倍行距' },
              ]}
            />
          </div>
          <div>
            <label className="block text-xs text-[#64748B] mb-2">页边距</label>
            <Select
              className="w-full"
              value={config.margin}
              onChange={value => updateConfig({ margin: value })}
              options={[
                { value: '标准', label: '标准' },
                { value: '窄', label: '窄' },
                { value: '宽', label: '宽' },
              ]}
            />
          </div>
        </div>
      </Card>

      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><FileText size={16} color="#2563EB" /> 拆分与水印</span>}>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-[#1E293B] font-medium">自动拆分投标文件</div>
              <div className="text-xs text-[#64748B] mt-0.5">根据招标文件要求，自动拆分为资质标、商务标、技术标</div>
            </div>
            <Switch checked={config.enableAutoSplit} onChange={checked => updateConfig({ enableAutoSplit: checked })} />
          </div>
          <Divider className="!my-3" />
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-[#1E293B] font-medium">文档水印</div>
              <div className="text-xs text-[#64748B] mt-0.5">在输出文档中添加企业标识水印</div>
            </div>
            <Switch checked={config.watermark} onChange={checked => updateConfig({ watermark: checked })} />
          </div>
          <div>
            <label className="block text-xs text-[#64748B] mb-2">水印文字</label>
            <Input disabled={!config.watermark} value={config.watermarkText} onChange={event => updateConfig({ watermarkText: event.target.value })} />
          </div>
        </div>
      </Card>

      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><FileText size={16} color="#2563EB" /> 企业模板文件</span>}>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="rounded-xl border border-[#E2E8F0] p-4"><div className="mb-1 text-sm font-medium text-[#1E293B]">Word 主模板</div><div className="mb-3 text-xs text-[#64748B]">当前：{templateFile}</div><AppUpload compact accept=".doc,.docx" label="更换 Word 模板" onFiles={files => { setTemplateFile(files[0].name); setDirty(true); message.success('Word 模板已选择，保存后生效') }} /></div>
          <div className="rounded-xl border border-[#E2E8F0] p-4"><div className="mb-1 text-sm font-medium text-[#1E293B]">企业 Logo</div><div className="mb-3 text-xs text-[#64748B]">当前：{logoFile}</div><AppUpload compact accept=".png,.jpg,.jpeg,.svg" maxSizeMb={5} label="更换企业标识" onFiles={files => { setLogoFile(files[0].name); setDirty(true); message.success('企业标识已选择，保存后生效') }} /></div>
        </div>
      </Card>

      <div className="sticky bottom-3 z-10 flex items-center justify-between gap-3 rounded-xl border border-[#E2E8F0] bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
        <span className={`text-xs ${dirty ? 'text-[#D97706]' : 'text-[#64748B]'}`}>{dirty ? '存在未保存配置' : lastSaved ? `已保存于 ${lastSaved}` : '当前配置已同步'}</span>
        <div className="flex gap-3"><Button onClick={reset} icon={<RotateCcw size={15} />}>恢复默认</Button><Button disabled={!dirty} onClick={save} type="primary" icon={<Save size={15} />}>保存配置</Button></div>
      </div>
    </div>
  )
}

function NotifySettings() {
  const defaultEvents = [
    { id: 'task_assigned', label: '任务分配', desc: '有新任务分配给你时通知', enabled: true },
    { id: 'ai_review', label: 'AI审核完成', desc: 'AI审核有结果时通知', enabled: true },
    { id: 'material_uploaded', label: '材料上传完成', desc: '团队成员上传材料时通知', enabled: true },
    { id: 'document_version', label: '文档版本更新', desc: '投标文件生成新版本时通知', enabled: true },
    { id: 'qualification_status', label: '资质状态变更', desc: '资质过期/更新时通知', enabled: true },
    { id: 'member_changed', label: '成员加入/退出', desc: '项目成员变动时通知', enabled: false },
  ]
  const defaults = {
    site: systemConfig.enableNotification,
    email: systemConfig.enableEmailNotify,
    expiry: systemConfig.enableExpiryWarning,
    warningDays: systemConfig.expiryWarningDays,
  }
  const [config, setConfig] = useState(defaults)
  const [events, setEvents] = useState(defaultEvents)
  const [dirty, setDirty] = useState(false)
  const [lastSaved, setLastSaved] = useState('')
  useUnsavedChangesGuard(dirty)

  const updateConfig = (patch: Partial<typeof defaults>) => {
    setConfig(previous => ({ ...previous, ...patch }))
    setDirty(true)
  }
  const reset = () => {
    setConfig(defaults)
    setEvents(defaultEvents)
    setDirty(true)
    message.info('已恢复通知默认值，请保存后生效')
  }
  const save = () => {
    setDirty(false)
    setLastSaved(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
    message.success('通知配置已保存')
  }

  return (
    <div className="space-y-4">
      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><Bell size={16} color="#2563EB" /> 通知开关</span>}>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-[#1E293B] font-medium">站内通知</div>
              <div className="text-xs text-[#64748B] mt-0.5">平台内消息提醒</div>
            </div>
            <Switch checked={config.site} onChange={checked => updateConfig({ site: checked })} />
          </div>
          <Divider className="!my-3" />
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-[#1E293B] font-medium">邮件通知</div>
              <div className="text-xs text-[#64748B] mt-0.5">重要事件通过邮件推送</div>
            </div>
            <Switch checked={config.email} onChange={checked => updateConfig({ email: checked })} />
          </div>
        </div>
      </Card>

      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><AlertTriangle size={16} color="#D97706" /> 资质预警</span>}>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-sm text-[#1E293B] font-medium">资质过期预警</div>
              <div className="text-xs text-[#64748B] mt-0.5">资质即将过期时自动提醒相关人员</div>
            </div>
            <Switch checked={config.expiry} onChange={checked => updateConfig({ expiry: checked })} />
          </div>
          <Divider className="!my-3" />
          <div className="flex items-center gap-4">
            <label className="text-xs text-[#64748B] whitespace-nowrap">提前预警天数</label>
            <Select
              style={{ width: 120 }}
              disabled={!config.expiry}
              value={config.warningDays}
              onChange={value => updateConfig({ warningDays: value })}
              options={[
                { value: 15, label: '15天' },
                { value: 30, label: '30天' },
                { value: 60, label: '60天' },
                { value: 90, label: '90天' },
              ]}
            />
          </div>
        </div>

        <div className="mt-4 rounded-lg bg-[#FFFBEB] border border-[#FDE68A] p-3 flex items-start gap-2">
          <AlertTriangle size={16} color="#D97706" className="mt-0.5 flex-shrink-0" />
          <div className="text-xs text-[#92400E]">
            当前有 <span className="font-semibold">2</span> 项资质即将过期，已自动通知负责人。建议在过期前完成更新。
          </div>
        </div>
      </Card>

      <Card className="!border-[#E2E8F0] !shadow-none" title={<span className="text-sm font-semibold flex items-center gap-2"><Bell size={16} color="#2563EB" /> 通知事件配置</span>}>
        <div className="space-y-3">
          {events.map(item => (
            <div key={item.id} className="flex items-center justify-between py-1">
              <div>
                <div className="text-sm text-[#1E293B]">{item.label}</div>
                <div className="text-xs text-[#64748B] mt-0.5">{item.desc}</div>
              </div>
              <Switch checked={item.enabled} size="small" onChange={checked => { setEvents(previous => previous.map(event => event.id === item.id ? { ...event, enabled: checked } : event)); setDirty(true) }} />
            </div>
          ))}
        </div>
      </Card>

      <div className="sticky bottom-3 z-10 flex items-center justify-between gap-3 rounded-xl border border-[#E2E8F0] bg-white/95 px-4 py-3 shadow-lg backdrop-blur">
        <span className={`text-xs ${dirty ? 'text-[#D97706]' : 'text-[#64748B]'}`}>{dirty ? '存在未保存配置' : lastSaved ? `已保存于 ${lastSaved}` : '当前配置已同步'}</span>
        <div className="flex gap-3"><Button onClick={reset} icon={<RotateCcw size={15} />}>恢复默认</Button><Button disabled={!dirty} onClick={save} type="primary" icon={<Save size={15} />}>保存配置</Button></div>
      </div>
    </div>
  )
}

function OperationLogs() {
  const [keyword, setKeyword] = useState('')
  const [actionFilter, setActionFilter] = useState('all')
  const actions = Array.from(new Set(operationLogs.map(row => row.action)))
  const filteredLogs = useMemo(() => operationLogs.filter(row => {
    const matchesKeyword = !keyword.trim() || `${row.user} ${row.action} ${row.target} ${row.ip}`.toLowerCase().includes(keyword.trim().toLowerCase())
    return matchesKeyword && (actionFilter === 'all' || row.action === actionFilter)
  }), [keyword, actionFilter])
  const columns = [
    {
      title: '时间',
      dataIndex: 'time',
      key: 'time',
      width: 160,
      render: (time: string) => <span className="text-xs text-[#94A3B8]">{time}</span>,
    },
    {
      title: '用户',
      dataIndex: 'user',
      key: 'user',
      render: (user: string) => <span className="text-sm font-medium text-[#1E293B]">{user}</span>,
    },
    {
      title: '操作',
      dataIndex: 'action',
      key: 'action',
      render: (action: string) => <Tag className="!text-xs" color="blue">{action}</Tag>,
    },
    {
      title: '目标',
      dataIndex: 'target',
      key: 'target',
      render: (target: string) => <span className="text-sm text-[#475569]">{target}</span>,
    },
    {
      title: 'IP地址',
      dataIndex: 'ip',
      key: 'ip',
      render: (ip: string) => <span className="text-xs text-[#94A3B8] font-mono">{ip}</span>,
    },
  ]

  return (
    <Card className="!border-[#E2E8F0] !shadow-none overflow-x-auto" title={<span className="text-sm font-semibold flex items-center gap-2"><Clock size={16} color="#2563EB" /> 操作日志</span>} extra={<Button size="small" onClick={() => downloadTableAsCsv('系统操作日志.csv', ['时间', '用户', '操作', '目标', 'IP地址'], filteredLogs.map(row => [row.time, row.user, row.action, row.target, row.ip]))}>导出当前结果</Button>}>
      <div className="mb-4 flex flex-wrap gap-2"><Input allowClear value={keyword} onChange={event => setKeyword(event.target.value)} placeholder="搜索用户、操作、目标或 IP" className="!w-72" /><Select value={actionFilter} onChange={setActionFilter} options={[{ value: 'all', label: '全部操作' }, ...actions.map(value => ({ value, label: value }))]} className="w-40" /><Button onClick={() => { setKeyword(''); setActionFilter('all') }}>重置</Button><span className="self-center text-xs text-[#64748B]">共 {filteredLogs.length} 条</span></div>
      <Table
        columns={columns}
        dataSource={filteredLogs}
        rowKey="id"
        pagination={{ pageSize: 10, showSizeChanger: false }}
        size="middle"
      />
    </Card>
  )
}

function useUnsavedChangesGuard(dirty: boolean) {
  useEffect(() => {
    if (!dirty) return undefined
    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [dirty])
}
