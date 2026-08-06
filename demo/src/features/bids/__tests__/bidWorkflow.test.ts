import { describe, expect, it } from 'vitest'
import { buildBidWorkflowPatch, nextBidStep, normalizeBidStep, prevBidStep } from '../hooks/bidWorkflow'

describe('bidWorkflow', () => {
  it('builds patch for material and review steps', () => {
    expect(buildBidWorkflowPatch(3)).toMatchObject({ currentStep: 3, status: 'material_prep', progress: 43 })
    expect(buildBidWorkflowPatch(6)).toMatchObject({ currentStep: 6, status: 'ai_review' })
    expect(buildBidWorkflowPatch(7, 50)).toMatchObject({ currentStep: 7, status: 'pending_output', progress: 92 })
  })

  it('recalculates progress when stepping backward', () => {
    expect(buildBidWorkflowPatch(4, 92)).toMatchObject({ currentStep: 4, progress: 57 })
  })

  it('normalizes string steps and clamps next/prev', () => {
    expect(normalizeBidStep('5')).toBe(5)
    expect(nextBidStep(7)).toBe(7)
    expect(prevBidStep(1)).toBe(1)
    expect(prevBidStep('3')).toBe(2)
    expect(nextBidStep(3)).toBe(4)
  })
})
