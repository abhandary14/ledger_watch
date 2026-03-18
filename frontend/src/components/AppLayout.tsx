import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  BarChart2,
  BookOpen,
  Building2,
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  LogOut,
  ArrowLeftRight,
  Settings,
  Users,
} from 'lucide-react'
import { useAuth } from '@/hooks/use-auth'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [collapsed, setCollapsed] = useState(false)

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  const navItems = [
    { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/transactions', icon: ArrowLeftRight, label: 'Transactions' },
    { to: '/analysis', icon: BarChart2, label: 'Analysis' },
    { to: '/alerts', icon: AlertCircle, label: 'Alerts' },
    { to: '/settings', icon: Settings, label: 'Settings' },
    ...(user?.role === 'owner'
      ? [{ to: '/manage-org', icon: Building2, label: 'Manage Org' }]
      : [{ to: '/org-directory', icon: Users, label: 'See Organization' }]),
  ]

  return (
    <div className="flex h-screen bg-background">
      <aside
        className={cn(
          'relative flex flex-col border-r bg-sidebar transition-[width] duration-200',
          collapsed ? 'w-14' : 'w-60',
        )}
      >
        {/* Brand */}
        <div
          className={cn(
            'flex h-16 cursor-pointer items-center border-b transition-all',
            collapsed ? 'justify-center px-3' : 'justify-start px-5',
          )}
          onClick={() => navigate('/dashboard')}
          title="Go to Dashboard"
        >
          <div className="flex items-center gap-2">
            <div className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary">
              <span className="text-xs font-bold text-primary-foreground">LW</span>
            </div>
            {!collapsed && (
              <span className="font-semibold text-sidebar-foreground">LedgerWatch</span>
            )}
          </div>
        </div>

        {/* Org name */}
        {user && !collapsed && (
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
        <nav className="flex flex-col flex-1 px-2 py-4">
          <div className="flex-1 space-y-0.5">
            {navItems.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                title={label}
                aria-label={label}
                className={({ isActive }) =>
                  cn(
                    'flex items-center gap-3 rounded-lg px-2 py-2 text-sm transition-colors',
                    collapsed ? 'justify-center' : 'justify-start px-3',
                    isActive
                      ? 'bg-sidebar-primary text-sidebar-primary-foreground font-medium'
                      : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                  )
                }
              >
                <Icon className="size-4 shrink-0" />
                {!collapsed && <span>{label}</span>}
              </NavLink>
            ))}
          </div>

          {/* Docs link — pinned to bottom of nav */}
          <NavLink
            to="/docs"
            title="Documentation"
            aria-label="Documentation"
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-lg px-2 py-2 text-sm transition-colors',
                collapsed ? 'justify-center' : 'justify-start px-3',
                isActive
                  ? 'bg-sidebar-primary text-sidebar-primary-foreground font-medium'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
              )
            }
          >
            <BookOpen className="size-4 shrink-0" />
            {!collapsed && <span>Documentation</span>}
          </NavLink>
        </nav>

        {/* User + Logout */}
        <div className={cn('border-t', collapsed ? 'p-2' : 'p-4')}>
          {user && !collapsed && (
            <p className="mb-3 truncate text-sm text-sidebar-foreground/70">{user.email}</p>
          )}
          <Button
            variant="ghost"
            size="sm"
            title="Sign out"
            className={cn(
              'w-full text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
              collapsed ? 'justify-center' : 'justify-start',
            )}
            onClick={handleLogout}
          >
            <LogOut className="size-4 shrink-0" />
            {!collapsed && <span>Sign out</span>}
          </Button>
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed((c) => !c)}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          className="absolute -right-3 top-[4.5rem] flex size-6 items-center justify-center rounded-full border bg-background text-muted-foreground shadow-sm hover:bg-accent hover:text-accent-foreground"
        >
          {collapsed ? <ChevronRight className="size-3.5" /> : <ChevronLeft className="size-3.5" />}
        </button>
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
