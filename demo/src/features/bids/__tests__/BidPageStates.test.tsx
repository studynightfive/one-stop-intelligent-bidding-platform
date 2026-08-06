import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  BidConflictState,
  BidEmptyState,
  BidErrorState,
  BidForbiddenState,
  BidLoadingState,
  BidNotFoundState,
  BidTimeoutState,
  BidTaskFailedBanner,
} from '../components/BidPageStates'
import { BID_TEST_IDS } from '../constants'
import { parseBidUiState } from '../types'

describe('parseBidUiState', () => {
  it('accepts known states', () => {
    expect(parseBidUiState('loading')).toBe('loading')
    expect(parseBidUiState('forbidden')).toBe('forbidden')
    expect(parseBidUiState('conflict')).toBe('conflict')
  })

  it('rejects unknown values', () => {
    expect(parseBidUiState('nope')).toBeNull()
    expect(parseBidUiState(null)).toBeNull()
  })
})

describe('BidPageStates', () => {
  it('renders loading state', () => {
    render(<BidLoadingState tip="加载中" />)
    expect(screen.getByTestId(BID_TEST_IDS.stateLoading)).toBeTruthy()
    expect(screen.getByText('加载中')).toBeTruthy()
  })

  it('renders empty state with action', () => {
    const onAction = vi.fn()
    render(<BidEmptyState description="没有项目" actionLabel="清除筛选" onAction={onAction} />)
    expect(screen.getByTestId(BID_TEST_IDS.stateEmpty)).toBeTruthy()
    screen.getByRole('button', { name: '清除筛选' }).click()
    expect(onAction).toHaveBeenCalled()
  })

  it('renders error / forbidden / timeout / conflict / not found', () => {
    const { rerender } = render(<BidErrorState onRetry={() => undefined} />)
    expect(screen.getByTestId(BID_TEST_IDS.stateError)).toBeTruthy()

    rerender(<BidForbiddenState onBack={() => undefined} />)
    expect(screen.getByTestId(BID_TEST_IDS.stateForbidden)).toBeTruthy()

    rerender(<BidTimeoutState onRetry={() => undefined} />)
    expect(screen.getByTestId(BID_TEST_IDS.stateTimeout)).toBeTruthy()

    rerender(<BidConflictState onRetry={() => undefined} />)
    expect(screen.getByTestId(BID_TEST_IDS.stateConflict)).toBeTruthy()

    rerender(<BidNotFoundState onBack={() => undefined} />)
    expect(screen.getByTestId(BID_TEST_IDS.taskNotFound)).toBeTruthy()
  })

  it('renders task failed banner', () => {
    render(<BidTaskFailedBanner />)
    expect(screen.getByTestId(BID_TEST_IDS.stateTaskFailed)).toBeTruthy()
  })
})
