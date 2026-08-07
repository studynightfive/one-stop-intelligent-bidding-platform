import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import './testEnvironment'
import { DemoProvider } from '../../../context/DemoContext'
import EvaluationDashboardView from '../views/EvaluationDashboardView'
import EvaluationCreateView from '../views/EvaluationCreateView'
import EvaluationTaskDetailView from '../views/EvaluationTaskDetailView'
import { evaluationRoutes } from '../routes'
import { evaluationNavigation } from '../navigation'
import { EVAL_TEST_IDS } from '../constants'

function renderWithDemo(node: React.ReactNode) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <DemoProvider>{node}</DemoProvider>
    </MemoryRouter>
  )
}

describe('M2 evaluation routes and navigation', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  it('exposes the evaluation route table consumed by the M3 bridge', () => {
    expect(evaluationRoutes.map(route => route.path)).toEqual([
      'evaluation',
      'evaluation/create',
      'evaluation/portal',
      'evaluation/:id',
    ])
  })

  it('exposes M2 owned sidebar navigation', () => {
    expect(evaluationNavigation.map(item => item.key)).toEqual([
      '/evaluation',
      '/evaluation/create',
      '/evaluation/portal/EVAL-2026-001',
    ])
    expect(evaluationNavigation.every(item => item.owner === 'M2' && item.section === 'main')).toBe(true)
  })

  it('renders the evaluation dashboard with stable E2E selectors', () => {
    renderWithDemo(<EvaluationDashboardView />)
    expect(screen.getByTestId(EVAL_TEST_IDS.dashboard)).toBeTruthy()
    expect(screen.getByTestId(EVAL_TEST_IDS.dashboardCreate)).toBeTruthy()
    expect(screen.getByTestId(EVAL_TEST_IDS.dashboardPortal)).toBeTruthy()
    expect(screen.getByTestId(EVAL_TEST_IDS.dashboardReset)).toBeTruthy()
  })

  it('renders the evaluation create flow', () => {
    renderWithDemo(<EvaluationCreateView />)
    expect(screen.getByTestId(EVAL_TEST_IDS.create)).toBeTruthy()
    expect(screen.getByTestId(EVAL_TEST_IDS.createSaveDraft)).toBeTruthy()
    expect(screen.getByTestId(EVAL_TEST_IDS.createPreview)).toBeTruthy()
    expect(screen.getByTestId(EVAL_TEST_IDS.createCancel)).toBeTruthy()
  })

  it('renders the evaluation task detail page', () => {
    renderWithDemo(<EvaluationTaskDetailView />)
    expect(screen.getByTestId(EVAL_TEST_IDS.taskDetail)).toBeTruthy()
    expect(screen.getByTestId(EVAL_TEST_IDS.taskBack)).toBeTruthy()
    expect(screen.getByTestId(EVAL_TEST_IDS.taskAiReview)).toBeTruthy()
    expect(screen.getByTestId(EVAL_TEST_IDS.taskClose)).toBeTruthy()
  })
})
