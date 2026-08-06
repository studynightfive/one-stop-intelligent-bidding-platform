import dayjs, { type Dayjs } from 'dayjs'
import customParseFormat from 'dayjs/plugin/customParseFormat'

dayjs.extend(customParseFormat)

export type TenderFileExtract = {
  projectName?: string
  tenderNo?: string
  tenderEntity?: string
  deadline?: Dayjs
  budget?: number
}

const FIELD_ALIASES: Record<keyof TenderFileExtract, string[]> = {
  projectName: ['项目名称', '工程名称', 'projectName', 'project_name', 'name'],
  tenderNo: ['招标编号', '项目编号', '标段编号', 'tenderNo', 'tender_no', 'bidNo'],
  tenderEntity: ['招标方', '招标人', '采购人', '采购单位', 'tenderEntity', 'buyer'],
  deadline: ['投标截止时间', '截止时间', '递交截止时间', 'deadline', 'dueDate'],
  budget: ['预算金额', '预算', '金额', 'budget'],
}

function normalizeKey(raw: string) {
  return raw.trim().replace(/[:：=\s]+$/g, '').trim()
}

function parseDeadline(value: string): Dayjs | undefined {
  const trimmed = value.trim()
  const formats = ['YYYY-MM-DD HH:mm:ss', 'YYYY-MM-DD HH:mm', 'YYYY/MM/DD HH:mm', 'YYYY-MM-DD', 'YYYY/MM/DD']
  for (const format of formats) {
    const parsed = dayjs(trimmed, format, true)
    if (parsed.isValid()) return parsed
  }
  const loose = dayjs(trimmed)
  return loose.isValid() ? loose : undefined
}

function parseBudget(value: string): number | undefined {
  const normalized = value.replace(/[,，\s]/g, '').replace(/元|万元/g, match => (match === '万元' ? '0000' : ''))
  const amount = Number(normalized.replace(/[^\d.]/g, ''))
  return Number.isFinite(amount) && amount >= 0 ? amount : undefined
}

function matchField(key: string): keyof TenderFileExtract | null {
  const normalized = normalizeKey(key).toLowerCase()
  for (const [field, aliases] of Object.entries(FIELD_ALIASES) as Array<[keyof TenderFileExtract, string[]]>) {
    if (aliases.some(alias => alias.toLowerCase() === normalized)) return field
  }
  return null
}

function assignExtract(target: TenderFileExtract, field: keyof TenderFileExtract, raw: string) {
  const value = raw.trim()
  if (!value) return
  if (field === 'deadline') {
    const deadline = parseDeadline(value)
    if (deadline) target.deadline = deadline
    return
  }
  if (field === 'budget') {
    const budget = parseBudget(value)
    if (budget !== undefined) target.budget = budget
    return
  }
  target[field] = value
}

/** Parse only structured text/json content. Never invent missing fields. */
export function extractTenderFieldsFromText(content: string): TenderFileExtract {
  const result: TenderFileExtract = {}
  const trimmed = content.trim()
  if (!trimmed) return result

  if (trimmed.startsWith('{')) {
    try {
      const json = JSON.parse(trimmed) as Record<string, unknown>
      for (const [key, value] of Object.entries(json)) {
        const field = matchField(key)
        if (!field || value == null) continue
        assignExtract(result, field, String(value))
      }
      return result
    } catch {
      // fall through to line parser
    }
  }

  for (const line of trimmed.split(/\r?\n/)) {
    const matched = line.match(/^([^:：=]+)[:：=](.+)$/)
    if (!matched) continue
    const field = matchField(matched[1])
    if (!field) continue
    assignExtract(result, field, matched[2])
  }

  return result
}

function isTextLikeFile(file: File) {
  const lower = file.name.toLowerCase()
  return (
    lower.endsWith('.txt') ||
    lower.endsWith('.csv') ||
    lower.endsWith('.json') ||
    lower.endsWith('.md') ||
    file.type.startsWith('text/') ||
    file.type === 'application/json'
  )
}

/**
 * Extract tender form fields from file content only.
 * PDF/Word/binary formats are not parsed here (needs M5/M7) → returns {}.
 */
export async function extractTenderFieldsFromFile(file: File): Promise<TenderFileExtract> {
  if (!isTextLikeFile(file)) return {}
  try {
    const text = await file.text()
    return extractTenderFieldsFromText(text)
  } catch {
    return {}
  }
}

export function toFormValuesFromExtract(extract: TenderFileExtract) {
  return {
    projectName: extract.projectName ?? '',
    tenderNo: extract.tenderNo ?? '',
    tenderEntity: extract.tenderEntity ?? '',
    deadline: extract.deadline ?? null,
    budget: extract.budget ?? null,
  }
}
