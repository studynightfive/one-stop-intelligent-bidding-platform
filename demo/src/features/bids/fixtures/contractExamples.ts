/**
 * Contract-example fixtures for M1 component tests.
 * Shape mirrors OpenAPI BidTask fields used by the workbench.
 */
export const bidTaskContractExample = {
  id: 'TASK-EXAMPLE-001',
  projectName: '示例政务云采购项目',
  tenderNo: 'ZB-EXAMPLE-2026-001',
  tenderEntity: '示例政务服务数据管理局',
  deadline: '2026-12-31',
  status: 'material_prep' as const,
  currentStep: 3,
  progress: 42,
  assignee: '张明远',
  materialTotal: 23,
  materialHave: 13,
  materialMissing: 10,
  createdAt: '2026-08-01',
  tags: ['contract-example'],
}

export const bidTaskListContractExample = [
  bidTaskContractExample,
  {
    ...bidTaskContractExample,
    id: 'TASK-EXAMPLE-002',
    projectName: '临期风险示例项目',
    tenderNo: 'ZB-EXAMPLE-2026-002',
    deadline: '2026-08-10',
    status: 'ai_review' as const,
    currentStep: 6,
    progress: 78,
    materialMissing: 3,
    assignee: '李雪琴',
  },
  {
    ...bidTaskContractExample,
    id: 'TASK-EXAMPLE-003',
    projectName: '已归档示例项目',
    tenderNo: 'ZB-EXAMPLE-2026-003',
    status: 'archived' as const,
    currentStep: 7,
    progress: 100,
    materialMissing: 0,
  },
]
