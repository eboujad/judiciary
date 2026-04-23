import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { ClipboardCheck, AlertCircle } from 'lucide-react'
import { casesApi } from '@/api/endpoints'
import { CaseStatusBadge, PaymentStatusBadge } from '@/components/ui/StatusBadge'
import { PageLoader } from '@/components/ui/Spinner'
import { formatDateTime, formatMoney, COURT_LABEL } from '@/utils/format'

export function AccountsQueue() {
  const { data, isLoading } = useQuery({
    queryKey: ['accounts-queue'],
    queryFn:  () => casesApi.accountsQueue(),
    refetchInterval: 30000,
  })

  const cases = data?.data?.results ?? []

  if (isLoading) return <PageLoader />

  return (
    <div className="page-container">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <ClipboardCheck size={20} className="text-gold" /> Accounts Queue
          </h1>
          <p className="page-subtitle">
            Cases awaiting fee verification. Verify that the MUSU payment matches the required form fees.
          </p>
        </div>
        <span className="text-2xl font-bold font-mono text-gold">{cases.length}</span>
      </div>

      {cases.length === 0 ? (
        <div className="card empty-state">
          <ClipboardCheck size={40} className="text-muted/40 mb-4" />
          <p className="empty-state-title">Queue is empty</p>
          <p className="empty-state-desc">No cases are currently awaiting Accounts review.</p>
        </div>
      ) : (
        <div className="card">
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Case Title</th>
                  <th>Court</th>
                  <th>Firm</th>
                  <th>Fee Due</th>
                  <th>Payment</th>
                  <th>Submitted</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c) => (
                  <tr key={c.id}>
                    <td className="font-mono text-xs text-gold">
                      {c.case_number ?? c.id.slice(0, 8).toUpperCase()}
                    </td>
                    <td className="font-medium text-ink max-w-xs truncate">{c.title}</td>
                    <td className="text-muted text-xs">{COURT_LABEL[c.court]}</td>
                    <td className="text-muted text-xs">{c.firm_name}</td>
                    <td className="font-mono text-xs text-ink">{formatMoney(c.total_fee)}</td>
                    <td>
                      {c.payment_status ? (
                        <PaymentStatusBadge status={c.payment_status as any} />
                      ) : '—'}
                    </td>
                    <td className="text-muted text-xs">{formatDateTime(c.submitted_at)}</td>
                    <td><CaseStatusBadge status={c.status} /></td>
                    <td>
                      <Link to={`/accounts/review/${c.id}`}
                        className="btn-primary btn btn-sm">
                        Review
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Discrepancy warning */}
          <div className="flex items-center gap-2 mt-4 p-3 bg-amber-dim border border-amber/20 rounded-lg">
            <AlertCircle size={14} className="text-amber flex-shrink-0" />
            <p className="text-xs text-muted">
              Check that <strong className="text-ink">Amount Paid ≥ Fee Due</strong> before forwarding to the Registrar.
              Flag any discrepancies with a note.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
