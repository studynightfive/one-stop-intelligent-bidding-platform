import { Alert, Button, Progress, Tag } from 'antd'
import { Ban, CheckCircle2, LoaderCircle, RefreshCw } from 'lucide-react'

export type CommonJobStatus = 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled'

export function JobProgress({
  title,
  status,
  progress = 0,
  message,
  onCancel,
  onRetry,
}: {
  title: string
  status: CommonJobStatus
  progress?: number
  message?: string
  onCancel?: () => void
  onRetry?: () => void
}) {
  if (status === 'failed') {
    return <Alert type="error" showIcon message={`${title}失败`} description={message} action={onRetry ? <Button size="small" icon={<RefreshCw size={13} />} onClick={onRetry}>重试</Button> : undefined} />
  }
  return (
    <div className="rounded-xl border border-[#E2E8F0] bg-white p-4" data-testid="common-job-progress">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-medium text-[#1E293B]">
          {status === 'succeeded' ? <CheckCircle2 size={16} className="text-[#16A34A]" /> : <LoaderCircle size={16} className="animate-spin text-[#2563EB]" />}
          {title}
        </div>
        <Tag color={status === 'succeeded' ? 'green' : status === 'cancelled' ? 'default' : 'blue'}>{status}</Tag>
      </div>
      <Progress percent={status === 'succeeded' ? 100 : progress} status={status === 'cancelled' ? 'exception' : 'active'} />
      <div className="mt-2 flex items-center justify-between gap-3 text-xs text-[#64748B]">
        <span>{message || (status === 'queued' ? '任务正在排队' : '任务正在执行')}</span>
        {onCancel && ['queued', 'running'].includes(status) && <Button size="small" type="text" danger icon={<Ban size={12} />} onClick={onCancel}>取消</Button>}
      </div>
    </div>
  )
}
