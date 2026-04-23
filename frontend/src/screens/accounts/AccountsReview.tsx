import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { ArrowLeft, CheckCircle2, Flag, AlertTriangle, FileText } from 'lucide-react'
import { casesApi } from '@/api/endpoints'
import { getApiError } from '@/api/client'
import { CaseStatusBadge, PaymentStatusBadge } from '@/components/ui/StatusBadge'
import { PageLoader, Spinner } from '@/components/ui/Spinner'
import { formatDateTime, formatMoney, COURT_LABEL } from '@/utils/format'

interface ReviewForm { note: string; action: 'forward' | 'flag' }

export function AccountsReview() {
  const { caseId } = useParams<{ caseId: string }>()
  const navigate   = useNavigate()
  const qc         = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['case', caseId],
    queryFn:  () => casesApi.get(caseId!),
    enabled:  !!caseId,
  })
  const case_ = data?.data

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<ReviewForm>({
    defaultValues: { action: 'forward' },
  })
  const action = watch('action')

  const reviewMutation = useMutation({
    mutationFn: (d: ReviewForm) => casesApi.accountsReview(caseId!, d.note, d.action),
    onSuccess: () => {
      toast.success(action === 'forward' ? 'Case forwarded to Registrar.' : 'Case flagged and returned.')
      qc.invalidateQueries({ queryKey: ['accounts-queue'] })
      navigate('/accounts/queue')
    },
    onError: (err) => toast.error(getApiError(err)),
  })

  if (isLoading) return <PageLoader />
  if (!case_) return <p className="p-6 text-muted">Case not found.</p>

  const payment    = case_.payment
  const discrepancy = payment?.has_discrepancy

  return (
    <div className="page-container max-w-3xl">
      <Link to="/accounts/queue" className="btn-ghost btn btn-sm mb-4">
        <ArrowLeft size={14} /> Back to Queue
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="page-title">Accounts Review</h1>
          <p className="text-sm text-muted font-mono">
            {case_.case_number ?? case_.id.slice(0, 8).toUpperCase()}
            {' · '}{COURT_LABEL[case_.court]}
          </p>
        </div>
        <CaseStatusBadge status={case_.status} />
      </div>

      <div className="grid grid-cols-2 gap-5 mb-5">
        {/* Case summary */}
        <div className="card">
          <h2 className="card-title mb-3">Case Details</h2>
          <div className="space-y-2 text-sm">
            <div><span className="text-muted text-xs">Title</span><p className="text-ink">{case_.title}</p></div>
            <div><span className="text-muted text-xs">Type</span><p className="text-ink capitalize">{case_.case_type.replace('_',' ')}</p></div>
            <div><span className="text-muted text-xs">Filed By</span><p className="text-ink">{case_.submitted_by_name}</p><p className="text-muted text-xs">{case_.firm_name}</p></div>
            <div><span className="text-muted text-xs">Submitted</span><p className="text-ink">{formatDateTime(case_.submitted_at)}</p></div>
          </div>
        </div>

        {/* Payment verification */}
        <div className={`card ${discrepancy ? 'border-amber/30 bg-amber-dim/30' : ''}`}>
          <div className="flex items-center justify-between mb-3">
            <h2 className="card-title">Payment Verification</h2>
            {payment && <PaymentStatusBadge status={payment.status} />}
          </div>
          {payment ? (
            <div className="space-y-2 text-sm">
              <div className="flex justify-between py-2 border-b border-border">
                <span className="text-muted text-xs">Fee Required</span>
                <span className="font-mono text-ink">{formatMoney(payment.amount_due)}</span>
              </div>
              <div className="flex justify-between py-2 border-b border-border">
                <span className="text-muted text-xs">Amount Paid</span>
                <span className={`font-mono ${discrepancy ? 'text-amber' : 'text-green'}`}>
                  {formatMoney(payment.amount_paid)}
                </span>
              </div>
              <div className="flex justify-between py-2 border-b border-border">
                <span className="text-muted text-xs">MUSU Reference</span>
                <span className="font-mono text-xs text-muted">{payment.musu_reference ?? '—'}</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-muted text-xs">Confirmed</span>
                <span className="text-xs text-muted">{formatDateTime(payment.confirmed_at)}</span>
              </div>
              {discrepancy && (
                <div className="flex items-center gap-2 p-2 bg-amber-dim border border-amber/20 rounded">
                  <AlertTriangle size={13} className="text-amber" />
                  <p className="text-xs text-amber">Fee discrepancy — paid differs from amount due.</p>
                </div>
              )}
              {payment.receipt_number && (
                <p className="text-xs text-muted font-mono">Receipt: {payment.receipt_number}</p>
              )}
            </div>
          ) : (
            <p className="text-sm text-red">No payment record found.</p>
          )}
        </div>
      </div>

      {/* Documents */}
      <div className="card mb-5">
        <h2 className="card-title mb-3 flex items-center gap-2">
          <FileText size={15} className="text-gold" /> Submitted Documents ({case_.documents.length})
        </h2>
        {case_.documents.length === 0 ? (
          <p className="text-sm text-red">⚠ No documents uploaded.</p>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr><th>Filename</th><th>Category</th><th>Size</th><th>Uploaded</th><th>Action</th></tr>
              </thead>
              <tbody>
                {case_.documents.map((doc) => (
                  <tr key={doc.id}>
                    <td className="text-ink text-xs">{doc.filename}</td>
                    <td className="text-muted text-xs capitalize">{doc.category.replace('_',' ')}</td>
                    <td className="text-muted text-xs">{(doc.file_size / 1024).toFixed(0)} KB</td>
                    <td className="text-muted text-xs">{formatDateTime(doc.uploaded_at)}</td>
                    <td>
                      {doc.file_url && (
                        <a href={doc.file_url} target="_blank" rel="noopener noreferrer"
                          className="btn-ghost btn btn-sm text-xs">View</a>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Review form */}
      <div className="card">
        <h2 className="card-title mb-4">Submission Note</h2>
        <form onSubmit={handleSubmit((d) => reviewMutation.mutate(d))}>
          <div className="form-group">
            <label className="form-label">Review Note *</label>
            <textarea className="form-textarea" rows={4}
              placeholder={action === 'forward'
                ? 'Confirm that the payment matches the required fee and documents are in order…'
                : 'Describe the discrepancy or issue that requires correction…'}
              {...register('note', { required: 'Note is required', minLength: { value: 10, message: 'Note must be at least 10 characters.' } })} />
            {errors.note && <span className="form-error">{errors.note.message}</span>}
          </div>

          {/* Action selector */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <button type="button" onClick={() => setValue('action', 'forward')}
              className={`p-4 rounded border text-sm text-left transition-colors
                ${action === 'forward' ? 'border-teal/40 bg-teal-dim' : 'border-border bg-surface2 hover:border-border2'}`}>
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle2 size={15} className="text-teal" />
                <span className="font-medium text-ink">Forward to Registrar</span>
              </div>
              <p className="text-xs text-muted">Payment verified — pass case to Registrar for registration.</p>
            </button>

            <button type="button" onClick={() => setValue('action', 'flag')}
              className={`p-4 rounded border text-sm text-left transition-colors
                ${action === 'flag' ? 'border-red/40 bg-red-dim' : 'border-border bg-surface2 hover:border-border2'}`}>
              <div className="flex items-center gap-2 mb-1">
                <Flag size={15} className="text-red" />
                <span className="font-medium text-ink">Flag & Return</span>
              </div>
              <p className="text-xs text-muted">Issue found — return to lawyer for correction.</p>
            </button>
          </div>

          <div className="flex justify-end">
            <button type="submit" disabled={reviewMutation.isPending}
              className={action === 'forward' ? 'btn-primary btn' : 'btn-danger btn'}>
              {reviewMutation.isPending ? <Spinner size="sm" /> : (
                action === 'forward'
                  ? <><CheckCircle2 size={15} /> Forward to Registrar</>
                  : <><Flag size={15} /> Flag Case</>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
