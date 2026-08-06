/** Demo helpers for M1 bid task seven-step progress. */

export type BidWorkflowPatch = {
  currentStep: number
  status: string
  progress: number
}

const STEP_STATUS: Record<number, string> = {
  1: 'parsing',
  2: 'parsing',
  3: 'material_prep',
  4: 'material_prep',
  5: 'material_prep',
  6: 'ai_review',
  7: 'pending_output',
}

export const BID_STEP_GUIDE: Record<number, { tip: string; nextLabel: string; prevLabel: string; tab: string }> = {
  1: { tip: '上传招标文件后继续解析。', nextLabel: '下一步：AI拆解需求', prevLabel: '上一步', tab: 'materials' },
  2: { tip: '确认 AI 拆解结果后进入材料清单。', nextLabel: '下一步：材料清单', prevLabel: '上一步：上传招标文件', tab: 'materials' },
  3: { tip: '请在下方「材料清单」核对条目，确认后进入下载模板。', nextLabel: '下一步：下载模板', prevLabel: '上一步：AI拆解需求', tab: 'materials' },
  4: { tip: '在材料清单里点击「下载模板」，准备好后进入批量上传。', nextLabel: '下一步：批量上传', prevLabel: '上一步：材料清单', tab: 'materials' },
  5: { tip: '用下方拖拽区或行内上传补齐缺失材料，然后进入 AI 审核。', nextLabel: '下一步：AI审核', prevLabel: '上一步：下载模板', tab: 'materials' },
  6: { tip: '查看审核结果并处理建议，完成后进入文档输出。', nextLabel: '下一步：输出文档', prevLabel: '上一步：批量上传', tab: 'review' },
  7: { tip: '可在「文档输出」生成并下载投标文件，或使用右上角导出。', nextLabel: '', prevLabel: '上一步：AI审核', tab: 'output' },
}

export function normalizeBidStep(value: unknown): number {
  const n = Number(value)
  if (!Number.isFinite(n)) return 1
  return Math.min(7, Math.max(1, Math.trunc(n)))
}

export function buildBidWorkflowPatch(currentStep: number | string, _progress = 0): BidWorkflowPatch {
  const step = normalizeBidStep(currentStep)
  const baseProgress = step === 7 ? 92 : Math.round((step / 7) * 100)
  return {
    currentStep: step,
    status: STEP_STATUS[step] || 'material_prep',
    // 前进/回退都按步骤重算进度，避免回退后进度条与步骤不一致、看起来像“没反应”
    progress: baseProgress,
  }
}

export function nextBidStep(currentStep: number | string) {
  return Math.min(7, normalizeBidStep(currentStep) + 1)
}

export function prevBidStep(currentStep: number | string) {
  return Math.max(1, normalizeBidStep(currentStep) - 1)
}
