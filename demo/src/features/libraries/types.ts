export type QualificationStatus = 'valid' | 'expiring' | 'expired' | 'permanent'

export interface LibraryVersion {
  version: string
  fileName?: string
  changeNote: string
  createdAt: string
  createdBy: string
}

export interface QualificationRecord {
  id: string
  name: string
  category: string
  certNumber: string
  expiryDate: string
  status?: QualificationStatus
  fileName: string
  issuer?: string
  source?: string
  version?: string
  versions?: LibraryVersion[]
  createdAt?: string
  updatedAt?: string
}

export interface FragmentReference {
  id: string
  projectName: string
  materialName?: string
  referencedAt: string
  referencedBy: string
}

export interface FragmentRecord {
  id: string
  title: string
  category: string
  preview: string
  content?: string
  tags: string[]
  useCount: number
  updatedAt: string
  fileName?: string
  source?: string
  version?: string
  versions?: LibraryVersion[]
  references?: FragmentReference[]
  matchScore?: number
  matchReason?: string
}
