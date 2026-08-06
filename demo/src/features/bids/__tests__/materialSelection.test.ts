import { describe, expect, it } from 'vitest'
import {
  isAllVisibleSelected,
  resolveSelectedMaterialIds,
  toggleAllVisibleSelection,
  toggleIdInSelection,
} from '../hooks/materialSelection'

describe('materialSelection', () => {
  it('keeps only available selected ids', () => {
    expect(resolveSelectedMaterialIds(['a', 'b', 'c'], ['a', 'c'])).toEqual(['a', 'c'])
  })

  it('toggles one id', () => {
    expect(toggleIdInSelection(['a'], 'b', true)).toEqual(['a', 'b'])
    expect(toggleIdInSelection(['a', 'b'], 'a', false)).toEqual(['b'])
  })

  it('selects and clears all visible ids', () => {
    expect(toggleAllVisibleSelection(['x'], ['a', 'b'], true)).toEqual(['x', 'a', 'b'])
    expect(toggleAllVisibleSelection(['a', 'b', 'x'], ['a', 'b'], false)).toEqual(['x'])
  })

  it('detects all-visible selected', () => {
    expect(isAllVisibleSelected(['a', 'b'], ['a', 'b'])).toBe(true)
    expect(isAllVisibleSelected(['a'], ['a', 'b'])).toBe(false)
    expect(isAllVisibleSelected([], [])).toBe(false)
  })
})
