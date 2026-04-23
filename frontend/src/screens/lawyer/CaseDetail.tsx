import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { ArrowLeft, Upload, FileText, RotateCcw, CreditCard, ShieldCheck } from 'lucide-react'
import { casesApi, documentsApi } from '@/api/endpoints'
import { getApiError } from '@/api/client'
import { CaseStatusBadge, PaymentStatusBadge } from '@/components/ui/StatusBadge'
import { CaseTimeline } from '@/components/case/CaseTimeline'
import { PageLoader, Spinner } from '@/components/ui/Spinner'
import { formatDate, formatFileSize, formatMoney, COURT_LABEL } from '@/utils/format'
import { useRole } from '@/stores/authStore'
import type { DocumentCategory } from '@/types'

const DOC_CATEGORIES: { value: DocumentCategory; label: string }[] = [
  { value: 'pleading',      label: 'Pleading / Statement of Claim' },
  { value: 'affidavit',     label: 'Affidavit' },
  { value: 'exhibit',       label: 'Exhibit' },
  { value: 'supporting',    label: 'Supporting Document' },
  { value: 'correspondence',label: 'Correspondence' },
  { value: 'other',         label: 'Other' },
]

function DocumentRow({ doc }: { doc: any; caseId: string }) {
  const verifyMutation  = useMutation({
    mutationFn: () => documentsApi.verify(doc.id),
    onSuccess: (res) => {
      const { intact } = res.data
      intact
        ? toast.success(`${doc.filename}: integrity verified ✓`)
        : toast.error(`${doc.filename}: TAMPER DETECTED!`)
    },
  })
  return (
    <tr>
      <td>
        <div className="flex items-center gap-2">
          <FileText size={14} className="text-gold flex-shrink-0" />
          <div>
            <p className="text-ink text-xs">{doc.filename}</p>
            <p className="text-muted text-[10px]">{doc.category}</p>
          </div>
        </div>
      </td>
      <td className="text-muted text-xs">{formatFileSize(doc.file_size)}</td>
      <td className="text-muted text-xs font-mono">{doc.sha256_hash.slice(0, 12)}…</td>
      <td className="text-muted text-xs">{doc.uploaded_by_name}</td>
      <td className="text-muted text-xs">{formatDate(doc.uploaded_at)}</td>
      <td>
        <div className="flex items-center gap-2">
          {doc.file_url && (
            <a href={doc.file_url} target="_blank" rel="noopener noreferrer"
              className="btn-ghost btn btn-sm text-xs">View</a>
          )}
          <button onClick={() => verifyMutation.mutate()} className="btn-ghost btn btn-sm text-xs">
            {verifyMutation.isPending ? <Spinner size="sm" /> : <ShieldCheck size={12} />}
          </button>
        </div>
      </td>
    </tr>
  )
}

function UploadModal({ caseId, onClose }: { caseId: string; onClose: () => void }) {
  const qc          = useQueryClient()
  const [file, setFile]         = useState<File | null>(null)
  const [category, setCategory] = useState<DocumentCategory>('other')
  const [desc, setDesc]         = useState('')

  const uploadMutation = useMutation({
    mutationFn: () => documentsApi.upload(caseId, file!, category, desc),
    onSuccess: () => {
      toast.success('Document uploaded.')
      qc.invalidateQueries({ queryKey: ['case', caseId] })
      onClose()
    },
    onError: (err) => toast.error(getApiError(err)),
  })

  return (
    <div className="fixed inset-0 bg-bg/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="card w-full max-w-md">
        <div className="card-header">
          <h2 className="card-title">Upload Document</h2>
          <button onClick={onClose} className="btn-ghost btn btn-sm">✕</button>
        </div>

        <div className="form-group">
          <label className="form-label">File *</label>
          <input type="file" accept=".pdf,.jpg,.jpeg,.png,.tiff,.doc,.docx"
            className="form-input text-xs py-2"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <span className="form-hint">PDF, JPEG, PNG, TIFF, DOC, DOCX — max 50MB</span>
        </div>

        <div className="form-group">
          <label className="form-label">Category</label>
          <select className="form-select" value={category}
            onChange={(e) => setCategory(e.target.value as DocumentCategory)}>
            {DOC_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </div>

        <div className="form-group">
          <label className="form-label">Description (optional)</label>
          <input className="form-input" value={desc} onChange={(e) => setDesc(e.target.value)}
            placeholder="e.g. Sworn affidavit of plaintiff" />
        </div>

        <div className="flex justify-end gap-3 mt-2">
          <button onClick={onClose} className="btn-secondary btn">Cancel</button>
          <button onClick={() => file && uploadMutation.mutate()}
            disabled={!file || uploadMutation.isPending}
            className="btn-primary btn">
            {uploadMutation.isPending ? <Spinner size="sm" /> : <><Upload size={14} /> Upload</>}
          </button>
        </div>
      </div>
    </div>
  )
}

export function CaseDetail() {
  const { caseId }      = useParams<{ caseId: string }>()
  const qc              = useQueryClient()
  const role            = useRole()
  const [showUpload, setShowUpload] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['case', caseId],
    queryFn:  () => casesApi.get(caseId!),
    enabled:  !!caseId,
  })
  const case_ = data?.data

  const resubmitMutation = useMutation({
    mutationFn: () => casesApi.resubmit(caseId!),
    onSuccess: () => {
      toast.success('Case resubmitted.')
      qc.invalidateQueries({ queryKey: ['case', caseId] })
      qc.invalidateQueries({ queryKey: ['my-cases'] })
    },
    onError: (err) => toast.error(getApiError(err)),
  })

  if (isLoading) return <PageLoader />
  if (!case_) return <p className="p-6 text-muted">Case not found.</p>

  const canUpload  = ['draft', 'rejected', 'resubmitted'].includes(case_.status) && role === 'lawyer'
  const canResubmit = case_.status === 'rejected' && role === 'lawyer'
  const needsPayment = case_.status === 'draft' && (!case_.payment || case_.payment.status !== 'confirmed') && role === 'lawyer'

  return (
    <div className="page-container">
      <Link to="/cases" className="btn-ghost btn btn-sm mb-4">
        <ArrowLeft size={14} /> Back to Cases
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="page-title mb-0">{case_.title}</h1>
            <CaseStatusBadge status={case_.status} />
          </div>
          <p className="text-sm text-muted font-mono">
            {case_.case_number ?? `Draft — ${case_.id.slice(0, 8).toUpperCase()}`}
            {' · '}{COURT_LABEL[case_.court]}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {needsPayment && (
            <Link to={`/cases/${caseId}/payment`} className="btn-primary btn">
              <CreditCard size={15} /> Pay Filing Fee
            </Link>
          )}
          {canResubmit && (
            <button onClick={() => resubmitMutation.mutate()}
              disabled={resubmitMutation.isPending}
              className="btn-secondary btn">
              {resubmitMutation.isPending ? <Spinner size="sm" /> : <><RotateCcw size={14} /> Resubmit</>}
            </button>
          )}
          {canUpload && (
            <button onClick={() => setShowUpload(true)} className="btn-secondary btn">
              <Upload size={14} /> Upload Document
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left: details + documents */}
        <div className="col-span-2 space-y-5">
          {/* Case info */}
          <div className="card">
            <h2 className="card-title mb-4">Case Information</h2>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted text-xs mb-1">Court</p>
                <p className="text-ink">{COURT_LABEL[case_.court]}</p>
              </div>
              <div>
                <p className="text-muted text-xs mb-1">Case Type</p>
                <p className="text-ink capitalize">{case_.case_type.replace('_', ' ')}</p>
              </div>
              <div>
                <p className="text-muted text-xs mb-1">Filed By</p>
                <p className="text-ink">{case_.submitted_by_name}</p>
                <p className="text-muted text-xs">{case_.firm_name}</p>
              </div>
              <div>
                <p className="text-muted text-xs mb-1">Opposing Party</p>
                <p className="text-ink">{case_.opposing_party_name || '—'}</p>
              </div>
              {case_.description && (
                <div className="col-span-2">
                  <p className="text-muted text-xs mb-1">Brief Facts</p>
                  <p className="text-ink text-xs leading-relaxed">{case_.description}</p>
                </div>
              )}
              {case_.relief_sought && (
                <div className="col-span-2">
                  <p className="text-muted text-xs mb-1">Relief Sought</p>
                  <p className="text-ink text-xs leading-relaxed">{case_.relief_sought}</p>
                </div>
              )}
            </div>
          </div>

          {/* Payment */}
          {case_.payment && (
            <div className="card">
              <div className="card-header">
                <h2 className="card-title flex items-center gap-2">
                  <CreditCard size={15} className="text-gold" /> Payment
                </h2>
                <PaymentStatusBadge status={case_.payment.status} />
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <p className="text-muted text-xs">Amount Due</p>
                  <p className="font-mono text-ink">{formatMoney(case_.payment.amount_due)}</p>
                </div>
                <div>
                  <p className="text-muted text-xs">Amount Paid</p>
                  <p className="font-mono text-ink">{formatMoney(case_.payment.amount_paid)}</p>
                </div>
                <div>
                  <p className="text-muted text-xs">Receipt</p>
                  <p className="font-mono text-xs text-ink">{case_.payment.receipt_number ?? '—'}</p>
                </div>
              </div>
              {case_.payment.has_discrepancy && (
                <p className="text-xs text-amber mt-3">⚠ Fee discrepancy detected — Accounts will review.</p>
              )}
            </div>
          )}

          {/* Documents */}
          <div className="card">
            <div className="card-header">
              <h2 className="card-title flex items-center gap-2">
                <FileText size={15} className="text-gold" /> Documents ({case_.documents.length})
              </h2>
              {canUpload && (
                <button onClick={() => setShowUpload(true)} className="btn-secondary btn btn-sm">
                  <Upload size={12} /> Upload
                </button>
              )}
            </div>
            {case_.documents.length === 0 ? (
              <p className="text-sm text-muted py-4">No documents uploaded yet.</p>
            ) : (
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th>File</th><th>Size</th><th>SHA-256</th><th>Uploaded By</th><th>Date</th><th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {case_.documents.map((doc) => (
                      <DocumentRow key={doc.id} doc={doc} caseId={caseId!} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

        {/* Right: timeline */}
        <div className="col-span-1">
          <div className="card">
            <div className="card-header mb-4">
              <h2 className="card-title">Case Timeline</h2>
            </div>
            <CaseTimeline case_={case_} />
          </div>

          {/* Court Forms */}
          <div className="card mt-4">
            <h2 className="card-title mb-3">Court Forms</h2>
            {case_.selected_forms.map(({ form }) => (
              <div key={form.id} className="flex justify-between text-xs py-2 border-b border-border last:border-0">
                <span className="text-muted">{form.name}</span>
                <span className="font-mono text-ink">{formatMoney(form.fee_amount)}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {showUpload && <UploadModal caseId={caseId!} onClose={() => setShowUpload(false)} />}
    </div>
  )
}
