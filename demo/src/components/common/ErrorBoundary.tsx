import { Component, type ErrorInfo, type ReactNode } from 'react'
import { Button, Result } from 'antd'

export class AppErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state: { error: Error | null } = { error: null }

  static getDerivedStateFromError(error: Error) {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Application render error', error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#F8FAFC] p-6">
        <Result
          status="500"
          title="页面出现异常"
          subTitle="页面渲染失败，刷新后可继续使用；如果问题持续，请将发生时间反馈给管理员。"
          extra={<Button type="primary" onClick={() => window.location.reload()}>刷新页面</Button>}
        />
      </main>
    )
  }
}
