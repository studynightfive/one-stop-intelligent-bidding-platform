import type { ReactNode } from 'react'
import { Button, Modal } from 'antd'
import type { ButtonProps } from 'antd'

export function ConfirmAction({
  title,
  description,
  onConfirm,
  children,
  danger = false,
  buttonProps,
}: {
  title: string
  description: string
  onConfirm: () => void | Promise<void>
  children: ReactNode
  danger?: boolean
  buttonProps?: ButtonProps
}) {
  return (
    <Button
      {...buttonProps}
      danger={danger || buttonProps?.danger}
      onClick={() => Modal.confirm({
        title,
        content: description,
        okText: '确认',
        cancelText: '取消',
        okButtonProps: { danger },
        onOk: onConfirm,
      })}
    >
      {children}
    </Button>
  )
}
