import { describe, expect, it } from 'vitest'
import {
  extractTenderFieldsFromText,
  toFormValuesFromExtract,
} from '../hooks/extractTenderFields'

describe('extractTenderFieldsFromText', () => {
  it('extracts labeled text fields and leaves others empty', () => {
    const extract = extractTenderFieldsFromText(`项目名称: 市政道路改造工程
招标编号：ZB-2026-088
招标方=某市住建局
投标截止时间: 2026-09-01 17:00
`)
    expect(extract.projectName).toBe('市政道路改造工程')
    expect(extract.tenderNo).toBe('ZB-2026-088')
    expect(extract.tenderEntity).toBe('某市住建局')
    expect(extract.deadline?.format('YYYY-MM-DD HH:mm')).toBe('2026-09-01 17:00')
    expect(extract.budget).toBeUndefined()
  })

  it('extracts from json without inventing missing keys', () => {
    const extract = extractTenderFieldsFromText(JSON.stringify({
      projectName: '云平台采购',
      tenderNo: 'CLOUD-1',
    }))
    expect(extract.projectName).toBe('云平台采购')
    expect(extract.tenderNo).toBe('CLOUD-1')
    expect(extract.tenderEntity).toBeUndefined()
    expect(toFormValuesFromExtract(extract)).toEqual({
      projectName: '云平台采购',
      tenderNo: 'CLOUD-1',
      tenderEntity: '',
      deadline: null,
      budget: null,
    })
  })

  it('returns empty object for free text without structured fields', () => {
    expect(extractTenderFieldsFromText('这是一份没有结构化字段的说明')).toEqual({})
  })
})
