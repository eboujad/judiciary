/**
 * Case creation wizard — 3 steps:
 *   1. Case details (title, court, type, description)
 *   2. Form selection (fee schedule) + total fee display
 *   3. Review & submit → goes to payment screen
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { ChevronRight, ChevronLeft, CheckSquare, Square, Info } from 'lucide-react'
import { casesApi, formsApi } from '@/api/endpoints'
import { getApiError } from '@/api/client'
import { Spinner } from '@/components/ui/Spinner'
import { formatMoney, COURT_LABEL } from '@/utils/format'
import type { CourtTier, CaseType } from '@/types'

const COURTS: { value: CourtTier; label: string }[] = [
  { value: 'cadi',       label: 'Cadi Court — Islamic personal law' },
  { value: 'magistrate', label: 'Magistrates Court — Criminal & civil (< GMD 100,000)' },
  { value: 'high',       label: 'High Court — Civil, criminal, constitutional' },
  { value: 'appeal',     label: 'Court of Appeal — Appeals from High Court' },
  { value: 'supreme',    label: 'Supreme Court — Final constitutional matters' },
]

const CASE_TYPES: { value: CaseType; label: string; courts: CourtTier[] }[] = [
  { value: 'criminal_complaint', label: 'Criminal Complaint',  courts: ['magistrate', 'high'] },
  { value: 'bail_application',   label: 'Bail Application',    courts: ['magistrate', 'high'] },
  { value: 'civil_claim',        label: 'Civil Claim',         courts: ['magistrate', 'high'] },
  { value: 'debt_recovery',      label: 'Debt Recovery',       courts: ['magistrate', 'high'] },
  { value: 'divorce',            label: 'Divorce',             courts: ['high'] },
  { value: 'custody',            label: 'Child Custody',       courts: ['high'] },
  { value: 'land_dispute',       label: 'Land Dispute',        courts: ['high'] },
  { value: 'constitutional',     label: 'Constitutional Matter',courts: ['high', 'supreme'] },
  { value: 'islamic_family',     label: 'Islamic Family Matter',courts: ['cadi'] },
  { value: 'other',              label: 'Other',               courts: ['cadi','magistrate','high','appeal','supreme'] },
]

interface Step1Data {
  title: string
  court: CourtTier
  case_type: CaseType
  description: string
  opposing_party_name: string
  relief_sought: string
}

type Step = 1 | 2 | 3

export function CaseNew() {
  const navigate         = useNavigate()
  const [step, setStep]  = useState<Step>(1)
  const [selectedForms, setSelectedForms] = useState<Set<string>>(new Set())
  const [step1Data, setStep1Data]         = useState<Step1Data | null>(null)

  const { register, handleSubmit, watch, formState: { errors } } = useForm<Step1Data>()
  const selectedCourt    = watch('court') as CourtTier | undefined
  const selectedCaseType = watch('case_type') as CaseType | undefined

  const availableTypes = CASE_TYPES.filter(
    (t) => !selectedCourt || t.courts.includes(selectedCourt)
  )

  // Fetch fee schedule for selected court
  const { data: formsData, isLoading: formsLoading } = useQuery({
    queryKey: ['court-forms', selectedCourt],
    queryFn:  () => formsApi.list(selectedCourt),
    enabled:  !!selectedCourt,
  })
  const forms = formsData?.data?.results ?? []

  const filteredForms = forms.filter(
    (f) => !selectedCaseType || !f.case_type || f.case_type === selectedCaseType
  )

  const totalFee = filteredForms
    .filter((f) => selectedForms.has(f.id))
    .reduce((sum, f) => sum + parseFloat(f.fee_amount), 0)

  const toggleForm = (id: string) => {
    setSelectedForms((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const createMutation = useMutation({
    mutationFn: (data: Step1Data) =>
      casesApi.create({ ...data, form_ids: Array.from(selectedForms) }),
    onSuccess: (res) => {
      toast.success('Case created. Proceed to payment.')
      navigate(`/cases/${res.data.id}/payment`)
    },
    onError: (err) => toast.error(getApiError(err)),
  })

  const onStep1Submit = (data: Step1Data) => {
    setStep1Data(data)
    setStep(2)
  }

  const onConfirm = () => {
    if (!step1Data) return
    if (selectedForms.size === 0) {
      toast.error('Please select at least one court form.')
      return
    }
    createMutation.mutate(step1Data)
  }

  const stepLabel = ['Case Details', 'Select Forms & Fees', 'Review & Create']

  return (
    <div className="page-container max-w-2xl">
      <h1 className="page-title">File New Case</h1>
      <p className="page-subtitle">Complete all steps to create your case and proceed to payment.</p>

      {/* Step indicators */}
      <div className="flex items-center gap-2 mb-8">
        {([1, 2, 3] as Step[]).map((s) => (
          <div key={s} className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-mono font-bold
              ${step >= s ? 'bg-gold text-bg' : 'bg-surface2 text-muted border border-border'}`}>
              {s}
            </div>
            <span className={`text-xs ${step === s ? 'text-ink' : 'text-muted'}`}>{stepLabel[s - 1]}</span>
            {s < 3 && <ChevronRight size={12} className="text-muted" />}
          </div>
        ))}
      </div>

      {/* ── STEP 1: Case details ── */}
      {step === 1 && (
        <div className="card">
          <form onSubmit={handleSubmit(onStep1Submit)}>
            <div className="form-group">
              <label className="form-label">Case Title *</label>
              <input className="form-input" placeholder="e.g. Ndure v. Ceesay"
                {...register('title', { required: 'Title is required', minLength: { value: 5, message: 'Too short' } })} />
              {errors.title && <span className="form-error">{errors.title.message}</span>}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="form-group">
                <label className="form-label">Court Tier *</label>
                <select className="form-select"
                  {...register('court', { required: 'Court is required' })}>
                  <option value="">Select court…</option>
                  {COURTS.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                </select>
                {errors.court && <span className="form-error">{errors.court.message}</span>}
              </div>

              <div className="form-group">
                <label className="form-label">Case Type *</label>
                <select className="form-select"
                  {...register('case_type', { required: 'Case type is required' })}>
                  <option value="">Select type…</option>
                  {availableTypes.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
                {errors.case_type && <span className="form-error">{errors.case_type.message}</span>}
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Opposing Party / Respondent</label>
              <input className="form-input" placeholder="Full name"
                {...register('opposing_party_name')} />
            </div>

            <div className="form-group">
              <label className="form-label">Brief Facts</label>
              <textarea className="form-textarea" rows={3}
                placeholder="Summarise the facts of the case…"
                {...register('description')} />
            </div>

            <div className="form-group">
              <label className="form-label">Relief Sought</label>
              <textarea className="form-textarea" rows={2}
                placeholder="What outcome are you seeking?"
                {...register('relief_sought')} />
            </div>

            <div className="flex justify-end mt-2">
              <button type="submit" className="btn-primary btn">
                Next — Select Forms <ChevronRight size={15} />
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── STEP 2: Form selection ── */}
      {step === 2 && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Court Forms & Fees</h2>
            <span className="text-xs text-muted">{COURT_LABEL[selectedCourt!]}</span>
          </div>

          {formsLoading ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : filteredForms.length === 0 ? (
            <p className="text-sm text-muted py-4">No forms available for this court/type combination.</p>
          ) : (
            <div className="space-y-2 mb-4">
              {filteredForms.map((form) => {
                const checked = selectedForms.has(form.id)
                return (
                  <button key={form.id} type="button" onClick={() => toggleForm(form.id)}
                    className={`w-full text-left p-3 rounded border transition-colors
                      ${checked
                        ? 'border-gold-border bg-gold-dim'
                        : 'border-border bg-surface2 hover:border-border2'}`}>
                    <div className="flex items-start gap-3">
                      {checked
                        ? <CheckSquare size={16} className="text-gold mt-0.5 flex-shrink-0" />
                        : <Square size={16} className="text-muted mt-0.5 flex-shrink-0" />}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-ink">{form.name}</p>
                        {form.description && (
                          <p className="text-xs text-muted mt-0.5">{form.description}</p>
                        )}
                      </div>
                      <span className="text-sm font-mono text-gold font-semibold flex-shrink-0">
                        {formatMoney(form.fee_amount)}
                      </span>
                    </div>
                  </button>
                )
              })}
            </div>
          )}

          {/* Fee total */}
          <div className="flex items-center justify-between p-3 bg-gold-dim border border-gold-border rounded-lg mb-4">
            <span className="text-sm text-muted">Total court fees due</span>
            <span className="text-lg font-bold font-mono text-gold">{formatMoney(totalFee)}</span>
          </div>

          <div className="flex items-center gap-2 p-3 bg-blue-dim border border-blue/20 rounded-lg mb-6">
            <Info size={14} className="text-blue flex-shrink-0" />
            <p className="text-xs text-muted">
              Payment is made via MUSU mobile money. You will be prompted to pay after creating the case.
            </p>
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep(1)} className="btn-secondary btn">
              <ChevronLeft size={15} /> Back
            </button>
            <button
              onClick={() => selectedForms.size > 0 ? setStep(3) : toast.error('Select at least one form.')}
              className="btn-primary btn"
            >
              Review Case <ChevronRight size={15} />
            </button>
          </div>
        </div>
      )}

      {/* ── STEP 3: Review ── */}
      {step === 3 && step1Data && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Review & Confirm</h2>
          </div>

          <div className="space-y-3 mb-6 text-sm">
            <div className="flex justify-between py-2 border-b border-border">
              <span className="text-muted">Title</span>
              <span className="text-ink font-medium">{step1Data.title}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-border">
              <span className="text-muted">Court</span>
              <span className="text-ink">{COURT_LABEL[step1Data.court]}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-border">
              <span className="text-muted">Case Type</span>
              <span className="text-ink capitalize">{step1Data.case_type.replace('_', ' ')}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-border">
              <span className="text-muted">Opposing Party</span>
              <span className="text-ink">{step1Data.opposing_party_name || '—'}</span>
            </div>
            <div className="py-2 border-b border-border">
              <span className="text-muted block mb-1">Selected Forms ({selectedForms.size})</span>
              {filteredForms.filter((f) => selectedForms.has(f.id)).map((f) => (
                <div key={f.id} className="flex justify-between text-xs py-1">
                  <span className="text-muted">{f.name}</span>
                  <span className="font-mono text-ink">{formatMoney(f.fee_amount)}</span>
                </div>
              ))}
            </div>
            <div className="flex justify-between py-2 font-semibold">
              <span className="text-muted">Total Payable</span>
              <span className="text-gold font-mono text-base">{formatMoney(totalFee)}</span>
            </div>
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep(2)} className="btn-secondary btn">
              <ChevronLeft size={15} /> Back
            </button>
            <button
              onClick={onConfirm}
              disabled={createMutation.isPending}
              className="btn-primary btn"
            >
              {createMutation.isPending ? <Spinner size="sm" /> : 'Create Case & Pay'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
