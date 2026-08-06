/** Pure helpers for materials batch actions (M1). */

export function resolveSelectedMaterialIds(selectedIds: string[], availableIds: string[]) {
  const available = new Set(availableIds)
  return selectedIds.filter(id => available.has(id))
}

export function toggleIdInSelection(selectedIds: string[], id: string, checked: boolean) {
  if (checked) return selectedIds.includes(id) ? selectedIds : [...selectedIds, id]
  return selectedIds.filter(item => item !== id)
}

export function toggleAllVisibleSelection(selectedIds: string[], visibleIds: string[], checked: boolean) {
  if (checked) {
    const set = new Set([...selectedIds, ...visibleIds])
    return Array.from(set)
  }
  const drop = new Set(visibleIds)
  return selectedIds.filter(id => !drop.has(id))
}

export function isAllVisibleSelected(selectedIds: string[], visibleIds: string[]) {
  if (visibleIds.length === 0) return false
  const set = new Set(selectedIds)
  return visibleIds.every(id => set.has(id))
}
