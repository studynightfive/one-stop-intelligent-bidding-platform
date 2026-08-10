import type { ReactNode } from 'react'
import { Button } from 'antd'
import { RotateCcw } from 'lucide-react'

export function FilterBar({ children, onReset, resultCount }: { children: ReactNode; onReset?: () => void; resultCount?: number }) {
  return (
    <section aria-label="筛选条件" className="mb-4 rounded-xl border border-[#E2E8F0] bg-white p-3">
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex flex-1 flex-wrap items-center gap-2">{children}</div>
        <div className="flex items-center gap-3">
          {resultCount !== undefined && <span className="text-xs text-[#64748B]">共 {resultCount} 条结果</span>}
          {onReset && <Button size="small" icon={<RotateCcw size={13} />} onClick={onReset}>重置</Button>}
        </div>
      </div>
    </section>
  )
}
