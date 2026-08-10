import { describe, expect, it } from 'vitest'
import {
  createDefaultTechnicalDocument,
  normalizeTechnicalDocument,
  validateTechnicalDocument,
} from '../adapters/technicalDocumentConfig'

describe('technical document configuration', () => {
  it('provides a valid paragraph-by-paragraph default format', () => {
    const draft = createDefaultTechnicalDocument()
    expect(draft.strategy).toBe('paragraph_by_paragraph')
    expect(draft.sections.length).toBeGreaterThanOrEqual(4)
    expect(validateTechnicalDocument(draft)).toEqual([])
  })

  it('validates image paragraph anchors and removes stale anchors', () => {
    const draft = createDefaultTechnicalDocument()
    draft.referenceImages = [{
      fileId: 'FILE-1',
      sectionKey: draft.sections[0].key,
      caption: ' 总体架构图 ',
      placement: 'after_paragraph',
      afterParagraphIndex: 99,
    }]
    expect(validateTechnicalDocument(draft)).toContain('第 1 张图片的段落锚点超出章节范围')

    draft.referenceImages[0].placement = 'after_section'
    const normalized = normalizeTechnicalDocument(draft)
    expect(normalized.referenceImages[0].caption).toBe('总体架构图')
    expect(normalized.referenceImages[0].afterParagraphIndex).toBeUndefined()
  })
})
