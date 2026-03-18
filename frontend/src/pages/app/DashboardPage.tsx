import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts'
import { toast } from 'sonner'
import { AlertTriangle, BarChart2, DollarSign, Receipt } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  getTransactionsApi,
  getOpenAlertsApi,
  getLatestAnalysisApi,
  acknowledgeAlertApi,
  type Alert,
} from '@/api/dashboard'

// ─── helpers ────────────────────────────────────────────────────────────────

function isoDate(date: Date): string {
  return date.toISOString().split('T')[0]
}

function formatUSD(value: string | number): string {
  const n = typeof value === 'string' ? parseFloat(value) : value
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}

function relativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(ms / 60_000)
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function shortMonth(yearMonth: string): string {
  const [y, m] = yearMonth.split('-')
  return new Date(Number(y), Number(m) - 1).toLocaleString('en-US', {
    month: 'short',
    year: '2-digit',
  })
}

// ─── severity ───────────────────────────────────────────────────────────────

const SEVERITY_COLOR: Record<Alert['severity'], string> = {
  HIGH: '#ef4444',
  MEDIUM: '#f59e0b',
  LOW: '#3b82f6',
}

const SEVERITY_CLASS: Record<Alert['severity'], string> = {
  HIGH: 'bg-red-100 text-red-700 border-red-200',
  MEDIUM: 'bg-amber-100 text-amber-700 border-amber-200',
  LOW: 'bg-blue-100 text-blue-700 border-blue-200',
}

function SeverityBadge({ severity }: { severity: Alert['severity'] }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${SEVERITY_CLASS[severity]}`}
    >
      {severity}
    </span>
  )
}

// ─── stat card ───────────────────────────────────────────────────────────────

interface StatCardProps {
  icon: React.ElementType
  label: string
  value: string
  isLoading: boolean
  isError?: boolean
}

function StatCard({ icon: Icon, label, value, isLoading, isError }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <Icon className="size-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-8 w-28" />
        ) : isError ? (
          <div className="text-sm text-destructive">Failed to load</div>
        ) : (
          <div className="text-2xl font-bold">{value}</div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── page ────────────────────────────────────────────────────────────────────

export function DashboardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { thirtyDaysAgo, sixMonthsAgo } = useMemo(() => {
    const now = new Date()
    const thirtyDaysAgo = new Date(now)
    thirtyDaysAgo.setDate(now.getDate() - 30)
    const sixMonthsAgo = new Date(now)
    sixMonthsAgo.setMonth(now.getMonth() - 6)
    return { thirtyDaysAgo, sixMonthsAgo }
  }, [])

  // ── queries ──────────────────────────────────────────────────────────────

  const { data: txn30d, isLoading: loadingTxn30d, isError: errorTxn30d } = useQuery({
    queryKey: ['dashboard', 'transactions30d'],
    queryFn: () =>
      getTransactionsApi({
        date_from: isoDate(thirtyDaysAgo),
        page_size: '500',
      }).then((r) => r.data),
  })

  const { data: txn6m, isLoading: loadingTxn6m, isError: errorTxn6m } = useQuery({
    queryKey: ['dashboard', 'transactions6m'],
    queryFn: () =>
      getTransactionsApi({
        date_from: isoDate(sixMonthsAgo),
        page_size: '500',
      }).then((r) => r.data),
  })

  const { data: openAlertsData, isLoading: loadingAlerts, isError: errorAlerts } = useQuery({
    queryKey: ['dashboard', 'openAlerts'],
    queryFn: () => getOpenAlertsApi(100).then((r) => r.data),
  })

  const { data: analysisData, isLoading: loadingAnalysis, isError: errorAnalysis } = useQuery({
    queryKey: ['dashboard', 'latestAnalysis'],
    queryFn: () => getLatestAnalysisApi().then((r) => r.data),
  })

  // ── mutations ────────────────────────────────────────────────────────────

  const { mutate: acknowledge, isPending: acknowledging } = useMutation({
    mutationFn: (id: string) => acknowledgeAlertApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'openAlerts'] })
      toast.success('Alert acknowledged')
    },
    onError: () => toast.error('Failed to acknowledge alert'),
  })

  // ── derived data ─────────────────────────────────────────────────────────

  const totalTransactions = txn30d?.count ?? 0

  const totalSpend = useMemo(
    () => txn30d?.results.reduce((sum, t) => sum + parseFloat(t.amount), 0) ?? 0,
    [txn30d],
  )

  const openAlertsCount = openAlertsData?.count ?? 0
  const latestRun = analysisData?.results[0]

  const spendChartData = useMemo(() => {
    if (!txn6m?.results.length) return []
    const map = new Map<string, number>()
    for (const t of txn6m.results) {
      const d = new Date(t.date)
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
      map.set(key, (map.get(key) ?? 0) + parseFloat(t.amount))
    }
    return Array.from(map.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([month, total]) => ({ month: shortMonth(month), total }))
  }, [txn6m])

  const donutData = useMemo(() => {
    if (!openAlertsData?.results.length) return []
    const counts: Partial<Record<Alert['severity'], number>> = {}
    for (const a of openAlertsData.results) {
      counts[a.severity] = (counts[a.severity] ?? 0) + 1
    }
    return (['HIGH', 'MEDIUM', 'LOW'] as const)
      .filter((s) => (counts[s] ?? 0) > 0)
      .map((s) => ({ name: s, value: counts[s]!, color: SEVERITY_COLOR[s] }))
  }, [openAlertsData])

  const recentAlerts = openAlertsData?.results.slice(0, 5) ?? []

  // ── render ───────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Financial health at a glance</p>
        </div>
      </div>

      {/* Row 1 — Stat Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard
          icon={Receipt}
          label="Total Transactions (30d)"
          value={totalTransactions.toLocaleString()}
          isLoading={loadingTxn30d}
          isError={errorTxn30d}
        />
        <StatCard
          icon={DollarSign}
          label="Total Spend (30d)"
          value={formatUSD(totalSpend)}
          isLoading={loadingTxn30d}
          isError={errorTxn30d}
        />
        <StatCard
          icon={AlertTriangle}
          label="Open Alerts"
          value={openAlertsCount.toLocaleString()}
          isLoading={loadingAlerts}
          isError={errorAlerts}
        />
        <StatCard
          icon={BarChart2}
          label="Last Analysis"
          value={
            latestRun
              ? relativeTime(latestRun.run_time ?? latestRun.created_at)
              : '—'
          }
          isLoading={loadingAnalysis}
          isError={errorAnalysis}
        />
      </div>

      {/* Row 2 — Charts */}
      <div className="grid grid-cols-3 gap-4">
        {/* Spend Over Time (2/3 width) */}
        <Card className="col-span-2">
          <CardHeader>
            <CardTitle className="text-sm font-medium">Spend Over Time</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingTxn6m ? (
              <Skeleton className="h-48 w-full" />
            ) : errorTxn6m ? (
              <div className="flex h-48 items-center justify-center text-sm text-destructive">
                Failed to load transaction data
              </div>
            ) : spendChartData.length === 0 ? (
              <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                No transaction data for the last 6 months
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={spendChartData} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis
                    tick={{ fontSize: 12 }}
                    tickFormatter={(v: number) =>
                      v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`
                    }
                    width={56}
                  />
                  <Tooltip
                    formatter={(value) => [formatUSD(Number(value)), 'Spend']}
                    contentStyle={{ fontSize: 12 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="total"
                    stroke="hsl(var(--primary))"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Open Alerts Donut (1/3 width) */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Alerts by Severity</CardTitle>
          </CardHeader>
          <CardContent>
            {loadingAlerts ? (
              <Skeleton className="h-48 w-full" />
            ) : errorAlerts ? (
              <div className="flex h-48 items-center justify-center text-sm text-destructive">
                Failed to load alerts
              </div>
            ) : donutData.length === 0 ? (
              <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                No open alerts
              </div>
            ) : (
              <div>
                <div className="relative">
                  <ResponsiveContainer width="100%" height={160}>
                    <PieChart>
                      <Pie
                        data={donutData}
                        cx="50%"
                        cy="50%"
                        innerRadius={48}
                        outerRadius={72}
                        dataKey="value"
                        strokeWidth={0}
                      >
                        {donutData.map((entry) => (
                          <Cell
                            key={entry.name}
                            fill={entry.color}
                            className="cursor-pointer opacity-90 hover:opacity-100"
                            onClick={() => navigate(`/alerts?severity=${entry.name}`)}
                          />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ fontSize: 12 }} />
                    </PieChart>
                  </ResponsiveContainer>
                  {/* Center count label */}
                  <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-2xl font-bold">{openAlertsCount}</span>
                    <span className="text-xs text-muted-foreground">open</span>
                  </div>
                </div>
                {/* Legend */}
                <div className="mt-2 flex flex-wrap justify-center gap-3">
                  {donutData.map((d) => (
                    <button
                      key={d.name}
                      className="flex items-center gap-1.5 text-xs hover:opacity-80"
                      onClick={() => navigate(`/alerts?severity=${d.name}`)}
                    >
                      <span
                        className="inline-block size-2 rounded-full"
                        style={{ backgroundColor: d.color }}
                      />
                      {d.name} ({d.value})
                    </button>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 3 — Recent Open Alerts */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-sm font-medium">Recent Open Alerts</CardTitle>
          <button
            className="text-xs text-primary underline-offset-4 hover:underline"
            onClick={() => navigate('/alerts')}
          >
            View all
          </button>
        </CardHeader>
        <CardContent>
          {loadingAlerts ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : errorAlerts ? (
            <p className="py-6 text-center text-sm text-destructive">
              Failed to load alerts. Please try refreshing the page.
            </p>
          ) : recentAlerts.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">
              No open alerts. Run an analysis to detect issues.
            </p>
          ) : (
            <div className="divide-y">
              {recentAlerts.map((alert) => (
                <div key={alert.id} className="flex items-start gap-3 py-3">
                  <div className="mt-0.5 shrink-0">
                    <SeverityBadge severity={alert.severity} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      {alert.alert_type}
                    </p>
                    <p className="line-clamp-2 text-sm">{alert.message}</p>
                  </div>
                  <div className="shrink-0 text-right">
                    <p className="text-xs text-muted-foreground">{relativeTime(alert.created_at)}</p>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="mt-1 h-6 px-2 text-xs"
                      disabled={acknowledging}
                      onClick={() => acknowledge(alert.id)}
                    >
                      Acknowledge
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
