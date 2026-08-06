import { useState } from 'react'
import { Button, Input, Divider, message } from 'antd'
import { Zap, Mail, Lock, ArrowRight } from 'lucide-react'
import { currentUser } from '../mock/data'

export default function Login({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState(currentUser.email)
  const [password, setPassword] = useState('demo123456')

  const submit = () => {
    if (!email.trim() || !password.trim()) {
      message.warning('请输入邮箱和密码，或直接进入演示')
      return
    }
    onLogin()
  }

  return (
    <div className="min-h-screen flex">
      {/* Left brand panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-[#0F172A] flex-col justify-between p-12 relative overflow-hidden">
        <div className="flex items-center gap-3 text-white">
          <div className="w-10 h-10 rounded-xl bg-[#2563EB] flex items-center justify-center">
            <Zap size={22} color="#fff" />
          </div>
          <span className="text-xl font-semibold">一站式智能招投标平台</span>
        </div>

        <div className="text-white max-w-md">
          <h1 className="text-4xl font-bold leading-tight mb-4">
            智能投标 · 智能评标<br />一站式智能招投标平台
          </h1>
          <p className="text-[#94A3B8] text-lg leading-relaxed">
            上传招标文件 → AI拆解需求 → 材料清单 → 智能审核 → 一键输出Word投标文件
          </p>

          <div className="mt-12 space-y-4">
            {[
              '7步闭环流程，全流程AI辅助',
              '多智能体协作：解析、拆解、审核、生成',
              '企业资质库 + 文档片段库，跨任务共享',
              '多项目并行管理，多人协作，全版本可回溯'
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3 text-[#CBD5E1] text-sm">
                <div className="w-1.5 h-1.5 rounded-full bg-[#2563EB]" />
                {item}
              </div>
            ))}
          </div>
        </div>

        <div className="text-[#64748B] text-xs">Demo 演示模式 · 使用模拟数据 · 仅供交互展示</div>
      </div>

      {/* Right login form */}
      <div className="flex-1 flex items-center justify-center p-8 bg-[#F8FAFC]">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-xl bg-[#2563EB] flex items-center justify-center">
              <Zap size={22} color="#fff" />
            </div>
            <span className="text-xl font-semibold text-[#1E293B]">一站式智能招投标平台</span>
          </div>

          <h2 className="text-2xl font-semibold text-[#1E293B] mb-1">欢迎回来</h2>
          <p className="text-sm text-[#64748B] mb-8">登录您的账号开始管理投标项目</p>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-[#334155] mb-1.5 block">邮箱</label>
              <Input
                size="large"
                prefix={<Mail size={16} className="text-[#94A3B8]" />}
                value={email}
                onChange={event => setEmail(event.target.value)}
                placeholder={currentUser.email}
                className="rounded-lg"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-[#334155] mb-1.5 block">密码</label>
              <Input.Password
                size="large"
                prefix={<Lock size={16} className="text-[#94A3B8]" />}
                value={password}
                onChange={event => setPassword(event.target.value)}
                onPressEnter={submit}
                placeholder="请输入密码"
                className="rounded-lg"
              />
            </div>

            <Button
              type="primary"
              size="large"
              block
              onClick={submit}
              className="rounded-lg h-11 flex items-center justify-center gap-2"
              style={{ background: '#2563EB' }}
            >
              登录
              <ArrowRight size={16} />
            </Button>
          </div>

          <Divider plain className="text-xs text-[#94A3B8]">演示模式</Divider>

          <div className="text-center">
            <p className="text-xs text-[#94A3B8] mb-3">
              这是演示Demo，点击登录即可直接进入系统
            </p>
            <Button type="default" size="large" block onClick={onLogin} className="rounded-lg h-11">
              直接进入演示
            </Button>
          </div>

          <p className="text-xs text-center text-[#94A3B8] mt-6">
            {currentUser.company} · {currentUser.role} · {currentUser.name}
          </p>
        </div>
      </div>
    </div>
  )
}
