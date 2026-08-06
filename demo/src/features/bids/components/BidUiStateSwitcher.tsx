import { Select } from 'antd'
import { BID_TEST_IDS } from '../constants'
import type { BidUiState } from '../types'

const OPTIONS: { value: BidUiState | 'clear'; label: string }[] = [
  { value: 'clear', label: '正常状态' },
  { value: 'loading', label: '加载中' },
  { value: 'empty', label: '空数据' },
  { value: 'error', label: '加载失败' },
  { value: 'forbidden', label: '无权限' },
  { value: 'timeout', label: '请求超时' },
  { value: 'conflict', label: '版本冲突' },
  { value: 'not_found', label: '未找到' },
]

/** Local demo switcher for exception states until real API errors exist. */
export function BidUiStateSwitcher({
  value,
  onChange,
}: {
  value: BidUiState | null
  onChange: (next: BidUiState | 'clear') => void
}) {
  return (
    <Select
      size="small"
      className="min-w-[140px]"
      data-testid={BID_TEST_IDS.uiStateSwitcher}
      value={value || 'clear'}
      onChange={onChange}
      options={OPTIONS}
      aria-label="切换投标页面异常态预览"
    />
  )
}
