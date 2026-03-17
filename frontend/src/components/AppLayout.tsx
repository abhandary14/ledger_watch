import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  BarChart2,
  LayoutDashboard,
  LogOut,
  ArrowLeftRight,
  Settings,
} from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/transactions', icon: ArrowLeftRight, label: 'Transactions' },
  { to: '/analysis', icon: BarChart2, label: 'Analysis' },
  { to: '/alerts', icon: AlertCircle, label: 'Alerts' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <aside className="flex w-60 flex-col border-r bg-sidebar">
        {/* Brand */}
        <div className="flex h-16 items-center border-b px-5">
          <div className="flex items-center gap-2">
            <div className="flex size-7 items-center justify-center rounded-lg bg-primary">
              <span className="text-xs font-bold text-primary-foreground">LW</span>
            </div>
            <span className="font-semibold text-sidebar-foreground">LedgerWatch</span>
          </div>
        </div>

        {/* Org name */}
        {user && (
          <div className="border-b px-5 py-3">
            <p className="text-xs font-medium uppercase tracking-wider text-sidebar-foreground/50">
              Organization
            </p>
            <p className="truncate text-sm font-medium text-sidebar-foreground">
              {user.organization.name}
            </p>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 space-y-0.5 px-3 py-4">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-sidebar-primary text-sidebar-primary-foreground font-medium'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                )
              }
            >
              <Icon className="size-4 shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User + Logout */}
        <div className="border-t p-4">
          {user && (
            <p className="mb-3 truncate text-sm text-sidebar-foreground/70">{user.email}</p>
          )}
          <Button
            variant="ghost"
            size="sm"
            className="w-full justify-start text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
            onClick={handleLogout}
          >
            <LogOut className="size-4" />
            Sign out
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
