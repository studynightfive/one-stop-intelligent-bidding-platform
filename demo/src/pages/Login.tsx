import { useState } from 'react'
import { Alert, Button, Checkbox, Divider, Form, Input, Modal, message } from 'antd'
import { ArrowRight, Lock, Mail, ShieldCheck, Zap } from 'lucide-react'
import { currentUser } from '../mock/data'

type LoginValues = { email: string; password: string; remember: boolean }

export default function Login({ onLogin }: { onLogin: () => void | Promise<void> }) {
  const [submitting, setSubmitting] = useState(false)
  const [forgotOpen, setForgotOpen] = useState(false)
  const [forgotForm] = Form.useForm<{ email: string }>()

  const submit = async (_values: LoginValues) => {
    setSubmitting(true)
    try {
      await new Promise(resolve => window.setTimeout(resolve, 420))
      await onLogin()
    } finally {
      setSubmitting(false)
    }
  }

  const sendResetEmail = async () => {
    const { email } = await forgotForm.validateFields()
    setForgotOpen(false)
    forgotForm.resetFields()
    message.success(`密码重置邮件已发送至 ${email}`)
  }

  return (
    <main className="flex min-h-screen" data-testid="login-page">
      <section className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-[#0F172A] p-12 lg:flex" aria-label="产品介绍">
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-blue-600/20 blur-3xl" />
        <div className="z-10 flex items-center gap-3 text-white">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#2563EB]"><Zap size={22} /></div>
          <span className="text-xl font-semibold">一站式智能招投标平台</span>
        </div>

        <div className="z-10 max-w-lg text-white">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-blue-400/30 bg-blue-400/10 px-3 py-1 text-xs text-blue-200">
            <ShieldCheck size={13} /> 企业级协同与权限隔离
          </div>
          <h1 className="mb-4 text-4xl font-bold leading-tight">智能投标 · 智能评标<br />一个平台完成全流程协作</h1>
          <p className="text-lg leading-relaxed text-[#94A3B8]">从招标文件解析、材料准备、AI 审核到供应商评审与归档，所有步骤完整留痕。</p>
          <div className="mt-10 grid grid-cols-2 gap-3">
            {['7 步投标闭环', '6 步评标闭环', '资源库跨项目复用', '权限与审计可追溯'].map(item => (
              <div key={item} className="rounded-lg border border-slate-700 bg-slate-800/60 p-3 text-sm text-[#CBD5E1]">{item}</div>
            ))}
          </div>
        </div>
        <div className="z-10 text-xs text-[#64748B]">Demo 演示模式 · 数据仅保存在当前浏览器</div>
      </section>

      <section className="flex flex-1 items-center justify-center bg-[#F8FAFC] p-6 sm:p-8" aria-label="账号登录">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#2563EB] text-white"><Zap size={22} /></div>
            <span className="text-xl font-semibold text-[#1E293B]">智能招投标平台</span>
          </div>

          <h2 className="mb-1 text-2xl font-semibold text-[#1E293B]">欢迎回来</h2>
          <p className="mb-6 text-sm text-[#64748B]">登录后继续管理投标、评标与企业资源库</p>
          <Alert className="mb-5" type="info" showIcon message="演示账号已预填，可直接登录体验全部 M3 功能。" />

          <Form<LoginValues>
            layout="vertical"
            initialValues={{ email: currentUser.email, password: 'demo123456', remember: true }}
            onFinish={submit}
            requiredMark={false}
          >
            <Form.Item name="email" label="邮箱" rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '请输入有效邮箱地址' }]}>
              <Input size="large" autoComplete="username" prefix={<Mail size={16} className="text-[#94A3B8]" />} placeholder="name@company.com" />
            </Form.Item>
            <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }, { min: 8, message: '密码至少需要 8 位' }]}>
              <Input.Password size="large" autoComplete="current-password" prefix={<Lock size={16} className="text-[#94A3B8]" />} placeholder="请输入密码" />
            </Form.Item>
            <div className="-mt-2 mb-5 flex items-center justify-between text-xs">
              <Form.Item name="remember" valuePropName="checked" noStyle><Checkbox>保持登录</Checkbox></Form.Item>
              <Button type="link" size="small" className="!h-auto !p-0" onClick={() => { forgotForm.setFieldValue('email', currentUser.email); setForgotOpen(true) }}>忘记密码？</Button>
            </div>
            <Button htmlType="submit" type="primary" size="large" block loading={submitting} iconPosition="end" icon={<ArrowRight size={16} />}>
              登录
            </Button>
          </Form>

          <Divider plain className="!my-5 !text-xs">演示快捷入口</Divider>
          <Button size="large" block disabled={submitting} onClick={() => void submit({ email: currentUser.email, password: 'demo123456', remember: true })}>直接进入演示</Button>
          <p className="mt-6 text-center text-xs text-[#64748B]">{currentUser.company} · {currentUser.role} · {currentUser.name}</p>
        </div>
      </section>

      <Modal title="找回密码" open={forgotOpen} onCancel={() => setForgotOpen(false)} onOk={sendResetEmail} okText="发送重置邮件" cancelText="取消">
        <p className="mb-4 text-sm text-[#64748B]">输入账号邮箱。系统只发送一次性重置链接，不会在页面展示临时密码。</p>
        <Form form={forgotForm} layout="vertical" requiredMark={false}>
          <Form.Item name="email" label="账号邮箱" rules={[{ required: true, message: '请输入邮箱' }, { type: 'email', message: '请输入有效邮箱地址' }]}>
            <Input prefix={<Mail size={15} />} placeholder="name@company.com" />
          </Form.Item>
        </Form>
      </Modal>
    </main>
  )
}
