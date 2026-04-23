import { format, formatDistanceToNow, parseISO } from 'date-fns'
import type { CaseStatus, PaymentStatus, CourtTier } from '@/types'

export function formatDate(iso: string | null | undefined, fmt = 'dd MMM yyyy'): string {
  if (!iso) return '—'
  try { return format(parseISO(iso), fmt) } catch { return '—' }
}

export function formatDateTime(iso: string | null | undefined): string {
  return formatDate(iso, 'dd MMM yyyy, HH:mm')
}

export function formatRelative(iso: string | null | undefined): string {
  if (!iso) return '—'
  try { return formatDistanceToNow(parseISO(iso), { addSuffix: true }) } catch { return '—' }
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

export function formatMoney(amount: string | number | null | undefined): string {
  if (amount == null) return '—'
  const n = typeof amount === 'string' ? parseFloat(amount) : amount
  return `GMD ${n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

// ── Status display maps ───────────────────────────────────────────────────

export const STATUS_LABEL: Record<CaseStatus, string> = {
  draft:              'Draft',
  pending_accounts:   'Pending Accounts',
  pending_registrar:  'Pending Registrar',
  registered:         'Registered',
  rejected:           'Rejected',
  resubmitted:        'Resubmitted',
  assigned:           'Assigned',
  hearing_scheduled:  'Hearing Scheduled',
  active:             'In Hearing',
  judgment_pending:   'Judgment Pending',
  judgment_delivered: 'Judgment Delivered',
  appeal_filed:       'Appeal Filed',
  closed:             'Closed',
  archived:           'Archived',
}

export const STATUS_CLASS: Record<CaseStatus, string> = {
  draft:              'badge-draft',
  pending_accounts:   'badge-pending',
  pending_registrar:  'badge-review',
  registered:         'badge-registered',
  rejected:           'badge-rejected',
  resubmitted:        'badge-pending',
  assigned:           'badge-teal',
  hearing_scheduled:  'badge-blue',
  active:             'badge-blue',
  judgment_pending:   'badge-amber',
  judgment_delivered: 'badge-registered',
  appeal_filed:       'badge-pending',
  closed:             'badge-draft',
  archived:           'badge-draft',
}

export const PAYMENT_STATUS_CLASS: Record<PaymentStatus, string> = {
  pending:   'badge-draft',
  initiated: 'badge-pending',
  confirmed: 'badge-confirmed',
  failed:    'badge-failed',
  refunded:  'badge-draft',
}

export const COURT_LABEL: Record<CourtTier, string> = {
  cadi:       'Cadi Court',
  magistrate: 'Magistrates Court',
  high:       'High Court',
  appeal:     'Court of Appeal',
  supreme:    'Supreme Court',
}
