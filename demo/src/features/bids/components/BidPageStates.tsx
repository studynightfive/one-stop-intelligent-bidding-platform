import { Button, Result, Spin } from 'antd'
import { AlertTriangle, Lock, RefreshCw, WifiOff } from 'lucide-react'
import { BID_TEST_IDS } from '../constants'

type ActionProps = {
  onRetry?: () => void
  onBack?: () => void
}

export function BidLoadingState({ tip = '正在加载投标数据…' }: { tip?: string }) {
  return (
    <div className="py-20 flex flex-col items-center justify-center" data-testid={BID_TEST_IDS.stateLoading}>
      <Spin size="large" />
      <p className="mt-4 text-sm text-[#64748B]">{tip}</p>
    </div>
  )
}

export function BidEmptyState({
  description = '暂无数据',
  actionLabel,
  onAction,
}: {
  description?: string
  actionLabel?: string
  onAction?: () => void
}) {
  return (
    <div className="py-16" data-testid={BID_TEST_IDS.stateEmpty}>
      <Result
        status="info"
        title="暂无结果"
        subTitle={description}
        extra={actionLabel && onAction ? <Button onClick={onAction}>{actionLabel}</Button> : undefined}
      />
    </div>
  )
}

export function BidErrorState({ onRetry, message = '加载失败，请稍后重试。' }: ActionProps & { message?: string }) {
  return (
    <div className="py-16" data-testid={BID_TEST_IDS.stateError}>
      <Result
        status="error"
        title="请求失败"
        subTitle={message}
        icon={<AlertTriangle className="text-[#DC2626]" size={48} />}
        extra={onRetry ? <Button type="primary" icon={<RefreshCw size={14} />} onClick={onRetry}>重试</Button> : undefined}
      />
    </div>
  )
}

export function BidForbiddenState({ onBack }: ActionProps) {
  return (
    <div className="py-16" data-testid={BID_TEST_IDS.stateForbidden}>
      <Result
        status="403"
        title="无权限访问"
        subTitle="你没有查看该投标资源的权限，请联系项目负责人分配权限。"
        icon={<Lock className="text-[#D97706]" size={48} />}
        extra={onBack ? <Button onClick={onBack}>返回工作台</Button> : undefined}
      />
    </div>
  )
}

export function BidTimeoutState({ onRetry }: ActionProps) {
  return (
    <div className="py-16" data-testid={BID_TEST_IDS.stateTimeout}>
      <Result
        status="warning"
        title="请求超时"
        subTitle="服务响应超时。网络不稳定或异步任务排队中，请重试。"
        icon={<WifiOff className="text-[#D97706]" size={48} />}
        extra={onRetry ? <Button type="primary" icon={<RefreshCw size={14} />} onClick={onRetry}>重新加载</Button> : undefined}
      />
    </div>
  )
}

export function BidConflictState({
  onRetry,
  message = '数据已被其他人更新（版本冲突）。请刷新后重试。',
}: ActionProps & { message?: string }) {
  return (
    <div className="py-16" data-testid={BID_TEST_IDS.stateConflict}>
      <Result
        status="warning"
        title="版本冲突"
        subTitle={message}
        extra={onRetry ? <Button type="primary" onClick={onRetry}>刷新并重试</Button> : undefined}
      />
    </div>
  )
}

export function BidNotFoundState({ onBack }: ActionProps) {
  return (
    <div className="py-16" data-testid={BID_TEST_IDS.taskNotFound}>
      <Result
        status="404"
        title="未找到投标任务"
        subTitle="任务不存在、已被归档删除，或你没有访问权限。"
        extra={onBack ? <Button type="primary" onClick={onBack}>回到工作台</Button> : undefined}
      />
    </div>
  )
}

export function BidTaskFailedBanner({
  message = '该任务处于失败状态，可重试解析或联系管理员。',
  onRetry,
}: {
  message?: string
  onRetry?: () => void
}) {
  return (
    <div
      className="mb-4 rounded-xl border border-[#FECACA] bg-[#FEF2F2] px-4 py-3 flex items-center justify-between gap-3"
      data-testid={BID_TEST_IDS.stateTaskFailed}
    >
      <div className="flex items-start gap-2 text-sm text-[#991B1B]">
        <AlertTriangle size={16} className="mt-0.5 flex-shrink-0" />
        <span>{message}</span>
      </div>
      {onRetry && (
        <Button size="small" danger onClick={onRetry}>
          重试
        </Button>
      )}
    </div>
  )
}
