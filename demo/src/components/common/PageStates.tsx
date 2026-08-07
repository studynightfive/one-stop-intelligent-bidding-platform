import type { ReactNode } from 'react'
import { Alert, Button, Empty, Result, Skeleton } from 'antd'
import { AlertTriangle, LockKeyhole, RefreshCw } from 'lucide-react'
import { isApiError } from '../../api/interceptors'

export function LoadingState({ label = '正在加载', rows = 4, compact = false }: { label?: string; rows?: number; compact?: boolean }) {
  return (
    <div className={compact ? 'py-4' : 'rounded-xl border border-[#E2E8F0] bg-white p-6'} data-testid="common-loading-state" aria-busy="true" aria-label={label}>
      <div className="mb-3 text-sm font-medium text-[#475569]">{label}</div>
      <Skeleton active paragraph={{ rows }} title={false} />
    </div>
  )
}
export function EmptyState({
  title = '暂无内容',
  description,
  action,
}: {
  title?: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="py-12" data-testid="common-empty-state">
      <Empty description={<span><strong className="block text-sm text-[#475569]">{title}</strong>{description && <span className="mt-1 block text-xs text-[#64748B]">{description}</span>}</span>}>
        {action}
      </Empty>
    </div>
  )
}

export function ErrorState({ error, onRetry, compact = false }: { error?: unknown; onRetry?: () => void; compact?: boolean }) {
  const title = isApiError(error) ? error.message : error instanceof Error ? error.message : '加载失败，请稍后重试'
  const requestId = isApiError(error) ? error.requestId : undefined
  if (compact) {
    return (
      <Alert
        data-testid="common-error-state"
        type="error"
        showIcon
        message={title}
        description={requestId ? `请求编号：${requestId}` : undefined}
        action={onRetry ? <Button size="small" onClick={onRetry}>重试</Button> : undefined}
      />
    )
  }
  return (
    <Result
      data-testid="common-error-state"
      status="error"
      title={title}
      subTitle={requestId ? `请求编号：${requestId}` : '请检查网络连接，或稍后重新加载。'}
      extra={onRetry ? <Button type="primary" icon={<RefreshCw size={15} />} onClick={onRetry}>重新加载</Button> : undefined}
    />
  )
}

export function ForbiddenState({ onBack }: { onBack?: () => void }) {
  return (
    <Result
      data-testid="common-forbidden-state"
      status="403"
      icon={<LockKeyhole size={54} className="mx-auto text-[#D97706]" />}
      title="没有访问权限"
      subTitle="当前账号没有访问此页面的权限。如需开通，请联系系统管理员。"
      extra={onBack ? <Button type="primary" onClick={onBack}>返回上一页</Button> : undefined}
    />
  )
}

export function ConflictState({ onRefresh }: { onRefresh: () => void }) {
  return (
    <Alert
      data-testid="common-conflict-state"
      type="warning"
      showIcon
      icon={<AlertTriangle size={18} />}
      message="内容已被其他成员更新"
      description="为避免覆盖他人的修改，请刷新后重新提交。"
      action={<Button size="small" onClick={onRefresh}>刷新内容</Button>}
    />
  )
}
