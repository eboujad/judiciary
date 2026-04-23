import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Bell, Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { casesApi } from '@/api/endpoints'
import { useRole } from '@/stores/authStore'

function useBreadcrumb(pathname: string): string {
  const map: Record<string, string> = {
    '/dashboard':       'Dashboard',
    '/cases':           'My Cases',
    '/cases/new':       'File New Case',
    '/accounts/queue':  'Accounts Queue',
    '/registrar/queue': 'Registrar Queue',
    '/firm':            'My Firm',
    '/profile':         'Profile',
  }
  if (map[pathname]) return map[pathname]
  if (pathname.startsWith('/cases/') && pathname.includes('/payment')) return 'Payment'
  if (pathname.startsWith('/cases/')) return 'Case Detail'
  if (pathname.startsWith('/accounts/')) return 'Accounts Review'
  if (pathname.startsWith('/registrar/')) return 'Registrar Review'
  return 'Judiciary E-Filing'
}

export function AppLayout() {
  const role     = useRole()
  const location = useLocation()
  const crumb    = useBreadcrumb(location.pathname)

  const { data: accountsData } = useQuery({
    queryKey:  ['accounts-queue-count'],
    queryFn:   () => casesApi.accountsQueue(),
    enabled:   role === 'accounts_dept' || role === 'system_admin',
    staleTime: 30000,
  })

  const { data: registrarData } = useQuery({
    queryKey:  ['registrar-queue-count'],
    queryFn:   () => casesApi.registrarQueue(),
    enabled:   role === 'registrar' || role === 'system_admin',
    staleTime: 30000,
  })

  return (
    <div className="app-layout">
      <Sidebar
        accountsQueueCount={accountsData?.data?.count}
        registrarQueueCount={registrarData?.data?.count}
      />

      {/* Top bar */}
      <header className="topbar">
        <div className="flex items-center gap-2 text-xs text-muted">
          <span>Judiciary E-Filing</span>
          <span>/</span>
          <span className="text-ink font-medium">{crumb}</span>
        </div>
        <div className="flex-1" />
        <button className="btn-ghost btn btn-sm p-2">
          <Search size={15} />
        </button>
        <button className="btn-ghost btn btn-sm p-2 relative">
          <Bell size={15} />
        </button>
      </header>

      {/* Main content */}
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
