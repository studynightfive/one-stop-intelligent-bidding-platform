import { describe, expect, it } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { render, screen, waitFor } from '@testing-library/react'
import { useBidUiState } from '../hooks/useBidUiState'
import { BID_TEST_IDS } from '../constants'
import { BidLoadingState, BidErrorState } from '../components/BidPageStates'

function Probe() {
  const { status } = useBidUiState({ bootstrapMs: 50 })
  if (status === 'loading') return <BidLoadingState />
  if (status === 'error') return <BidErrorState />
  return <div data-testid="ready-probe">ready</div>
}

describe('useBidUiState', () => {
  it('bootstraps from loading to ready', async () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/dashboard" element={<Probe />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByTestId(BID_TEST_IDS.stateLoading)).toBeTruthy()
    await waitFor(() => expect(screen.getByTestId('ready-probe')).toBeTruthy())
  })

  it('honors ui query override', () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }} initialEntries={['/dashboard?ui=error']}>
        <Routes>
          <Route path="/dashboard" element={<Probe />} />
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByTestId(BID_TEST_IDS.stateError)).toBeTruthy()
  })
})
