import { useCallback, useRef, useState } from 'react'
import { getBidApi } from '../adapters/getBidApi'
import type { FileRef, UploadProgress, UploadPurpose } from '../adapters/schemaTypes'

const idle: UploadProgress = { status: 'idle', percent: 0, uploadedParts: 0, totalParts: 0 }

export function useResumableUpload() {
  const [progress, setProgress] = useState<UploadProgress>(idle)
  const [fileRef, setFileRef] = useState<FileRef | null>(null)
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setProgress(idle)
    setFileRef(null)
    setError(null)
  }, [])

  const cancel = useCallback(async () => {
    abortRef.current?.abort()
    const uploadId = progress.uploadId
    if (uploadId) {
      try {
        await getBidApi().cancelUpload(uploadId)
      } catch {
        /* ignore */
      }
    }
    setProgress(prev => ({ ...prev, status: 'cancelled' }))
  }, [progress.uploadId])

  const upload = useCallback(async (file: File, purpose: UploadPurpose, resourceId?: string) => {
    setError(null)
    setFileRef(null)
    abortRef.current?.abort()
    const controller = new AbortController()
    abortRef.current = controller
    try {
      const ref = await getBidApi().uploadFile(file, purpose, {
        resourceId,
        signal: controller.signal,
        onProgress: setProgress,
      })
      setFileRef(ref)
      return ref
    } catch (err) {
      const message = err instanceof Error ? err.message : 'UPLOAD_FAILED'
      setError(message)
      setProgress(prev => ({ ...prev, status: message === 'UPLOAD_ABORTED' ? 'cancelled' : 'failed' }))
      throw err
    }
  }, [])

  return { progress, fileRef, error, upload, cancel, reset }
}
