/**
 * MUSU Payment Screen.
 * - Fetches case + payment data
 * - Lets user enter their MUSU-registered phone number
 * - Initiates payment → MUSU returns a payment URL (real) or mock reference (dev)
 * - In dev: "Confirm Payment" button simulates the MUSU callback
 */
import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import toast from 'react-hot-toast'
import { CreditCard, CheckCircle2, Phone, AlertCircle, ArrowLeft } from 'lucide-react'
import { casesApi, paymentsApi } from '@/api/endpoints'
import { getApiError } from '@/api/client'
import { PageLoader, Spinner } from '@/components/ui/Spinner'
import { PaymentStatusBadge } from '@/components/ui/StatusBadge'
import { formatMoney, formatDateTime } from '@/utils/format'

interface PhoneForm { payer_phone: string }

export function PaymentScreen() {
  const { caseId }    = useParams<{ caseId: string }>()
  const navigate      = useNavigate()
  const qc            = useQueryClient()
  const [paymentUrl, setPaymentUrl] = useState<string | null>(null)
  const [musuRef, setMusuRef]       = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors } } = useForm<PhoneForm>({
    defaultValues: { payer_phone: '+220' },
  })

  const { data: caseData, isLoading: caseLoading } = useQuery({
    queryKey: ['case', caseId],
    queryFn:  () => casesApi.get(caseId!),
    enabled:  !!caseId,
  })
  const case_ = caseData?.data

  const { data: paymentData, refetch: refetchPayment } = useQuery({
    queryKey: ['payment', caseId],
    queryFn:  () => paymentsApi.get(caseId!),
    enabled:  !!caseId,
    refetchInterval: (query) =>
      query.state.data?.data?.status === 'initiated' ? 3000 : false,
  })
  const payment = paymentData?.data

  const initiateMutation = useMutation({
    mutationFn: (phone: string) => paymentsApi.initiate(caseId!, phone),
    onSuccess: (res) => {
      setPaymentUrl(res.data.payment_url)
      setMusuRef(res.data.payment.musu_reference)
      toast.success('Payment initiated. Complete payment on MUSU.')
      refetchPayment()
    },
    onError: (err) => toast.error(getApiError(err)),
  })

  const confirmMutation = useMutation({
    mutationFn: () => paymentsApi.mockConfirm(musuRef!),
    onSuccess: () => {
      toast.success('Payment confirmed! Case submitted.')
      qc.invalidateQueries({ queryKey: ['case', caseId] })
      qc.invalidateQueries({ queryKey: ['payment', caseId] })
      qc.invalidateQueries({ queryKey: ['my-cases'] })
      setTimeout(() => navigate(`/cases/${caseId}`), 1500)
    },
    onError: (err) => toast.error(getApiError(err)),
  })

  if (caseLoading) return <PageLoader />
  if (!case_) return <p className="p-6 text-muted">Case not found.</p>

  const isConfirmed = payment?.status === 'confirmed'
  const isInitiated = payment?.status === 'initiated'

  return (
    <div className="page-container max-w-lg">
      <Link to={`/cases/${caseId}`} className="btn-ghost btn btn-sm mb-4">
        <ArrowLeft size={14} /> Back to Case
      </Link>

      <h1 className="page-title">Court Filing Fee Payment</h1>
      <p className="page-subtitle">Pay via MUSU mobile money to submit your case.</p>

      {/* Case summary */}
      <div className="card mb-4">
        <div className="text-sm space-y-2">
          <div className="flex justify-between">
            <span className="text-muted">Case</span>
            <span className="text-ink font-medium">{case_.title}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted">Court</span>
            <span className="text-ink capitalize">{case_.court}</span>
          </div>
          {case_.selected_forms.map(({ form }) => (
            <div key={form.id} className="flex justify-between text-xs">
              <span className="text-muted">{form.name}</span>
              <span className="font-mono">{formatMoney(form.fee_amount)}</span>
            </div>
          ))}
          <div className="divider" />
          <div className="flex justify-between font-semibold">
            <span className="text-muted">Total Due</span>
            <span className="text-gold font-mono text-lg">
              {formatMoney(payment?.amount_due ?? case_.payment?.amount_due ?? 0)}
            </span>
          </div>
        </div>
      </div>

      {/* Payment status */}
      {payment && (
        <div className="mb-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs text-muted">Payment status:</span>
            <PaymentStatusBadge status={payment.status} />
          </div>
          {payment.musu_reference && (
            <p className="text-xs text-muted font-mono">Ref: {payment.musu_reference}</p>
          )}
          {payment.confirmed_at && (
            <p className="text-xs text-green mt-1">
              Confirmed {formatDateTime(payment.confirmed_at)} — Receipt {payment.receipt_number}
            </p>
          )}
        </div>
      )}

      {/* Confirmed state */}
      {isConfirmed ? (
        <div className="card border-green/20 bg-green-dim">
          <div className="flex items-center gap-3">
            <CheckCircle2 size={24} className="text-green" />
            <div>
              <p className="text-sm font-medium text-ink">Payment Confirmed</p>
              <p className="text-xs text-muted">Your case has been submitted to the Accounts Department queue.</p>
            </div>
          </div>
          <Link to={`/cases/${caseId}`} className="btn-primary btn mt-4 w-full justify-center">
            View Case Timeline
          </Link>
        </div>
      ) : isInitiated && musuRef ? (
        /* Initiated — show confirm button (dev) or payment URL (prod) */
        <div className="card">
          <div className="flex items-center gap-2 mb-4 p-3 bg-amber-dim border border-amber/20 rounded-lg">
            <AlertCircle size={14} className="text-amber flex-shrink-0" />
            <p className="text-xs text-muted">
              Open MUSU on your phone and complete the payment.
              This page will auto-update when payment is received.
            </p>
          </div>

          {paymentUrl && (
            <a href={paymentUrl} target="_blank" rel="noopener noreferrer"
              className="btn-primary btn w-full justify-center mb-3">
              <CreditCard size={15} /> Open MUSU Payment Page
            </a>
          )}

          {/* DEV ONLY mock confirm */}
          <div className="divider" />
          <p className="text-xs text-muted text-center mb-3">Development mode — skip MUSU</p>
          <button
            onClick={() => confirmMutation.mutate()}
            disabled={confirmMutation.isPending}
            className="btn-secondary btn w-full justify-center"
          >
            {confirmMutation.isPending ? <Spinner size="sm" /> : '⚡ Simulate Payment Confirmation'}
          </button>
        </div>
      ) : (
        /* Not yet initiated — phone entry form */
        <div className="card">
          <div className="card-header">
            <h2 className="card-title flex items-center gap-2">
              <CreditCard size={16} className="text-gold" /> Pay via MUSU
            </h2>
          </div>

          <form onSubmit={handleSubmit((d) => initiateMutation.mutate(d.payer_phone))}>
            <div className="form-group">
              <label className="form-label">MUSU-registered phone number</label>
              <div className="relative">
                <Phone size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
                <input
                  className="form-input pl-9"
                  placeholder="+220 7001234"
                  {...register('payer_phone', {
                    required: 'Phone number is required',
                    pattern: {
                      value: /^\+\d{7,15}$/,
                      message: 'Use E.164 format: +220XXXXXXX',
                    },
                  })}
                />
              </div>
              {errors.payer_phone && <span className="form-error">{errors.payer_phone.message}</span>}
              <span className="form-hint">You will receive a MUSU prompt to approve the payment.</span>
            </div>

            <button
              type="submit"
              disabled={initiateMutation.isPending}
              className="btn-primary btn w-full justify-center"
            >
              {initiateMutation.isPending ? <Spinner size="sm" /> : (
                <><CreditCard size={15} /> Initiate MUSU Payment</>
              )}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}
