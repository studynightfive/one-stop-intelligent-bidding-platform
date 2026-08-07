import { Button, Result } from 'antd'
import { useNavigate } from 'react-router-dom'
import { ForbiddenState } from './PageStates'

export function ForbiddenPage() {
  const navigate = useNavigate()
  return <div className="p-6"><ForbiddenState onBack={() => navigate(-1)} /></div>
}

export function NotFoundPage() {
  const navigate = useNavigate()
  return (
    <Result
      status="404"
      title="页面不存在"
      subTitle="链接可能已失效，或者页面已经迁移。"
      extra={<Button type="primary" onClick={() => navigate('/dashboard')}>返回工作台</Button>}
    />
  )
}

export function ServerErrorPage() {
  return (
    <Result
      status="500"
      title="服务暂时不可用"
      subTitle="请稍后重试。如问题持续，请向管理员提供当前时间和请求编号。"
      extra={<Button type="primary" onClick={() => window.location.reload()}>重新加载</Button>}
    />
  )
}
