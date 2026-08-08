export type EvaluationTaskStatus =
  | 'collecting'
  | 'ai_review'
  | 'human_review'
  | 'completed'
  | 'closed'

export type EvaluationFilterTab = EvaluationTaskStatus | 'all' | 'risk'

export type EvaluationTaskSummary = {
  id: string
  projectName: string
  tenderNo: string
  tenderEntity: string
  status: EvaluationTaskStatus
  assignee: string
  deadline: string
  bidderCount: number
  progress: number
  budget: string
}

export type PortalMode = 'active' | 'closed'
