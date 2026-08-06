import { useCallback, useEffect, useState } from 'react'
import { Button, Modal, Tag, message } from 'antd'
import { Download as DownloadIcon, FileCheck2, FileOutput, FileText, History } from 'lucide-react'
import { getBidApi } from '../adapters/getBidApi'
import { newIdempotencyKey } from '../adapters/cryptoUtils'
import type { DocumentVersion } from '../adapters/schemaTypes'
import { BID_TEST_IDS } from '../constants'

function downloadBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = fileName
  anchor.click()
  URL.revokeObjectURL(url)
}

export function BidDocumentOutputTab({ taskId, projectName }: { taskId: string; projectName: string }) {
  const [generating, setGenerating] = useState(false)
  const [versions, setVersions] = useState<DocumentVersion[]>([])
  const [loading, setLoading] = useState(false)

  const reload = useCallback(async () => {
    setLoading(true)
    try {
      const page = await getBidApi().listDocumentVersions(taskId, { page: 1, pageSize: 50, sortOrder: 'desc' })
      setVersions(page.data)
    } catch {
      message.error('加载文档版本失败')
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void reload()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [reload])

  const latestId = versions[0]?.id

  const generateDocuments = async () => {
    setGenerating(true)
    try {
      const job = await getBidApi().generateDocuments(
        taskId,
        {
          mode: 'split',
          sections: ['qualification', 'commercial', 'technical'],
          templateMode: 'tender_requirement',
          includeWatermark: false,
        },
        newIdempotencyKey('gen'),
      )
      await reload()
      const versionNumber = (job.result as { versionNumber?: number } | undefined)?.versionNumber
      message.success(versionNumber ? `已生成 v${versionNumber}.0（Job ${job.id}）` : `生成任务完成（Job ${job.id}）`)
    } catch {
      message.error('文档生成失败')
    } finally {
      setGenerating(false)
    }
  }

  const downloadLatest = async () => {
    if (!versions[0]) {
      message.warning('暂无版本可下载')
      return
    }
    const blob = await getBidApi().downloadDocumentBlob(taskId, versions[0].id)
    downloadBlob(blob, versions[0].file.fileName || `${projectName}-投标文件.docx`)
  }

  const compareWithLatest = async (version: DocumentVersion) => {
    if (!latestId || version.id === latestId) {
      message.info('请选择非最新版本进行对比')
      return
    }
    try {
      const diff = await getBidApi().compareDocumentVersions(taskId, version.id, latestId)
      Modal.info({
        title: `版本对比 v${diff.from.versionNumber} → v${diff.to.versionNumber}`,
        width: 640,
        content: (
          <div className="space-y-2 mt-3 max-h-[420px] overflow-y-auto">
            {diff.changes.map((change, index) => (
              <div key={`${change.section}-${index}`} className="rounded-lg border border-[#E2E8F0] p-3 text-xs">
                <div className="font-medium text-[#1E293B] mb-1">
                  {change.section}
                  <Tag className="ml-2 !text-[10px]" color={change.type === 'added' ? 'green' : change.type === 'removed' ? 'red' : 'blue'}>
                    {change.type}
                  </Tag>
                </div>
                {change.before && <div className="text-[#94A3B8]">前：{change.before}</div>}
                {change.after && <div className="text-[#334155]">后：{change.after}</div>}
              </div>
            ))}
          </div>
        ),
      })
    } catch {
      message.error('版本对比失败')
    }
  }

  const rollback = (version: DocumentVersion) => {
    Modal.confirm({
      title: `回滚到 v${version.versionNumber}.0？`,
      content: '将基于所选版本创建新版本（OpenAPI rollback → Job）。演示可用 ?forceConflict=1 模拟冲突。',
      okText: '确认回滚',
      onOk: async () => {
        try {
          await getBidApi().rollbackDocumentVersion(taskId, version.id, `回滚到 v${version.versionNumber}`, newIdempotencyKey('rollback'))
          await reload()
          message.success(`已回滚并生成新版本（基于 v${version.versionNumber}）`)
        } catch (err) {
          const code = (err as { code?: string; message?: string })?.code || (err as Error)?.message
          if (code === 'VERSION_CONFLICT') {
            message.error('版本冲突：回滚失败，请刷新后重试')
            return Promise.reject(err)
          }
          message.error('回滚失败')
          return Promise.reject(err)
        }
      },
    })
  }

  const docTypes = [
    { type: 'qualification', name: '资质标', icon: FileCheck2, color: '#2563EB', bg: '#EFF6FF', pages: 45 },
    { type: 'commercial', name: '商务标', icon: FileText, color: '#D97706', bg: '#FFFBEB', pages: 12 },
    { type: 'technical', name: '技术标', icon: FileText, color: '#16A34A', bg: '#F0FDF4', pages: 68 },
  ]

  return (
    <div className="pb-4">
      <div className="bg-[#F8FAFC] rounded-xl p-4 mb-4">
        <div className="text-sm font-medium text-[#1E293B] mb-1">输出配置</div>
        <div className="text-xs text-[#64748B] mb-3">
          契约接口：生成 / 版本列表 / 对比 / 回滚（Mock 已关闭，需 setBidApi 注入真实 Client）
        </div>
        <div className="flex items-center gap-2">
          <Button
            loading={generating}
            onClick={() => void generateDocuments()}
            type="primary"
            icon={<FileOutput size={14} />}
            data-testid={BID_TEST_IDS.outputGenerate}
          >
            生成全部投标文件
          </Button>
          <Button onClick={() => void downloadLatest()} icon={<DownloadIcon size={14} />}>
            下载最新版本
          </Button>
          <Button loading={loading} onClick={() => void reload()}>
            刷新版本
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        {docTypes.map(doc => {
          const Icon = doc.icon
          return (
            <div key={doc.type} className="border border-[#E2E8F0] rounded-xl p-4">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: doc.bg }}>
                  <Icon size={20} color={doc.color} />
                </div>
                <div>
                  <div className="text-sm font-medium text-[#1E293B]">{doc.name}</div>
                  <div className="text-xs text-[#94A3B8]">{doc.pages} 页（演示）</div>
                </div>
              </div>
              <Button onClick={() => void downloadLatest()} size="small" type="primary" block className="text-xs h-7">
                下载
              </Button>
            </div>
          )
        })}
      </div>

      <div className="bg-[#F8FAFC] rounded-xl p-4">
        <div className="text-sm font-medium text-[#1E293B] mb-3 flex items-center gap-1.5">
          <History size={15} /> 版本历史
        </div>
        <div className="space-y-2">
          {versions.map((version, index) => {
            const isLatest = index === 0
            const label = `v${version.versionNumber}.0`
            return (
              <div key={version.id} className="flex items-start gap-3 bg-white rounded-lg p-3 border border-[#F1F5F9]">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${isLatest ? 'bg-[#F0FDF4]' : 'bg-[#F8FAFC]'}`}>
                  <FileText size={15} color={isLatest ? '#16A34A' : '#94A3B8'} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-xs font-medium text-[#1E293B] font-mono">{label}</span>
                    {isLatest && (
                      <Tag color="green" className="text-xs border-0 rounded">
                        最新
                      </Tag>
                    )}
                    <span className="text-xs text-[#94A3B8]">{version.createdBy.name}</span>
                  </div>
                  <div className="text-xs text-[#64748B] truncate">{version.changeSummary}</div>
                  <div className="text-xs text-[#CBD5E1]">{new Date(version.createdAt).toLocaleString('zh-CN', { hour12: false })}</div>
                </div>
                <div className="flex flex-col gap-1">
                  {!isLatest && (
                    <Button
                      data-testid={BID_TEST_IDS.outputRollback}
                      onClick={() => rollback(version)}
                      size="small"
                      type="text"
                      className="text-xs h-6"
                    >
                      回滚
                    </Button>
                  )}
                  {!isLatest && (
                    <Button
                      data-testid={BID_TEST_IDS.outputCompare}
                      onClick={() => void compareWithLatest(version)}
                      size="small"
                      type="text"
                      className="text-xs h-6"
                    >
                      对比
                    </Button>
                  )}
                  <Button
                    onClick={async () => {
                      const blob = await getBidApi().downloadDocumentBlob(taskId, version.id)
                      downloadBlob(blob, version.file.fileName)
                    }}
                    size="small"
                    type="text"
                    className="text-xs h-6"
                  >
                    下载
                  </Button>
                </div>
              </div>
            )
          })}
          {!versions.length && !loading && <div className="text-xs text-[#94A3B8]">暂无版本，请先生成投标文件</div>}
        </div>
      </div>
    </div>
  )
}
