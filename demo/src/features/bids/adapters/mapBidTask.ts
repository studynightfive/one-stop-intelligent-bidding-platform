import type { components } from '../../../api/generated/schema'
import type { BidTaskViewModel } from '../types'

type BidTask = components['schemas']['BidTask']

/** Map OpenAPI BidTask → M1 list/detail view model. */
export function mapBidTaskToViewModel(task: BidTask): BidTaskViewModel {
  const deadline = typeof task.deadline === 'string' ? task.deadline.slice(0, 10) : String(task.deadline)
  return {
    id: task.id,
    projectName: task.projectName,
    tenderNo: task.tenderNo,
    tenderEntity: task.tenderEntity,
    deadline,
    status: task.status,
    currentStep: task.currentStep,
    progress: task.progressPercent,
    assignee: task.assignee?.name || '',
    assigneeId: task.assignee?.id,
    materialTotal: task.materialSummary?.total ?? 0,
    materialHave: task.materialSummary?.have ?? 0,
    materialMissing: task.materialSummary?.missing ?? 0,
    linkedEvaluationId: task.linkedEvaluationId,
    version: task.version,
    createdAt: task.createdAt,
    tags: task.tags,
  }
}
