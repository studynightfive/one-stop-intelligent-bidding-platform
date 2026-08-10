import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import './testEnvironment'
import { DemoProvider } from '../../../context/DemoContext'
import EvaluationDashboardView from '../views/EvaluationDashboardView'
import EvaluationCreateView from '../views/EvaluationCreateView'
import EvaluationTaskDetailView from '../views/EvaluationTaskDetailView'
import { evaluationRoutes } from '../routes'
import { evaluationNavigation } from '../navigation'
import { EVAL_TEST_IDS } from '../constants'
import { apiClient } from '../../../api/client'

vi.mock('../../../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
  },
}))

const sampleStats = {
  total: 2,
  collecting: 1,
  aiReview: 1,
  humanReview: 0,
  completed: 0,
  risk: 1,
}

const sampleTasks = [
  {
    id: 'EVAL-API-001',
    projectName: '接口评标项目',
    tenderNo: 'API-001',
    tenderEntity: '测试单位',
    budgetAmount: '1000000',
    currency: 'CNY',
    supplierDeadline: '2026-09-01T17:00:00',
    evaluationStartAt: '2026-09-02T09:00:00',
    evaluationEndAt: '2026-09-05T18:00:00',
    status: 'ai_review',
    currentStep: 4,
    progressPercent: 55,
    assignee: { id: 'u1', name: '刘德华' },
    supplierCount: 3,
    riskCount: 1,
    version: 1,
    createdAt: '2026-08-09T10:00:00',
    updatedAt: '2026-08-09T10:00:00',
  },
]

const sampleCreatedTask = { ...sampleTasks[0], id: 'EVAL-DRAFT-1' }

const sampleDetail = {
  ...sampleCreatedTask,
  version: 5,
  materials: [],
  scoringCriteria: [],
  reviewSettings: {
    multiRoundPricing: true,
    maxRounds: 2,
    supplementDeadlineMinutes: 120,
    allowModifyBeforeDeadline: false,
    notifyOnMissing: true,
    closeSubmissionAtDeadline: true,
  },
  reviewers: [],
  suppliers: [],
  latestJobs: [],
  allowedActions: [],
}

const samplePublishResult = {
  evaluation: { ...sampleCreatedTask, status: 'collecting' },
  invites: [{
    supplierId: 's1',
    supplierName: 'supplier-a',
    inviteCodeMasked: '****',
    inviteUrl: 'https://example.test/portal/INVITE-1',
    status: 'active',
    expiresAt: '2026-09-01T17:00:00',
  }],
}

function renderWithDemo(node: React.ReactNode) {
  return render(
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <DemoProvider>{node}</DemoProvider>
    </MemoryRouter>
  )
}

const getMock = vi.mocked(apiClient.get)
const postMock = vi.mocked(apiClient.post)
const putMock = vi.mocked(apiClient.put)
const patchMock = vi.mocked(apiClient.patch)

describe('M2 evaluation routes and navigation', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    getMock.mockReset()
    postMock.mockReset()
    putMock.mockReset()
    patchMock.mockReset()
    getMock.mockImplementation(async (path: string) => {
      if (path === '/evaluations/stats') return sampleStats
      if (path === '/evaluations') return sampleTasks
      if (path === '/evaluations/EVAL-DRAFT-1') return sampleDetail
      return []
    })
    postMock.mockImplementation(async (path: string) => {
      if (path === '/evaluations') return sampleCreatedTask
      if (path.includes('/publish')) return samplePublishResult
      return {}
    })
    putMock.mockResolvedValue([])
    patchMock.mockResolvedValue({ ...sampleCreatedTask, version: 2 })
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

  it('renders the evaluation dashboard from the M6 API with stable E2E selectors', async () => {
    renderWithDemo(<EvaluationDashboardView />)
    expect(screen.getByTestId(EVAL_TEST_IDS.dashboard)).toBeTruthy()
    await waitFor(() => {
      expect(screen.getByText('接口评标项目')).toBeTruthy()
      expect(getMock).toHaveBeenCalledWith('/evaluations/stats', expect.anything())
      expect(getMock).toHaveBeenCalledWith('/evaluations', expect.anything())
    })
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

  it('saves a new server draft through M6 APIs', async () => {
    localStorage.setItem(
      'bid-platform-access-token',
      `header.${btoa(JSON.stringify({ sub: 'u-1' }))}.signature`,
    )
    renderWithDemo(<EvaluationCreateView />)
    fireEvent.click(screen.getByText('填入示例'))
    fireEvent.click(screen.getByTestId(EVAL_TEST_IDS.createSaveDraft))
    await waitFor(() => {
      expect(postMock).toHaveBeenCalledWith('/evaluations', expect.anything())
      expect(putMock).toHaveBeenCalledWith('/evaluations/EVAL-DRAFT-1/materials', expect.anything())
      expect(putMock).toHaveBeenCalledWith('/evaluations/EVAL-DRAFT-1/criteria', expect.anything())
      expect(putMock).toHaveBeenCalledWith('/evaluations/EVAL-DRAFT-1/review-settings', expect.anything())
      expect(putMock).toHaveBeenCalledWith('/evaluations/EVAL-DRAFT-1/reviewers', expect.anything())
      expect(putMock).toHaveBeenCalledWith('/evaluations/EVAL-DRAFT-1/suppliers', expect.anything())
      expect(getMock).toHaveBeenCalledWith('/evaluations/EVAL-DRAFT-1')
    })
  })

  it('renders the evaluation task detail page', () => {
    renderWithDemo(<EvaluationTaskDetailView />)
    expect(screen.getByTestId(EVAL_TEST_IDS.taskDetail)).toBeTruthy()
    expect(screen.getByTestId(EVAL_TEST_IDS.taskBack)).toBeTruthy()
    expect(screen.getByTestId(EVAL_TEST_IDS.taskAiReview)).toBeTruthy()
    expect(screen.getByTestId(EVAL_TEST_IDS.taskClose)).toBeTruthy()
  })
})
