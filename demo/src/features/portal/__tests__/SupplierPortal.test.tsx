import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import '../../evaluations/__tests__/testEnvironment'
import { DemoProvider } from '../../../context/DemoContext'
import SupplierPortalView from '../views/SupplierPortalView'
import { PORTAL_TEST_IDS } from '../constants'

describe('M2 supplier portal', () => {
  it('renders the active supplier submission portal with E2E selectors', () => {
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <DemoProvider>
          <SupplierPortalView />
        </DemoProvider>
      </MemoryRouter>
    )
    expect(screen.getByTestId(PORTAL_TEST_IDS.portal)).toBeTruthy()
    expect(screen.getByTestId(PORTAL_TEST_IDS.portalSaveDraft)).toBeTruthy()
    expect(screen.getByTestId(PORTAL_TEST_IDS.portalSubmit)).toBeTruthy()
  })
})
