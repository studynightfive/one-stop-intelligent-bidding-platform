export type EvaluationTaskStatus =
  | 'draft'
  | 'collecting'
  | 'pending'
  | 'ai_review'
  | 'human_review'
  | 'completed'
  | 'closed'
  | 'cancelled'

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
  riskCount: number
}

export type PortalMode = 'active' | 'closed'
