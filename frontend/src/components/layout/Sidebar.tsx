import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, FolderOpen, FilePlus, Users, Building2,
  ClipboardCheck, BookOpen, LogOut, ChevronRight, Scale,
} from 'lucide-react'
import { clsx } from 'clsx'
import { useAuthStore, useUser, useRole } from '@/stores/authStore'
import { authApi } from '@/api/endpoints'
import toast from 'react-hot-toast'

interface NavItem {
  to: string
  label: string
  icon: React.ReactNode
  roles: string[]
  badge?: number
}

interface SidebarProps {
  accountsQueueCount?: number
  registrarQueueCount?: number
}

export function Sidebar({ accountsQueueCount, registrarQueueCount }: SidebarProps) {
  const user     = useUser()
  const role     = useRole()
  const navigate = useNavigate()
  const logout   = useAuthStore((s) => s.logout)
  const refresh  = useAuthStore((s) => s.refreshToken)

  const navItems: NavItem[] = [
    {
      to: '/dashboard', label: 'Dashboard', icon: <LayoutDashboard size={16} />,
      roles: ['lawyer', 'accounts_dept', 'registrar', 'chief_justice', 'judge', 'judge_clerk', 'system_admin'],
    },
    {
      to: '/cases', label: 'My Cases', icon: <FolderOpen size={16} />,
      roles: ['lawyer'],
    },
    {
      to: '/cases/new', label: 'File New Case', icon: <FilePlus size={16} />,
      roles: ['lawyer'],
    },
    {
      to: '/accounts/queue', label: 'Accounts Queue', icon: <ClipboardCheck size={16} />,
      roles: ['accounts_dept', 'system_admin'],
      badge: accountsQueueCount,
    },
    {
      to: '/registrar/queue', label: 'Registrar Queue', icon: <BookOpen size={16} />,
      roles: ['registrar', 'system_admin'],
      badge: registrarQueueCount,
    },
    {
      to: '/firm', label: 'My Firm', icon: <Building2 size={16} />,
      roles: ['lawyer', 'system_admin'],
    },
    {
      to: '/admin/firms', label: 'All Firms', icon: <Building2 size={16} />,
      roles: ['system_admin'],
    },
    {
      to: '/admin/users', label: 'Users', icon: <Users size={16} />,
      roles: ['system_admin'],
    },
  ]

  const visible = navItems.filter((item) => role && item.roles.includes(role))

  const handleLogout = async () => {
    try {
      if (refresh) await authApi.logout(refresh)
    } catch { /* ignore */ }
    logout()
    navigate('/login')
    toast.success('Logged out successfully.')
  }

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="w-8 h-8 bg-gold-dim border border-gold-border rounded flex items-center justify-center flex-shrink-0">
          <Scale size={16} className="text-gold" />
        </div>
        <div>
          <p className="text-xs font-semibold text-ink leading-tight">Gambia Judiciary</p>
          <p className="text-[10px] text-muted font-mono">E-Filing System</p>
        </div>
      </div>

      {/* Role pill */}
      <div className="px-4 py-3 border-b border-border">
        <span className="role-pill">
          <span className="w-1.5 h-1.5 rounded-full bg-gold" />
          {user?.full_name ?? 'Unknown'}
        </span>
        <p className="text-[10px] text-muted font-mono mt-1 ml-0.5 capitalize">
          {role?.replace('_', ' ')}
        </p>
      </div>

      {/* Nav */}
      <nav className="sidebar-nav">
        {visible.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => clsx('nav-item', isActive && 'active')}
          >
            {item.icon}
            <span className="flex-1">{item.label}</span>
            {item.badge != null && item.badge > 0 && (
              <span className="nav-badge">{item.badge}</span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-2 py-3 border-t border-border">
        <NavLink to="/profile" className="nav-item">
          <div className="w-6 h-6 rounded-full bg-gold-dim border border-gold-border flex items-center justify-center text-gold text-[10px] font-bold">
            {user?.first_name?.[0]}{user?.last_name?.[0]}
          </div>
          <span className="flex-1 truncate text-xs">{user?.email}</span>
          <ChevronRight size={12} className="text-muted" />
        </NavLink>
        <button onClick={handleLogout} className="nav-item w-full text-red/80 hover:text-red mt-1">
          <LogOut size={16} />
          <span>Log out</span>
        </button>
      </div>
    </aside>
  )
}
