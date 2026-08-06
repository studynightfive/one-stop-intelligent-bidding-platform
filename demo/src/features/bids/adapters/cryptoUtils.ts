/** Demo SHA-256; browsers use SubtleCrypto, Node/jsdom use a stable fallback. */
export async function sha256Hex(file: Blob): Promise<string> {
  const canDigest =
    typeof crypto !== 'undefined' &&
    !!crypto.subtle &&
    typeof (file as Blob).arrayBuffer === 'function'

  if (canDigest) {
    try {
      const buffer = await file.arrayBuffer()
      const digest = await crypto.subtle.digest('SHA-256', buffer)
      return Array.from(new Uint8Array(digest))
        .map(b => b.toString(16).padStart(2, '0'))
        .join('')
    } catch {
      /* fall through */
    }
  }

  // Deterministic fallback for vitest / non-secure contexts
  const size = file.size
  const name = (file as File).name || 'blob'
  let hash = 0
  const seed = `${name}:${size}`
  for (let i = 0; i < seed.length; i += 1) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0
  return `demo${hash.toString(16).padStart(56, '0')}`.slice(0, 64)
}

export function newIdempotencyKey(prefix = 'bid'): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}
