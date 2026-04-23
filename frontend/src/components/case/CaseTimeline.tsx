import { formatDateTime } from '@/utils/format'
import { CaseStatusBadge } from '@/components/ui/StatusBadge'
import type { CaseDetail, SubmissionNote } from '@/types'
import { CheckCircle2, Clock, FileText, CreditCard, XCircle, Send } from 'lucide-react'

function TimelineStep({
  icon, label, time, detail, color = 'dot-gold', children,
}: {
  icon: React.ReactNode
  label: string
  time: string | null | undefined
  detail?: string
  color?: string
  children?: React.ReactNode
}) {
  return (
    <div className="timeline-item">
      <div className={`timeline-dot ${color}`}>{icon}</div>
      <div className="timeline-content ml-2">
        <div className="flex items-center justify-between mb-1">
          <span className="text-sm font-medium text-ink">{label}</span>
          <span className="text-xs text-muted font-mono">{formatDateTime(time)}</span>
        </div>
        {detail && <p className="text-xs text-muted">{detail}</p>}
        {children}
      </div>
    </div>
  )
}

function NoteBlock({ note }: { note: SubmissionNote }) {
  const isAccounts  = note.staff_role === 'accounts'
  const actionColor = note.action === 'registered' ? 'text-green'
    : note.action === 'rejected' || note.action === 'flagged' ? 'text-red'
    : 'text-teal'

  return (
    <div className={`mt-3 p-3 rounded border ${isAccounts ? 'border-teal/20 bg-teal-dim' : 'border-blue/20 bg-blue-dim'}`}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-medium text-ink capitalize">
          {note.staff_role === 'accounts' ? 'Accounts Department' : 'Registrar'} — {note.author_name}
        </span>
        <span className={`text-xs font-mono font-medium capitalize ${actionColor}`}>
          {note.action}
        </span>
      </div>
      <p className="text-xs text-muted italic">"{note.note}"</p>
      <p className="text-[10px] text-muted/60 mt-1 font-mono">{formatDateTime(note.created_at)}</p>
    </div>
  )
}

interface CaseTimelineProps { case_: CaseDetail }

export function CaseTimeline({ case_: c }: CaseTimelineProps) {
  const accountsNotes  = c.submission_notes.filter((n) => n.staff_role === 'accounts')
  const registrarNotes = c.submission_notes.filter((n) => n.staff_role === 'registrar')

  return (
    <div className="timeline">
      {/* Step 1: Case Created */}
      <TimelineStep
        icon={<FileText size={8} />}
        label="Case Created"
        time={c.created_at}
        detail={`${c.court.toUpperCase()} · ${c.case_type.replace('_', ' ')}`}
        color="dot-gold"
      />

      {/* Step 2: Payment */}
      {c.payment && (
        <TimelineStep
          icon={<CreditCard size={8} />}
          label={c.payment.status === 'confirmed' ? 'Payment Confirmed' : 'Payment Initiated'}
          time={c.payment.confirmed_at ?? c.payment.initiated_at}
          color={c.payment.status === 'confirmed' ? 'dot-green' : 'dot-gold'}
        >
          {c.payment.status === 'confirmed' && (
            <p className="text-xs text-green mt-1">
              GMD {c.payment.amount_paid} — Receipt {c.payment.receipt_number ?? 'N/A'}
            </p>
          )}
          {c.payment.has_discrepancy && (
            <p className="text-xs text-amber mt-1">⚠ Amount discrepancy detected</p>
          )}
        </TimelineStep>
      )}

      {/* Step 3: Submitted */}
      {c.submitted_at && (
        <TimelineStep
          icon={<Send size={8} />}
          label="Submitted to Accounts"
          time={c.submitted_at}
          color="dot-teal"
        />
      )}

      {/* Step 4: Accounts review */}
      {accountsNotes.length > 0 && (
        <TimelineStep
          icon={<CheckCircle2 size={8} />}
          label="Accounts Review"
          time={accountsNotes[accountsNotes.length - 1]?.created_at}
          color={accountsNotes.some(n => n.action === 'flagged') ? 'dot-red' : 'dot-teal'}
        >
          {accountsNotes.map((n) => <NoteBlock key={n.id} note={n} />)}
        </TimelineStep>
      )}

      {/* Step 5: Registrar review */}
      {registrarNotes.length > 0 && (
        <TimelineStep
          icon={c.status === 'registered' ? <CheckCircle2 size={8} /> : <XCircle size={8} />}
          label="Registrar Review"
          time={registrarNotes[registrarNotes.length - 1]?.created_at}
          color={c.status === 'registered' ? 'dot-green' : 'dot-red'}
        >
          {registrarNotes.map((n) => <NoteBlock key={n.id} note={n} />)}
        </TimelineStep>
      )}

      {/* Step 6: Registered */}
      {c.registered_at && (
        <TimelineStep
          icon={<CheckCircle2 size={8} />}
          label={`Case Registered — ${c.case_number}`}
          time={c.registered_at}
          color="dot-green"
        />
      )}

      {/* Current status if still pending */}
      {['draft', 'pending_accounts', 'pending_registrar'].includes(c.status) && (
        <TimelineStep
          icon={<Clock size={8} />}
          label="Awaiting Action"
          time={null}
          color="dot-gold"
        >
          <CaseStatusBadge status={c.status} />
        </TimelineStep>
      )}
    </div>
  )
}
