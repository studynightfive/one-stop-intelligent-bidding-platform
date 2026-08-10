import { describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import '../../evaluations/__tests__/testEnvironment'
import { DemoProvider } from '../../../context/DemoContext'
import SupplierPortalView from '../views/SupplierPortalView'
import { PORTAL_TEST_IDS } from '../constants'
import { vi } from 'vitest'

vi.mock('../evaluations/api', () => ({
  fetchPortalContext: vi.fn().mockRejectedValue(new Error('no backend')),
  fetchPortalMaterials: vi.fn().mockRejectedValue(new Error('no backend')),
  fetchPortalPriceRounds: vi.fn().mockRejectedValue(new Error('no backend')),
  fetchPortalNotices: vi.fn().mockRejectedValue(new Error('no backend')),
  fetchPortalActivity: vi.fn().mockRejectedValue(new Error('no backend')),
}))

describe('M2 supplier portal', () => {
  it('renders the active supplier submission portal with E2E selectors', async () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <DemoProvider>
          <SupplierPortalView />
        </DemoProvider>
      </MemoryRouter>
    )
    await waitFor(() => {
      expect(screen.getByTestId(PORTAL_TEST_IDS.portal)).toBeTruthy()
    })
    expect(screen.getByTestId(PORTAL_TEST_IDS.portalSaveDraft)).toBeTruthy()
    expect(screen.getByTestId(PORTAL_TEST_IDS.portalSubmit)).toBeTruthy()
  })
})
