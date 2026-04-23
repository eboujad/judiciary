// ── User & Auth ───────────────────────────────────────────────────────────

export type UserRole =
  | 'system_admin'
  | 'accounts_dept'
  | 'registrar'
  | 'chief_justice'
  | 'judge'
  | 'judge_clerk'
  | 'lawyer'
  | 'public_user'
  | 'respondent'
  | 'witness'
  | 'interpreter'

export interface User {
  id: string
  email: string
  phone: string
  first_name: string
  last_name: string
  full_name: string
  role: UserRole
  is_active: boolean
  is_verified: boolean
  two_fa_enabled: boolean
  created_at: string
}

export interface AuthTokens {
  access: string
  refresh: string
  user: User
}

// ── Firms & Lawyers ───────────────────────────────────────────────────────

export type FirmStatus = 'pending' | 'active' | 'suspended' | 'revoked'

export interface LawFirm {
  id: string
  name: string
  bar_number: string
  address: string
  phone: string
  email: string
  status: FirmStatus
  lawyer_count: number
  admin_email: string | null
  created_at: string
  approved_at: string | null
}

export interface Lawyer {
  id: string
  email: string
  full_name: string
  phone: string
  bar_number: string
  firm_name: string
  specialisation: string
  is_active: boolean
  created_at: string
}

// ── Cases ─────────────────────────────────────────────────────────────────

export type CourtTier = 'cadi' | 'magistrate' | 'high' | 'appeal' | 'supreme'

export type CaseType =
  | 'criminal_complaint' | 'bail_application'
  | 'civil_claim' | 'debt_recovery'
  | 'divorce' | 'custody'
  | 'land_dispute' | 'constitutional'
  | 'islamic_family' | 'other'

export type CaseStatus =
  | 'draft'
  | 'pending_accounts'
  | 'pending_registrar'
  | 'registered'
  | 'rejected'
  | 'resubmitted'
  | 'assigned'
  | 'hearing_scheduled'
  | 'active'
  | 'judgment_pending'
  | 'judgment_delivered'
  | 'appeal_filed'
  | 'closed'
  | 'archived'

export interface CourtForm {
  id: string
  court: CourtTier
  case_type: string
  name: string
  description: string
  fee_amount: string
}

export interface SubmissionNote {
  id: string
  staff_role: 'accounts' | 'registrar'
  note: string
  action: 'forwarded' | 'registered' | 'rejected' | 'flagged'
  author_name: string
  author_role: string
  created_at: string
}

export interface CaseListItem {
  id: string
  case_number: string | null
  title: string
  court: CourtTier
  case_type: CaseType
  status: CaseStatus
  submitted_by_name: string
  firm_name: string
  total_fee: string | null
  payment_status: string | null
  created_at: string
  submitted_at: string | null
}

export interface CaseDetail extends CaseListItem {
  description: string
  opposing_party_name: string
  relief_sought: string
  is_sealed: boolean
  selected_forms: Array<{ id: string; form: CourtForm }>
  submission_notes: SubmissionNote[]
  documents: Document[]
  payment: Payment | null
  registered_at: string | null
  updated_at: string
}

// ── Documents ─────────────────────────────────────────────────────────────

export type DocumentCategory =
  | 'pleading' | 'affidavit' | 'exhibit' | 'supporting'
  | 'court_order' | 'judgment' | 'correspondence' | 'other'

export interface Document {
  id: string
  category: DocumentCategory
  description: string
  filename: string
  mime_type: string
  file_size: number
  sha256_hash: string
  uploaded_by_name: string
  uploaded_at: string
  is_signed: boolean
  signed_at: string | null
  file_url: string | null
  is_active: boolean
}

// ── Payments ──────────────────────────────────────────────────────────────

export type PaymentStatus = 'pending' | 'initiated' | 'confirmed' | 'failed' | 'refunded'

export interface Payment {
  id: string
  amount_due: string
  amount_paid: string | null
  status: PaymentStatus
  musu_reference: string | null
  musu_transaction_id: string | null
  payer_phone: string
  is_waived: boolean
  has_discrepancy: boolean
  created_at: string
  initiated_at: string | null
  confirmed_at: string | null
  receipt_number: string | null
}

// ── Pagination ────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  count: number
  total_pages: number
  next: string | null
  previous: string | null
  results: T[]
}

// ── Audit ─────────────────────────────────────────────────────────────────

export interface AuditLog {
  id: string
  actor_email: string | null
  actor_role: string
  action: string
  content_type: string
  object_id: string
  note: string
  severity: 'info' | 'warning' | 'critical'
  ip_address: string | null
  created_at: string
}
