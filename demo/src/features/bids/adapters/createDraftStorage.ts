import type { BidCreateDraft } from '../types'
import { BID_CREATE_DRAFT_KEY } from '../constants'

export function loadBidCreateDraft(): BidCreateDraft | null {
  try {
    const raw = localStorage.getItem(BID_CREATE_DRAFT_KEY)
    return raw ? (JSON.parse(raw) as BidCreateDraft) : null
  } catch {
    return null
  }
}

export function saveBidCreateDraft(draft: Omit<BidCreateDraft, 'updatedAt'> & { updatedAt?: string }) {
  const payload: BidCreateDraft = {
    ...draft,
    updatedAt: draft.updatedAt || new Date().toISOString(),
  }
  localStorage.setItem(BID_CREATE_DRAFT_KEY, JSON.stringify(payload))
  return payload
}

export function clearBidCreateDraft() {
  localStorage.removeItem(BID_CREATE_DRAFT_KEY)
}
