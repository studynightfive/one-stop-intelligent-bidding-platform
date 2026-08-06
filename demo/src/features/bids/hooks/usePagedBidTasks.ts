import { useCallback, useEffect, useState } from 'react'
import type { BidTaskViewModel } from '../types'
import { getBidApi } from '../adapters/getBidApi'
import type { ListBidTasksQuery, PaginationMeta } from '../adapters/schemaTypes'

const emptyMeta: PaginationMeta = { page: 1, pageSize: 20, total: 0, totalPages: 1 }

export function usePagedBidTasks(query: ListBidTasksQuery, depsKey: string) {
  const [data, setData] = useState<BidTaskViewModel[]>([])
  const [meta, setMeta] = useState<PaginationMeta>(emptyMeta)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getBidApi().listBidTasks(query)
      setData(result.data)
      setMeta(result.meta)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'LIST_FAILED')
      setData([])
      setMeta(emptyMeta)
    } finally {
      setLoading(false)
    }
  }, [depsKey]) // eslint-disable-line react-hooks/exhaustive-deps -- depsKey encodes query

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [reload])

  return { data, meta, loading, error, reload }
}
