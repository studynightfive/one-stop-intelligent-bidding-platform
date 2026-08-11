import { describe, expect, it } from 'vitest'
import { formatSearchResultSubtitle } from './searchPresentation'

describe('formatSearchResultSubtitle', () => {
  it('distinguishes bid and evaluation entries for the same project', () => {
    const subtitle = 'SZGYY-2026-0312 · 深圳市政务服务数据管理局'

    expect(formatSearchResultSubtitle({ type: 'bidTask', subtitle })).toBe(`投标任务 · ${subtitle}`)
    expect(formatSearchResultSubtitle({ type: 'evaluation', subtitle })).toBe(`评标任务 · ${subtitle}`)
  })

  it('uses the type label when an optional subtitle is absent', () => {
    expect(formatSearchResultSubtitle({ type: 'page' })).toBe('功能页面')
  })
})
