import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { BID_UI_QUERY_KEY, parseBidUiState, type BidUiState } from '../types'

type Options = {
  /** Brief loading before ready when no ui override. */
  bootstrapMs?: number
  /** Force empty when data length is 0 and status would be ready. */
  isEmpty?: boolean
}

/**
 * Resolves page UI state.
 * Override via URL `?ui=loading|error|forbidden|timeout|conflict|empty|not_found|ready` for M7 demos.
 */
export function useBidUiState(options: Options = {}) {
  const { bootstrapMs = 350, isEmpty = false } = options
  const [searchParams, setSearchParams] = useSearchParams()
  const override = parseBidUiState(searchParams.get(BID_UI_QUERY_KEY))
  const [bootstrapped, setBootstrapped] = useState(bootstrapMs <= 0)

  useEffect(() => {
    if (bootstrapMs <= 0 || override) {
      setBootstrapped(true)
      return
    }
    setBootstrapped(false)
    const timer = window.setTimeout(() => setBootstrapped(true), bootstrapMs)
    return () => window.clearTimeout(timer)
  }, [bootstrapMs, override])

  const status: BidUiState = useMemo(() => {
    if (override) return override
    if (!bootstrapped) return 'loading'
    if (isEmpty) return 'empty'
    return 'ready'
  }, [override, bootstrapped, isEmpty])

  const setUiOverride = (next: BidUiState | 'clear') => {
    const params = new URLSearchParams(searchParams)
    if (next === 'clear' || next === 'ready') params.delete(BID_UI_QUERY_KEY)
    else params.set(BID_UI_QUERY_KEY, next)
    setSearchParams(params, { replace: true })
  }

  const clearOverrideAndRetry = () => {
    setUiOverride('clear')
    setBootstrapped(false)
    window.setTimeout(() => setBootstrapped(true), bootstrapMs)
  }

  return {
    status,
    override,
    setUiOverride,
    retry: clearOverrideAndRetry,
  }
}
