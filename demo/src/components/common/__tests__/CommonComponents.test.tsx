import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { EmptyState, ErrorState, FilterBar, JobProgress, LoadingState, PermissionGate } from '..'
import { ApiError } from '../../../api/interceptors'

describe('common page states', () => {
  it('renders accessible loading and empty states', () => {
    const { rerender } = render(<LoadingState label="正在获取用户" />)
    expect(screen.getByLabelText('正在获取用户').getAttribute('aria-busy')).toBe('true')
    rerender(<EmptyState title="暂无用户" description="发送邀请后会显示在这里" />)
    expect(screen.getByText('暂无用户')).toBeTruthy()
  })

  it('shows mapped errors and retries', () => {
    const retry = vi.fn()
    render(<ErrorState error={new ApiError({ message: '服务失败', requestId: 'REQ-1' })} onRetry={retry} />)
    expect(screen.getByText('服务失败')).toBeTruthy()
    expect(screen.getByText(/REQ-1/)).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: '重新加载' }))
    expect(retry).toHaveBeenCalledOnce()
  })
})

describe('shared interaction components', () => {
  it('gates protected actions by permission', () => {
    const { rerender } = render(<PermissionGate permissions={['library:read']} require="library:write" fallback={<span>无权限</span>}><button>删除</button></PermissionGate>)
    expect(screen.getByText('无权限')).toBeTruthy()
    rerender(<PermissionGate permissions={['library:write']} require="library:write"><button>删除</button></PermissionGate>)
    expect(screen.getByRole('button', { name: '删除' })).toBeTruthy()
  })

  it('renders job progress and filter reset', () => {
    const reset = vi.fn()
    const { rerender } = render(<JobProgress title="导入文件" status="running" progress={45} />)
    expect(screen.getByText('导入文件')).toBeTruthy()
    rerender(<FilterBar resultCount={3} onReset={reset}><span>筛选项</span></FilterBar>)
    fireEvent.click(screen.getByRole('button', { name: /重置/ }))
    expect(reset).toHaveBeenCalledOnce()
  })
})
