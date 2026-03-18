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
      {/* Sidebar — icon-only on <md, full labels on md+ */}
      <aside className="flex w-14 flex-col border-r bg-sidebar md:w-60">
        {/* Brand */}
        <div className="flex h-16 items-center justify-center border-b px-3 md:justify-start md:px-5">
          <div className="flex items-center gap-2">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary">
              <span className="text-xs font-bold text-primary-foreground">LW</span>
            </div>
            <span className="hidden font-semibold text-sidebar-foreground md:block">
              LedgerWatch
            </span>
          </div>
        </div>

        {/* Org name — hidden on icon-only width */}
        {user && (
          <div className="hidden border-b px-5 py-3 md:block">
            <p className="text-xs font-medium uppercase tracking-wider text-sidebar-foreground/50">
              Organization
            </p>
            <p className="truncate text-sm font-medium text-sidebar-foreground">
              {user.organization.name}
            </p>
          </div>
        )}

        {/* Navigation */}
        <nav className="flex-1 space-y-0.5 px-2 py-4 md:px-3">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              title={label}
              aria-label={label}
              className={({ isActive }) =>
                cn(
                  'flex items-center justify-center gap-3 rounded-lg px-2 py-2 text-sm transition-colors md:justify-start md:px-3',
                  isActive
                    ? 'bg-sidebar-primary text-sidebar-primary-foreground font-medium'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                )
              }
            >
              <Icon className="size-4 shrink-0" />
              <span className="hidden md:block">{label}</span>
            </NavLink>
          ))}
        </nav>

        {/* User + Logout */}
        <div className="border-t p-2 md:p-4">
          {user && (
            <p className="mb-3 hidden truncate text-sm text-sidebar-foreground/70 md:block">
              {user.email}
            </p>
          )}
          <Button
            variant="ghost"
            size="sm"
            title="Sign out"
            className="w-full justify-center text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground md:justify-start"
            onClick={handleLogout}
          >
            <LogOut className="size-4 shrink-0" />
            <span className="hidden md:block">Sign out</span>
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        <div className="p-4 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
