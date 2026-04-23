import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { BookOpen } from 'lucide-react'
import { casesApi } from '@/api/endpoints'
import { CaseStatusBadge } from '@/components/ui/StatusBadge'
import { PageLoader } from '@/components/ui/Spinner'
import { formatDateTime, COURT_LABEL } from '@/utils/format'

export function RegistrarQueue() {
  const { data, isLoading } = useQuery({
    queryKey: ['registrar-queue'],
    queryFn:  () => casesApi.registrarQueue(),
    refetchInterval: 30000,
  })

  const cases = data?.data?.results ?? []
  if (isLoading) return <PageLoader />

  return (
    <div className="page-container">
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="page-title flex items-center gap-2">
            <BookOpen size={20} className="text-gold" /> Registrar Queue
          </h1>
          <p className="page-subtitle">
            Cases verified by Accounts awaiting official registration or rejection.
          </p>
        </div>
        <span className="text-2xl font-bold font-mono text-gold">{cases.length}</span>
      </div>

      {cases.length === 0 ? (
        <div className="card empty-state">
          <BookOpen size={40} className="text-muted/40 mb-4" />
          <p className="empty-state-title">Queue is empty</p>
          <p className="empty-state-desc">No cases are awaiting registration.</p>
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
                  <th>Type</th>
                  <th>Forwarded</th>
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
                    <td className="text-muted text-xs capitalize">{c.case_type.replace('_',' ')}</td>
                    <td className="text-muted text-xs">{formatDateTime(c.submitted_at)}</td>
                    <td><CaseStatusBadge status={c.status} /></td>
                    <td>
                      <Link to={`/registrar/review/${c.id}`} className="btn-primary btn btn-sm">
                        Review
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
