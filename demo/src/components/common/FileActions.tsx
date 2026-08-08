import { useState } from 'react'
import { Button, Descriptions, Modal, Progress, Upload, message } from 'antd'
import type { UploadProps } from 'antd'
import { Eye, FileUp, UploadCloud } from 'lucide-react'

export interface PreviewFile {
  name: string
  type?: string
  size?: number | string
  version?: string
  source?: string
  updatedAt?: string
  content?: string
}

export function FilePreview({ file, buttonLabel = '预览' }: { file: PreviewFile; buttonLabel?: string }) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <Button type="link" size="small" icon={<Eye size={13} />} onClick={() => setOpen(true)}>{buttonLabel}</Button>
      <Modal title={file.name} open={open} onCancel={() => setOpen(false)} footer={<Button onClick={() => setOpen(false)}>关闭</Button>} width={720}>
        <Descriptions size="small" column={2} bordered className="mb-4">
          <Descriptions.Item label="文件类型">{file.type || '文档'}</Descriptions.Item>
          <Descriptions.Item label="大小">{file.size || '演示文件'}</Descriptions.Item>
          <Descriptions.Item label="版本">{file.version || 'v1.0'}</Descriptions.Item>
          <Descriptions.Item label="来源">{file.source || '平台上传'}</Descriptions.Item>
          {file.updatedAt && <Descriptions.Item label="更新时间" span={2}>{file.updatedAt}</Descriptions.Item>}
        </Descriptions>
        <div className="min-h-44 whitespace-pre-wrap rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-5 text-sm leading-7 text-[#475569]">
          {file.content || `${file.name} 的安全预览区域。正式环境由 /files/{fileId}/preview 返回短期授权内容。`}
        </div>
      </Modal>
    </>
  )
}

export function AppUpload({
  onFiles,
  accept,
  maxSizeMb = 200,
  multiple = false,
  compact = false,
  label = '拖拽文件到此处，或点击选择文件',
}: {
  onFiles: (files: File[]) => void | Promise<void>
  accept?: string
  maxSizeMb?: number
  multiple?: boolean
  compact?: boolean
  label?: string
}) {
  const [progress, setProgress] = useState(0)
  const [uploading, setUploading] = useState(false)

  const beforeUpload: UploadProps['beforeUpload'] = async (file, fileList) => {
    if (file.size > maxSizeMb * 1024 * 1024) {
      message.error(`${file.name} 超过 ${maxSizeMb} MiB 限制`)
      return Upload.LIST_IGNORE
    }
    if (file.uid !== fileList[0]?.uid) return false
    setUploading(true)
    setProgress(24)
    try {
      await Promise.resolve(onFiles(fileList as unknown as File[]))
      setProgress(100)
      window.setTimeout(() => {
        setUploading(false)
        setProgress(0)
      }, 350)
    } catch (error) {
      setUploading(false)
      setProgress(0)
      message.error(error instanceof Error ? error.message : '文件处理失败，请重试')
    }
    return false
  }

  if (compact) {
    return (
      <Upload accept={accept} multiple={multiple} showUploadList={false} beforeUpload={beforeUpload}>
        <Button loading={uploading} icon={<FileUp size={14} />}>{label}</Button>
      </Upload>
    )
  }

  return (
    <div>
      <Upload.Dragger accept={accept} multiple={multiple} showUploadList={false} beforeUpload={beforeUpload}>
        <UploadCloud size={30} className="mx-auto mb-2 text-[#2563EB]" />
        <div className="text-sm text-[#475569]">{label}</div>
        <div className="mt-1 text-xs text-[#64748B]">单文件最大 {maxSizeMb} MiB，上传前自动校验文件</div>
      </Upload.Dragger>
      {uploading && <Progress className="mt-2" percent={progress} size="small" />}
    </div>
  )
}
