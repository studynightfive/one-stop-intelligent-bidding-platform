import type { JobRef } from './schemaTypes'
import { getBidApi } from './getBidApi'

const TERMINAL_JOB_STATUSES = new Set<JobRef['status']>(['succeeded', 'failed', 'cancelled'])

function failureMessage(job: JobRef): string {
  return job.error?.message || (job.status === 'cancelled' ? '任务已取消' : '任务执行失败')
}

export async function waitForBidJob(
  initial: JobRef,
  options: {
    timeoutMs?: number
    intervalMs?: number
    onChange?: (job: JobRef) => void
  } = {},
): Promise<JobRef> {
  const timeoutMs = options.timeoutMs ?? 15 * 60 * 1000
  const intervalMs = options.intervalMs ?? 1000
  const deadline = Date.now() + timeoutMs
  let current = initial
  options.onChange?.(current)

  while (!TERMINAL_JOB_STATUSES.has(current.status) && Date.now() < deadline) {
    await new Promise(resolve => window.setTimeout(resolve, intervalMs))
    current = await getBidApi().getJob(current.id)
    options.onChange?.(current)
  }

  if (!TERMINAL_JOB_STATUSES.has(current.status)) {
    throw new Error('任务等待超时，请稍后在任务详情中查看')
  }
  if (current.status !== 'succeeded') throw new Error(failureMessage(current))
  return current
}
