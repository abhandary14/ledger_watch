import { useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Loader2, ChevronLeft, ChevronRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  runAnalysisApi,
  getAnalysisResultsApi,
  getAnalysisResultApi,
  type AnalysisRun,
} from '@/api/analysis'
import { useAuth } from '@/hooks/use-auth'

// ─── constants ───────────────────────────────────────────────────────────────

const ANALYZER_TYPES = [
  {
    value: 'large_transaction',
    label: 'Large Transaction Detector',
    description: 'Flags transactions exceeding 2× the org mean or $10,000',
  },
  {
    value: 'burn_rate',
    label: 'Burn Rate Analyzer',
    description: 'Calculates monthly cash burn and runway in months',
  },
  {
    value: 'vendor_spike',
    label: 'Vendor Spike Detector',
    description: 'Detects month-over-month vendor spend increases ≥ 25%',
  },
  {
    value: 'duplicate',
    label: 'Duplicate Transaction Finder',
    description: 'Finds transactions with identical vendor + amount within 48 hours',
  },
]

// ─── helpers ─────────────────────────────────────────────────────────────────

function formatUSD(value: string | number): string {
  const n = typeof value === 'string' ? parseFloat(value) : value
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}

function relativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(ms / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

function getKeyMetric(run: AnalysisRun): string {
  if (!run.results_summary) return '—'
  const s = run.results_summary
  switch (run.analysis_type) {
    case 'large_transaction': {
      const count =
        (s.flagged_count as number) ??
        (Array.isArray(s.transactions) ? (s.transactions as unknown[]).length : null) ??
        (Array.isArray(s.flagged_transactions) ? (s.flagged_transactions as unknown[]).length : 0)
      return `${count} flagged`
    }
    case 'burn_rate': {
      const runway = s.runway_months as number | undefined
      return runway != null ? `Runway: ${runway.toFixed(1)} months` : '—'
    }
    case 'vendor_spike': {
      const count =
        (s.vendor_count as number) ??
        (Array.isArray(s.flagged_vendors) ? (s.flagged_vendors as unknown[]).length : 0)
      return `${count} vendors spiked`
    }
    case 'duplicate': {
      const count =
        (s.group_count as number) ??
        (Array.isArray(s.duplicate_groups) ? (s.duplicate_groups as unknown[]).length : 0)
      return `${count} duplicate groups`
    }
    default:
      return '—'
  }
}

// ─── status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: AnalysisRun['status'] }) {
  const variants: Record<AnalysisRun['status'], string> = {
    PENDING: 'bg-gray-100 text-gray-700 border-gray-200',
    SUCCEEDED: 'bg-green-100 text-green-700 border-green-200',
    FAILED: 'bg-red-100 text-red-700 border-red-200',
  }
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${variants[status]}`}
    >
      {status}
    </span>
  )
}

// ─── result detail drawer ────────────────────────────────────────────────────

function ResultDetail({ run }: { run: AnalysisRun }) {
  const s = run.results_summary
  if (!s) return <p className="text-sm text-muted-foreground">No results data available.</p>

  if (run.analysis_type === 'large_transaction') {
    const threshold = s.threshold as number | undefined
    const txns = (s.flagged_transactions ?? s.transactions ?? []) as Array<{
      vendor: string
      amount: string
      date: string
    }>
    return (
      <div className="space-y-4">
        {threshold != null && (
          <p className="text-sm">
            <span className="font-medium">Threshold:</span> {formatUSD(threshold)}
          </p>
        )}
        {txns.length === 0 ? (
          <p className="text-sm text-muted-foreground">No flagged transactions.</p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Vendor</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Date</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {txns.map((t, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <Link
                      to={`/transactions?vendor=${encodeURIComponent(t.vendor)}`}
                      className="text-primary underline-offset-4 hover:underline"
                    >
                      {t.vendor}
                    </Link>
                  </TableCell>
                  <TableCell className="text-right">{formatUSD(t.amount)}</TableCell>
                  <TableCell>{t.date}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    )
  }

  if (run.analysis_type === 'burn_rate') {
    const avgExpenses = s.avg_monthly_expenses as number | undefined
    const avgRevenue = s.avg_monthly_revenue as number | undefined
    const netBurn = s.net_burn as number | undefined
    const runway = s.runway_months as number | undefined

    const runwayColor =
      runway == null ? '' : runway < 3 ? 'bg-red-500' : runway < 6 ? 'bg-amber-500' : 'bg-green-500'
    const runwayPct = runway != null ? Math.min((runway / 12) * 100, 100) : 0

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-3 text-sm">
          {avgExpenses != null && (
            <div>
              <p className="text-muted-foreground">Avg Monthly Expenses</p>
              <p className="font-medium">{formatUSD(avgExpenses)}</p>
            </div>
          )}
          {avgRevenue != null && (
            <div>
              <p className="text-muted-foreground">Avg Monthly Revenue</p>
              <p className="font-medium">{formatUSD(avgRevenue)}</p>
            </div>
          )}
          {netBurn != null && (
            <div>
              <p className="text-muted-foreground">Net Burn</p>
              <p className="font-medium">{formatUSD(netBurn)}</p>
            </div>
          )}
          {runway != null && (
            <div>
              <p className="text-muted-foreground">Runway</p>
              <p className="font-medium">{runway.toFixed(1)} months</p>
            </div>
          )}
        </div>
        {runway != null && (
          <div className="space-y-1">
            <p className="text-xs text-muted-foreground">Runway indicator</p>
            <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full rounded-full transition-all ${runwayColor}`}
                style={{ width: `${runwayPct}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">
              {runway < 3 ? 'Critical — less than 3 months' : runway < 6 ? 'Warning — 3–6 months' : 'Healthy — more than 6 months'}
            </p>
          </div>
        )}
      </div>
    )
  }

  if (run.analysis_type === 'vendor_spike') {
    const vendors = (s.flagged_vendors ?? []) as Array<{
      vendor: string
      previous_spend: number
      current_spend: number
      percent_increase: number
    }>
    return vendors.length === 0 ? (
      <p className="text-sm text-muted-foreground">No vendor spikes detected.</p>
    ) : (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Vendor</TableHead>
            <TableHead className="text-right">Previous</TableHead>
            <TableHead className="text-right">Current</TableHead>
            <TableHead className="text-right">% Change</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {vendors.map((v, i) => (
            <TableRow key={i}>
              <TableCell>{v.vendor}</TableCell>
              <TableCell className="text-right">{formatUSD(v.previous_spend ?? 0)}</TableCell>
              <TableCell className="text-right">{formatUSD(v.current_spend ?? 0)}</TableCell>
              <TableCell className="text-right text-amber-600">
                +{(v.percent_increase ?? 0).toFixed(1)}%
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    )
  }

  if (run.analysis_type === 'duplicate') {
    const groups = (s.duplicate_groups ?? []) as Array<{
      vendor: string
      amount: string | number
      transactions: Array<{ id: string; date: string; created_at?: string }>
    }>
    return groups.length === 0 ? (
      <p className="text-sm text-muted-foreground">No duplicate groups found.</p>
    ) : (
      <div className="space-y-4">
        {groups.map((g, i) => (
          <div key={i} className="rounded-md border p-3 text-sm">
            <p className="font-medium">
              {g.vendor} — {formatUSD(g.amount)}
            </p>
            <div className="mt-2 space-y-1">
              {(g.transactions ?? []).map((t) => (
                <p key={t.id} className="text-muted-foreground">
                  ID: {t.id.slice(0, 8)}… &middot; {t.date ?? t.created_at}
                </p>
              ))}
            </div>
          </div>
        ))}
      </div>
    )
  }

  return <pre className="text-xs">{JSON.stringify(s, null, 2)}</pre>
}

// ─── inline run result ────────────────────────────────────────────────────────

function InlineResult({ run }: { run: AnalysisRun }) {
  return (
    <div className="mt-3 rounded-md border bg-muted/40 p-3 text-sm">
      <div className="flex items-center gap-2">
        <StatusBadge status={run.status} />
        <span className="font-medium">{getKeyMetric(run)}</span>
      </div>
      {run.error_message && (
        <p className="mt-1 text-destructive">{run.error_message}</p>
      )}
    </div>
  )
}

// ─── page ─────────────────────────────────────────────────────────────────────

export function AnalysisPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()

  const [selectedType, setSelectedType] = useState<string>('')
  const [lastResult, setLastResult] = useState<AnalysisRun | null>(null)
  const [runError, setRunError] = useState<string | null>(null)
  const [drawerRunId, setDrawerRunId] = useState<string | null>(null)

  const filterType = searchParams.get('analysis_type') ?? ''
  const filterStatus = searchParams.get('status') ?? ''
  const page = parseInt(searchParams.get('page') ?? '1', 10)

  function setFilter(key: string, value: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (value) next.set(key, value)
      else next.delete(key)
      next.delete('page')
      return next
    })
  }

  function setPage(p: number) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('page', String(p))
      return next
    })
  }

  const { mutate: runAnalysis, isPending: isRunning } = useMutation({
    mutationFn: () => runAnalysisApi(selectedType),
    onSuccess: ({ data }) => {
      setLastResult(data)
      setRunError(null)
      queryClient.invalidateQueries({ queryKey: ['analysis', 'results'] })
      toast.success('Analysis started')
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string; analysis_type?: string[] } } })?.response
          ?.data?.detail ??
        (err as { response?: { data?: { analysis_type?: string[] } } })?.response?.data
          ?.analysis_type?.[0] ??
        'Analysis failed'
      setRunError(msg)
      setLastResult(null)
    },
  })

  const {
    data: resultsData,
    isLoading: loadingResults,
    isError: errorResults,
  } = useQuery({
    queryKey: ['analysis', 'results', filterType, filterStatus, page],
    queryFn: () =>
      getAnalysisResultsApi({
        analysis_type: filterType || undefined,
        status: filterStatus || undefined,
        page,
      }).then((r) => r.data),
  })

  const { data: drawerRun, isLoading: loadingDrawer } = useQuery({
    queryKey: ['analysis', 'result', drawerRunId],
    queryFn: () => getAnalysisResultApi(drawerRunId!).then((r) => r.data),
    enabled: drawerRunId != null,
  })

  const { user } = useAuth()
  const canRunAnalysis = user?.role === 'owner' || user?.role === 'admin'

  const selectedMeta = ANALYZER_TYPES.find((t) => t.value === selectedType)
  const totalPages = resultsData ? Math.ceil(resultsData.count / 20) : 1

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Analysis</h1>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left panel — Run Analysis */}
        {canRunAnalysis ? (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Run Analysis</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Select value={selectedType} onValueChange={setSelectedType}>
                <SelectTrigger>
                  <SelectValue placeholder="Select analyzer type…" />
                </SelectTrigger>
                <SelectContent>
                  {ANALYZER_TYPES.map((t) => (
                    <SelectItem key={t.value} value={t.value}>
                      {t.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {selectedMeta && (
                <p className="text-xs text-muted-foreground">{selectedMeta.description}</p>
              )}

              <Button
                className="w-full"
                disabled={!selectedType || isRunning}
                onClick={() => {
                  setLastResult(null)
                  setRunError(null)
                  runAnalysis()
                }}
              >
                {isRunning && <Loader2 className="mr-2 size-4 animate-spin" />}
                Run Analysis
              </Button>

              {runError && (
                <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
                  {runError}
                </p>
              )}

              {lastResult && <InlineResult run={lastResult} />}
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">Run Analysis</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-muted-foreground">
                Only admins and owners can run analysis.
              </p>
            </CardContent>
          </Card>
        )}

        {/* Right panel — Results History */}
        <div className="col-span-2 space-y-4">
          {/* Filters */}
          <div className="flex gap-2">
            <Select value={filterType} onValueChange={(v) => setFilter('analysis_type', v === 'all' ? '' : v)}>
              <SelectTrigger className="w-52">
                <SelectValue placeholder="All types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All types</SelectItem>
                {ANALYZER_TYPES.map((t) => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={filterStatus} onValueChange={(v) => setFilter('status', v === 'all' ? '' : v)}>
              <SelectTrigger className="w-40">
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All statuses</SelectItem>
                <SelectItem value="PENDING">Pending</SelectItem>
                <SelectItem value="SUCCEEDED">Succeeded</SelectItem>
                <SelectItem value="FAILED">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Card>
            <CardContent className="p-0">
              {loadingResults ? (
                <div className="space-y-px p-4">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : errorResults ? (
                <p className="py-10 text-center text-sm text-destructive">
                  Failed to load analysis results
                </p>
              ) : !resultsData?.results.length ? (
                <p className="py-10 text-center text-sm text-muted-foreground">
                  No analysis results found.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Type</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Run Time</TableHead>
                        <TableHead>Key Metric</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {resultsData.results.map((run) => (
                        <TableRow
                          key={run.id}
                          className="cursor-pointer hover:bg-muted/50"
                          onClick={() => setDrawerRunId(run.id)}
                        >
                          <TableCell className="font-medium">
                            {ANALYZER_TYPES.find((t) => t.value === run.analysis_type)?.label ??
                              run.analysis_type}
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={run.status} />
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {run.run_time ? relativeTime(run.run_time) : relativeTime(run.created_at)}
                          </TableCell>
                          <TableCell className="text-sm">{getKeyMetric(run)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-end gap-2 text-sm">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                <ChevronLeft className="size-4" />
                Previous
              </Button>
              <span className="text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
              >
                Next
                <ChevronRight className="size-4" />
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Result Detail Drawer */}
      <Sheet open={drawerRunId != null} onOpenChange={(open) => !open && setDrawerRunId(null)}>
        <SheetContent className="w-[520px] overflow-y-auto sm:max-w-[520px]">
          <SheetHeader>
            <SheetTitle>
              {drawerRun
                ? (ANALYZER_TYPES.find((t) => t.value === drawerRun.analysis_type)?.label ??
                  drawerRun.analysis_type)
                : 'Result Detail'}
            </SheetTitle>
          </SheetHeader>
          <div className="mt-4">
            {loadingDrawer ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-10 w-full" />
                ))}
              </div>
            ) : drawerRun ? (
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <StatusBadge status={drawerRun.status} />
                  <span className="text-sm text-muted-foreground">
                    {drawerRun.run_time
                      ? relativeTime(drawerRun.run_time)
                      : relativeTime(drawerRun.created_at)}
                  </span>
                </div>
                {drawerRun.error_message && (
                  <p className="text-sm text-destructive">{drawerRun.error_message}</p>
                )}
                <ResultDetail run={drawerRun} />
              </div>
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  )
}
