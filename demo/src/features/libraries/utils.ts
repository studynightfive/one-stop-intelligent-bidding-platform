import dayjs, { type Dayjs } from 'dayjs'
import type { FragmentRecord, LibraryVersion, QualificationStatus } from './types'

export function qualificationRemainingDays(expiryDate: string, now: Dayjs = dayjs()) {
  if (!expiryDate || expiryDate === '-') return null
  return dayjs(expiryDate).startOf('day').diff(now.startOf('day'), 'day')
}

export function deriveQualificationStatus(expiryDate: string, warningDays = 60, now: Dayjs = dayjs()): QualificationStatus {
  const remaining = qualificationRemainingDays(expiryDate, now)
  if (remaining === null) return 'permanent'
  if (remaining < 0) return 'expired'
  if (remaining <= warningDays) return 'expiring'
  return 'valid'
}

function normalizeText(value: string) {
  return value.trim().toLowerCase().replace(/[\s，。；、：:,.!?（）()\-_]/g, '')
}

function textTokens(value: string) {
  const normalized = normalizeText(value)
  const chars = Array.from(normalized)
  const tokens = new Set(chars)
  for (let index = 0; index < chars.length - 1; index += 1) tokens.add(`${chars[index]}${chars[index + 1]}`)
  return tokens
}

export function rankFragmentsSemantic(fragments: FragmentRecord[], query: string) {
  const normalizedQuery = normalizeText(query)
  if (!normalizedQuery) return fragments.map(fragment => ({ ...fragment, matchScore: undefined, matchReason: undefined }))
  const queryTokens = textTokens(query)

  return fragments
    .map(fragment => {
      const title = normalizeText(fragment.title)
      const tags = fragment.tags.map(normalizeText)
      const corpus = `${fragment.title}${fragment.preview}${fragment.content || ''}${fragment.tags.join('')}`
      const corpusTokens = textTokens(corpus)
      const overlap = [...queryTokens].filter(token => corpusTokens.has(token)).length
      const overlapRatio = overlap / Math.max(queryTokens.size, 1)
      const titleBoost = title.includes(normalizedQuery) || normalizedQuery.includes(title) ? 0.32 : 0
      const tagBoost = tags.some(tag => tag && (normalizedQuery.includes(tag) || tag.includes(normalizedQuery))) ? 0.2 : 0
      const score = Math.min(99, Math.max(42, Math.round((overlapRatio + titleBoost + tagBoost) * 100)))
      const matchedTags = fragment.tags.filter(tag => {
        const normalizedTag = normalizeText(tag)
        return normalizedTag && (normalizedQuery.includes(normalizedTag) || normalizedTag.includes(normalizedQuery))
      }).slice(0, 3)
      const reason = matchedTags.length
        ? `命中 ${matchedTags.join('、')} 等主题，内容与检索需求相关`
        : `标题与正文语义存在 ${Math.round(overlapRatio * 100)}% 的关键词关联`
      return { ...fragment, matchScore: score, matchReason: reason }
    })
    .sort((left, right) => (right.matchScore || 0) - (left.matchScore || 0))
}

export function nextDocumentVersion(currentVersion?: string) {
  const match = currentVersion?.match(/v?(\d+)(?:\.(\d+))?/i)
  if (!match) return 'v1.0'
  return `v${Number(match[1]) + 1}.0`
}

export function appendLibraryVersion(
  versions: LibraryVersion[] | undefined,
  version: Omit<LibraryVersion, 'createdAt' | 'createdBy'> & Partial<Pick<LibraryVersion, 'createdAt' | 'createdBy'>>,
) {
  return [
    {
      ...version,
      createdAt: version.createdAt || new Date().toLocaleString('zh-CN', { hour12: false }),
      createdBy: version.createdBy || '张明远',
    },
    ...(versions || []),
  ]
}

export function paginate<T>(items: T[], page: number, pageSize: number) {
  const safePageSize = Math.max(1, pageSize)
  const totalPages = Math.max(1, Math.ceil(items.length / safePageSize))
  const safePage = Math.min(Math.max(1, page), totalPages)
  return {
    items: items.slice((safePage - 1) * safePageSize, safePage * safePageSize),
    page: safePage,
    pageSize: safePageSize,
    total: items.length,
    totalPages,
  }
}
