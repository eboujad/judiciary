import { useParams, Link, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { ArrowLeft, CheckCircle2, XCircle, FileText, MessageSquare } from 'lucide-react'
import { casesApi } from '@/api/endpoints'
import { getApiError } from '@/api/client'
import { CaseStatusBadge } from '@/components/ui/StatusBadge'
import { PageLoader, Spinner } from '@/components/ui/Spinner'
import { formatDateTime, COURT_LABEL } from '@/utils/format'

interface ReviewForm { note: string; action: 'register' | 'reject' }

export function RegistrarReview() {
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
    defaultValues: { action: 'register' },
  })
  const action = watch('action')

  const reviewMutation = useMutation({
    mutationFn: (d: ReviewForm) => casesApi.registrarReview(caseId!, d.note, d.action),
    onSuccess: (res) => {
      const registered = res.data.status === 'registered'
      toast.success(registered
        ? `Case registered — ${res.data.case_number}`
        : 'Case rejected and lawyer notified.')
      qc.invalidateQueries({ queryKey: ['registrar-queue'] })
      navigate('/registrar/queue')
    },
    onError: (err) => toast.error(getApiError(err)),
  })

  if (isLoading) return <PageLoader />
  if (!case_) return <p className="p-6 text-muted">Case not found.</p>

  const accountsNote = case_.submission_notes.filter((n) => n.staff_role === 'accounts').at(-1)

  return (
    <div className="page-container max-w-3xl">
      <Link to="/registrar/queue" className="btn-ghost btn btn-sm mb-4">
        <ArrowLeft size={14} /> Back to Queue
      </Link>

      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="page-title">Registrar Review</h1>
          <p className="text-sm text-muted font-mono">
            {case_.case_number ?? case_.id.slice(0, 8).toUpperCase()}
            {' · '}{COURT_LABEL[case_.court]}
          </p>
        </div>
        <CaseStatusBadge status={case_.status} />
      </div>

      {/* Case summary */}
      <div className="card mb-4">
        <h2 className="card-title mb-3">Case Details</h2>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><p className="text-muted text-xs">Title</p><p className="text-ink font-medium">{case_.title}</p></div>
          <div><p className="text-muted text-xs">Type</p><p className="text-ink capitalize">{case_.case_type.replace('_',' ')}</p></div>
          <div><p className="text-muted text-xs">Filed By</p><p className="text-ink">{case_.submitted_by_name}</p><p className="text-muted text-xs">{case_.firm_name}</p></div>
          <div><p className="text-muted text-xs">Opposing Party</p><p className="text-ink">{case_.opposing_party_name || '—'}</p></div>
          {case_.description && (
            <div className="col-span-2"><p className="text-muted text-xs">Brief Facts</p><p className="text-ink text-xs leading-relaxed">{case_.description}</p></div>
          )}
          {case_.relief_sought && (
            <div className="col-span-2"><p className="text-muted text-xs">Relief Sought</p><p className="text-ink text-xs leading-relaxed">{case_.relief_sought}</p></div>
          )}
        </div>
      </div>

      {/* Accounts note */}
      {accountsNote && (
        <div className="card mb-4 border-teal/20 bg-teal-dim/20">
          <div className="flex items-center gap-2 mb-2">
            <MessageSquare size={14} className="text-teal" />
            <h2 className="card-title">Accounts Department Note</h2>
            <span className="text-xs text-muted ml-auto">{formatDateTime(accountsNote.created_at)}</span>
          </div>
          <p className="text-xs text-muted italic mb-1">"{accountsNote.note}"</p>
          <p className="text-[10px] text-muted/60">— {accountsNote.author_name}</p>
        </div>
      )}

      {/* Documents */}
      <div className="card mb-4">
        <h2 className="card-title mb-3 flex items-center gap-2">
          <FileText size={15} className="text-gold" /> Documents ({case_.documents.length})
        </h2>
        {case_.documents.length === 0 ? (
          <p className="text-sm text-red">⚠ No documents submitted.</p>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr><th>Filename</th><th>Category</th><th>Uploaded By</th><th>Date</th><th>View</th></tr>
              </thead>
              <tbody>
                {case_.documents.map((doc) => (
                  <tr key={doc.id}>
                    <td className="text-ink text-xs">{doc.filename}</td>
                    <td className="text-muted text-xs capitalize">{doc.category.replace('_',' ')}</td>
                    <td className="text-muted text-xs">{doc.uploaded_by_name}</td>
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

      {/* Registration form */}
      <div className="card">
        <h2 className="card-title mb-4">Registrar Decision</h2>
        <form onSubmit={handleSubmit((d) => reviewMutation.mutate(d))}>
          <div className="form-group">
            <label className="form-label">Registrar Note *</label>
            <textarea className="form-textarea" rows={4}
              placeholder={action === 'register'
                ? 'All documents are in order. Case meets jurisdictional requirements…'
                : 'Reason for rejection (this note will be sent to the filing lawyer)…'}
              {...register('note', { required: 'Note is required', minLength: { value: 10, message: 'Minimum 10 characters.' } })} />
            {errors.note && <span className="form-error">{errors.note.message}</span>}
          </div>

          <div className="grid grid-cols-2 gap-3 mb-5">
            <button type="button" onClick={() => setValue('action', 'register')}
              className={`p-4 rounded border text-sm text-left transition-colors
                ${action === 'register' ? 'border-green/40 bg-green-dim' : 'border-border bg-surface2 hover:border-border2'}`}>
              <div className="flex items-center gap-2 mb-1">
                <CheckCircle2 size={15} className="text-green" />
                <span className="font-medium text-ink">Register Case</span>
              </div>
              <p className="text-xs text-muted">Issue an official case number. Case proceeds to Chief Justice assignment.</p>
            </button>

            <button type="button" onClick={() => setValue('action', 'reject')}
              className={`p-4 rounded border text-sm text-left transition-colors
                ${action === 'reject' ? 'border-red/40 bg-red-dim' : 'border-border bg-surface2 hover:border-border2'}`}>
              <div className="flex items-center gap-2 mb-1">
                <XCircle size={15} className="text-red" />
                <span className="font-medium text-ink">Reject</span>
              </div>
              <p className="text-xs text-muted">Return case to lawyer with reason. Lawyer can correct and resubmit.</p>
            </button>
          </div>

          <div className="flex justify-end">
            <button type="submit" disabled={reviewMutation.isPending}
              className={action === 'register' ? 'btn-primary btn' : 'btn-danger btn'}>
              {reviewMutation.isPending ? <Spinner size="sm" /> : (
                action === 'register'
                  ? <><CheckCircle2 size={15} /> Register Case</>
                  : <><XCircle size={15} /> Reject Case</>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
