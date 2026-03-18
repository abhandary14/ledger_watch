import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  AreaChart,
  Area,
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
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'
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

function formatDateAxis(dateStr: string, range: ChartRange): string {
  const d = new Date(dateStr + 'T12:00:00') // noon avoids UTC-midnight timezone shift
  if (range === '5Y') {
    return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
  }
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
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

type ChartRange = '1M' | '6M' | 'YTD' | '1Y' | '5Y' | 'CUSTOM'
const CHART_RANGES: ChartRange[] = ['1M', '6M', 'YTD', '1Y', '5Y', 'CUSTOM']

export function DashboardPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [chartRange, setChartRange] = useState<ChartRange>('6M')
  const [customFrom, setCustomFrom] = useState('')
  const [customTo, setCustomTo] = useState('')
  const [showCumulative, setShowCumulative] = useState(false)

  const { thirtyDaysAgo } = useMemo(() => {
    const now = new Date()
    const thirtyDaysAgo = new Date(now)
    thirtyDaysAgo.setDate(now.getDate() - 30)
    return { thirtyDaysAgo }
  }, [])

  const { chartDateFrom, chartDateTo } = useMemo(() => {
    const now = new Date()
    if (chartRange === 'CUSTOM') {
      return { chartDateFrom: customFrom, chartDateTo: customTo || isoDate(now) }
    }
    let from: Date
    if (chartRange === '1M') {
      from = new Date(now); from.setMonth(now.getMonth() - 1)
    } else if (chartRange === '6M') {
      from = new Date(now); from.setMonth(now.getMonth() - 6)
    } else if (chartRange === 'YTD') {
      from = new Date(now.getFullYear(), 0, 1)
    } else if (chartRange === '1Y') {
      from = new Date(now); from.setFullYear(now.getFullYear() - 1)
    } else {
      from = new Date(now); from.setFullYear(now.getFullYear() - 5)
    }
    return { chartDateFrom: isoDate(from), chartDateTo: isoDate(now) }
  }, [chartRange, customFrom, customTo])

  // ── queries ──────────────────────────────────────────────────────────────

  const { data: txn30d, isLoading: loadingTxn30d, isError: errorTxn30d } = useQuery({
    queryKey: ['dashboard', 'transactions30d'],
    queryFn: () =>
      getTransactionsApi({
        date_from: isoDate(thirtyDaysAgo),
        page_size: '500',
      }).then((r) => r.data),
  })

  const { data: txnChart, isLoading: loadingChart, isError: errorChart } = useQuery({
    queryKey: ['dashboard', 'transactionsChart', chartDateFrom, chartDateTo],
    queryFn: () =>
      getTransactionsApi({
        date_from: chartDateFrom,
        date_to: chartDateTo,
        page_size: '1000',
      }).then((r) => r.data),
    enabled: chartRange !== 'CUSTOM' || !!(customFrom && customTo),
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
    if (!txnChart?.results.length) return []
    const map = new Map<string, number>()
    for (const t of txnChart.results) {
      map.set(t.date, (map.get(t.date) ?? 0) + parseFloat(t.amount))
    }
    const sorted = Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b))
    let cum = 0
    return sorted.map(([date, total]) => {
      cum += total
      return { date, total, cumulative: cum }
    })
  }, [txnChart])

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
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Spend Over Time</CardTitle>
            <div className="flex items-center gap-1">
              {CHART_RANGES.map((r) => (
                <button
                  key={r}
                  className={cn(
                    'rounded px-2 py-0.5 text-xs font-medium transition-colors',
                    chartRange === r
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-muted',
                  )}
                  onClick={() => setChartRange(r)}
                >
                  {r}
                </button>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            {/* controls row */}
            <div className="mb-3 flex flex-wrap items-center gap-4">
              {chartRange === 'CUSTOM' && (
                <div className="flex items-center gap-2">
                  <Input
                    type="date"
                    className="h-7 w-36 text-xs"
                    value={customFrom}
                    onChange={(e) => setCustomFrom(e.target.value)}
                  />
                  <span className="text-xs text-muted-foreground">to</span>
                  <Input
                    type="date"
                    className="h-7 w-36 text-xs"
                    value={customTo}
                    onChange={(e) => setCustomTo(e.target.value)}
                  />
                </div>
              )}
              <label className="flex cursor-pointer items-center gap-1.5 select-none">
                <input
                  type="checkbox"
                  checked={showCumulative}
                  onChange={(e) => setShowCumulative(e.target.checked)}
                  className="size-3.5 accent-amber-500"
                />
                <span className="inline-block size-2 rounded-full bg-amber-400" />
                <span className="text-xs text-muted-foreground">Total spend</span>
              </label>
            </div>

            {loadingChart ? (
              <Skeleton className="h-52 w-full" />
            ) : errorChart ? (
              <div className="flex h-52 items-center justify-center text-sm text-destructive">
                Failed to load transaction data
              </div>
            ) : chartRange === 'CUSTOM' && !(customFrom && customTo) ? (
              <div className="flex h-52 items-center justify-center text-sm text-muted-foreground">
                Select a start and end date
              </div>
            ) : spendChartData.length === 0 ? (
              <div className="flex h-52 items-center justify-center text-sm text-muted-foreground">
                No transaction data for this period
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={210}>
                <AreaChart
                  data={spendChartData}
                  margin={{ top: 8, right: showCumulative ? 64 : 8, left: 0, bottom: 0 }}
                >
                  <defs>
                    <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#6366f1" stopOpacity={0.18} />
                      <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v) => formatDateAxis(v, chartRange)}
                    interval={Math.max(0, Math.floor(spendChartData.length / 6) - 1)}
                  />
                  <YAxis
                    yAxisId="left"
                    tick={{ fontSize: 11 }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v: number) =>
                      v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`
                    }
                    width={52}
                  />
                  {showCumulative && (
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      tick={{ fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v: number) =>
                        v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v}`
                      }
                      width={60}
                    />
                  )}
                  <Tooltip
                    formatter={(value, name) => [
                      formatUSD(Number(value)),
                      name === 'total' ? 'Daily spend' : 'Total spend',
                    ]}
                    labelFormatter={(label) =>
                      new Date(label + 'T12:00:00').toLocaleDateString('en-US', {
                        month: 'long', day: 'numeric', year: 'numeric',
                      })
                    }
                    contentStyle={{
                      fontSize: 12,
                      border: '1px solid #e5e7eb',
                      borderRadius: '6px',
                      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
                    }}
                    cursor={{ stroke: '#6366f1', strokeWidth: 1, strokeDasharray: '4 4' }}
                  />
                  <Area
                    yAxisId="left"
                    type="monotone"
                    dataKey="total"
                    stroke="#6366f1"
                    strokeWidth={2}
                    fill="url(#spendGrad)"
                    dot={false}
                    activeDot={{ r: 4, fill: '#6366f1', strokeWidth: 0 }}
                  />
                  {showCumulative && (
                    <Line
                      yAxisId="right"
                      type="monotone"
                      dataKey="cumulative"
                      stroke="#f59e0b"
                      strokeWidth={1.5}
                      dot={false}
                      activeDot={{ r: 3, fill: '#f59e0b', strokeWidth: 0 }}
                    />
                  )}
                </AreaChart>
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
                      <Tooltip contentStyle={{ fontSize: 12 }} wrapperStyle={{ zIndex: 10 }} />
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
