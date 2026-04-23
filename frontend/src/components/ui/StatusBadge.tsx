import { STATUS_CLASS, STATUS_LABEL, PAYMENT_STATUS_CLASS } from '@/utils/format'
import type { CaseStatus, PaymentStatus } from '@/types'

interface CaseStatusBadgeProps { status: CaseStatus }
export function CaseStatusBadge({ status }: CaseStatusBadgeProps) {
  const cls = STATUS_CLASS[status] ?? 'badge-draft'
  return <span className={cls}>{STATUS_LABEL[status] ?? status}</span>
}

interface PaymentStatusBadgeProps { status: PaymentStatus }
export function PaymentStatusBadge({ status }: PaymentStatusBadgeProps) {
  const cls = PAYMENT_STATUS_CLASS[status] ?? 'badge-draft'
  const label = status.charAt(0).toUpperCase() + status.slice(1)
  return <span className={cls}>{label}</span>
}
