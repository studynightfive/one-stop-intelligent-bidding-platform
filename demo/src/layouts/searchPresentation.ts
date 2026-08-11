import type { SearchResult } from '../api/platformApi'

const searchTypeLabels: Record<SearchResult['type'], string> = {
  page: '功能页面',
  bidTask: '投标任务',
  evaluation: '评标任务',
  qualification: '资质记录',
  fragment: '文档片段',
}

export function formatSearchResultSubtitle(result: Pick<SearchResult, 'type' | 'subtitle'>): string {
  const label = searchTypeLabels[result.type]
  return result.subtitle ? `${label} · ${result.subtitle}` : label
}
