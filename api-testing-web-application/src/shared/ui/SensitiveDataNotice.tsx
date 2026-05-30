import WarningAmberIcon from '@mui/icons-material/WarningAmber'
import { Alert, AlertTitle, type AlertProps } from '@mui/material'
import type { ReactNode } from 'react'

type SensitiveDataNoticeProps = {
  children?: ReactNode
  severity?: AlertProps['severity']
  title?: ReactNode
}

export function SensitiveDataNotice({
  children = 'Raw artifacts and visible bodies may include credentials, cookies, tokens, or proprietary payloads. Keep exports local and review content before sharing.',
  severity = 'warning',
  title = 'Sensitive data review',
}: SensitiveDataNoticeProps) {
  return (
    <Alert icon={<WarningAmberIcon fontSize="inherit" />} severity={severity} variant="outlined">
      <AlertTitle>{title}</AlertTitle>
      {children}
    </Alert>
  )
}
