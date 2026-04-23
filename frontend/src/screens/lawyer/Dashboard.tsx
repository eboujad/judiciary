import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { FilePlus, FolderOpen, Clock, CheckCircle2, XCircle, AlertCircle } from 'lucide-react'
import { casesApi } from '@/api/endpoints'
import { CaseStatusBadge } from '@/components/ui/StatusBadge'
import { PageLoader } from '@/components/ui/Spinner'
import { formatDate, formatMoney, COURT_LABEL } from '@/utils/format'
import { useUser } from '@/stores/authStore'
import type { CaseListItem } from '@/types'

function StatCard({ label, value, icon, color }: {
  label: string; value: number; icon: React.ReactNode; color: string
}) {
  return (
    <div className="stat-card">
      <div className="flex items-start justify-between">
        <div>
          <p className="stat-value">{value}</p>
          <p className="stat-label">{label}</p>
        </div>
        <div className={`p-2 rounded-lg ${color}`}>{icon}</div>
      </div>
    </div>
  )
}

function CaseRow({ c }: { c: CaseListItem }) {
  return (
    <tr>
      <td>
        <Link to={`/cases/${c.id}`} className="text-gold hover:text-amber font-mono text-xs">
          {c.case_number ?? `DRAFT-${c.id.slice(0, 8).toUpperCase()}`}
        </Link>
      </td>
      <td>
        <Link to={`/cases/${c.id}`} className="text-ink hover:text-gold">
          {c.title}
        </Link>
      </td>
      <td className="text-muted text-xs">{COURT_LABEL[c.court]}</td>
      <td><CaseStatusBadge status={c.status} /></td>
      <td className="text-muted text-xs font-mono">{formatDate(c.created_at)}</td>
      <td>
        {c.total_fee ? (
          <span className="text-xs font-mono text-ink">{formatMoney(c.total_fee)}</span>
        ) : '—'}
      </td>
    </tr>
  )
}

export function LawyerDashboard() {
  const user = useUser()
  const { data, isLoading } = useQuery({
    queryKey: ['my-cases'],
    queryFn:  () => casesApi.list(),
  })

  if (isLoading) return <PageLoader />

  const cases  = data?.data?.results ?? []
  const counts = {
    draft:    cases.filter((c) => c.status === 'draft').length,
    pending:  cases.filter((c) => ['pending_accounts', 'pending_registrar', 'resubmitted'].includes(c.status)).length,
    registered: cases.filter((c) => c.status === 'registered').length,
    rejected: cases.filter((c) => c.status === 'rejected').length,
  }

  return (
    <div className="page-container">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="page-title">Good morning, {user?.first_name}.</h1>
          <p className="page-subtitle">Here's an overview of your cases.</p>
        </div>
        <Link to="/cases/new" className="btn-primary btn">
          <FilePlus size={15} />
          File New Case
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Draft" value={counts.draft}
          icon={<Clock size={16} className="text-muted" />} color="bg-surface2" />
        <StatCard label="Under Review" value={counts.pending}
          icon={<AlertCircle size={16} className="text-amber" />} color="bg-amber-dim" />
        <StatCard label="Registered" value={counts.registered}
          icon={<CheckCircle2 size={16} className="text-green" />} color="bg-green-dim" />
        <StatCard label="Rejected" value={counts.rejected}
          icon={<XCircle size={16} className="text-red" />} color="bg-red-dim" />
      </div>

      {/* Cases table */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title flex items-center gap-2">
            <FolderOpen size={16} className="text-gold" /> My Cases
          </h2>
          <Link to="/cases" className="btn-ghost btn btn-sm">View all</Link>
        </div>

        {cases.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon"><FolderOpen size={40} /></div>
            <p className="empty-state-title">No cases yet</p>
            <p className="empty-state-desc">File your first case to get started.</p>
            <Link to="/cases/new" className="btn-primary btn mt-4">
              <FilePlus size={15} /> File New Case
            </Link>
          </div>
        ) : (
          <div className="table-container">
            <table className="table">
              <thead>
                <tr>
                  <th>Reference</th>
                  <th>Title</th>
                  <th>Court</th>
                  <th>Status</th>
                  <th>Filed</th>
                  <th>Fee</th>
                </tr>
              </thead>
              <tbody>
                {cases.slice(0, 10).map((c) => <CaseRow key={c.id} c={c} />)}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
