import { beforeEach, describe, expect, it } from 'vitest'
import {
  clearBidCreateDraft,
  loadBidCreateDraft,
  saveBidCreateDraft,
} from '../adapters/createDraftStorage'
import { BID_CREATE_DRAFT_KEY } from '../constants'

describe('createDraftStorage', () => {
  beforeEach(() => {
    localStorage.removeItem(BID_CREATE_DRAFT_KEY)
  })

  it('saves and loads a create draft', () => {
    saveBidCreateDraft({
      projectName: '草稿项目',
      tenderNo: 'DRAFT-001',
      tenderEntity: '测试单位',
      fileName: 'tender.pdf',
      fileSize: 1024,
    })
    const draft = loadBidCreateDraft()
    expect(draft?.projectName).toBe('草稿项目')
    expect(draft?.tenderNo).toBe('DRAFT-001')
    expect(draft?.fileName).toBe('tender.pdf')
    expect(draft?.updatedAt).toBeTruthy()
  })

  it('clears draft storage', () => {
    saveBidCreateDraft({ projectName: '临时' })
    clearBidCreateDraft()
    expect(loadBidCreateDraft()).toBeNull()
  })
})
