import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { getAlertsApi, acknowledgeAlertApi, resolveAlertApi, type Alert } from '@/api/alerts'

// ─── constants ───────────────────────────────────────────────────────────────

const ALERT_TYPES = ['large_transaction', 'burn_rate', 'vendor_spike', 'duplicate']

const SEVERITY_CLASS: Record<Alert['severity'], string> = {
  HIGH: 'bg-red-100 text-red-700 border-red-200',
  MEDIUM: 'bg-amber-100 text-amber-700 border-amber-200',
  LOW: 'bg-blue-100 text-blue-700 border-blue-200',
}

const STATUS_CLASS: Record<Alert['status'], string> = {
  OPEN: 'border-gray-300 text-gray-600',
  ACKNOWLEDGED: 'border-yellow-400 text-yellow-700',
  RESOLVED: 'border-green-500 text-green-700',
}

const SEVERITY_BTN: Record<Alert['severity'], string> = {
  HIGH: 'border-red-300 text-red-700 hover:bg-red-50',
  MEDIUM: 'border-amber-300 text-amber-700 hover:bg-amber-50',
  LOW: 'border-blue-300 text-blue-700 hover:bg-blue-50',
}

// ─── helpers ─────────────────────────────────────────────────────────────────

function relativeTime(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(ms / 60_000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}

// ─── severity badge ───────────────────────────────────────────────────────────

function SeverityBadge({ severity }: { severity: Alert['severity'] }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${SEVERITY_CLASS[severity]}`}
    >
      {severity}
    </span>
  )
}

// ─── status badge ─────────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: Alert['status'] }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${STATUS_CLASS[status]}`}
    >
      {status}
    </span>
  )
}

// ─── expandable message ───────────────────────────────────────────────────────

function AlertMessage({ message }: { message: string }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = message.length > 120
  return (
    <div>
      <p className={cn('text-sm', !expanded && isLong && 'line-clamp-2')}>{message}</p>
      {isLong && (
        <button
          className="mt-0.5 text-xs text-primary hover:underline"
          onClick={(e) => {
            e.stopPropagation()
            setExpanded((v) => !v)
          }}
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
    </div>
  )
}

// ─── page ─────────────────────────────────────────────────────────────────────

export function AlertsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const filterStatus = searchParams.get('status') ?? ''
  const filterSeverity = searchParams.get('severity') ?? ''
  const filterType = searchParams.get('alert_type') ?? ''
  const page = parseInt(searchParams.get('page') ?? '1', 10)

  const hasFilters = !!(filterStatus || filterSeverity || filterType)

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

  const {
    data: alertsData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['alerts', filterStatus, filterSeverity, filterType, page],
    queryFn: () =>
      getAlertsApi({
        status: filterStatus || undefined,
        severity: filterSeverity || undefined,
        alert_type: filterType || undefined,
        page,
      }).then((r) => r.data),
  })

  const { mutate: acknowledge, isPending: acknowledging } = useMutation({
    mutationFn: (id: string) => acknowledgeAlertApi(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setSelected((s) => { const n = new Set(s); n.delete(id); return n })
      toast.success('Alert acknowledged')
    },
    onError: () => toast.error('Failed to acknowledge alert'),
  })

  const { mutate: resolve, isPending: resolving } = useMutation({
    mutationFn: (id: string) => resolveAlertApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('Alert resolved')
    },
    onError: () => toast.error('Failed to resolve alert'),
  })

  async function acknowledgeAll() {
    const ids = Array.from(selected)
    if (ids.length > 5) toast.info(`Acknowledging ${ids.length} alerts…`)
    try {
      await Promise.all(ids.map((id) => acknowledgeAlertApi(id)))
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setSelected(new Set())
      toast.success(`${ids.length} alerts acknowledged`)
    } catch {
      toast.error('Some alerts could not be acknowledged')
    }
  }

  const alerts = alertsData?.results ?? []
  const totalPages = alertsData ? Math.ceil(alertsData.count / 20) : 1
  const openAlerts = alerts.filter((a) => a.status === 'OPEN')

  function toggleSelect(id: string) {
    setSelected((s) => {
      const n = new Set(s)
      if (n.has(id)) n.delete(id)
      else n.add(id)
      return n
    })
  }

  function toggleAll() {
    if (selected.size === openAlerts.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(openAlerts.map((a) => a.id)))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Alerts</h1>
        <p className="text-sm text-muted-foreground">Review and manage detected issues</p>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Status button group */}
        <div className="flex rounded-md border">
          {(['', 'OPEN', 'ACKNOWLEDGED', 'RESOLVED'] as const).map((s) => (
            <button
              key={s || 'all'}
              className={cn(
                'px-3 py-1.5 text-xs font-medium transition-colors first:rounded-l-md last:rounded-r-md',
                filterStatus === s
                  ? 'bg-foreground text-background'
                  : 'hover:bg-muted',
              )}
              onClick={() => setFilter('status', s)}
            >
              {s || 'All'}
            </button>
          ))}
        </div>

        {/* Severity button group */}
        <div className="flex rounded-md border">
          <button
            className={cn(
              'px-3 py-1.5 text-xs font-medium transition-colors rounded-l-md',
              filterSeverity === '' ? 'bg-foreground text-background' : 'hover:bg-muted',
            )}
            onClick={() => setFilter('severity', '')}
          >
            All
          </button>
          {(['HIGH', 'MEDIUM', 'LOW'] as const).map((sv) => (
            <button
              key={sv}
              className={cn(
                'px-3 py-1.5 text-xs font-medium border-l transition-colors last:rounded-r-md',
                filterSeverity === sv
                  ? SEVERITY_CLASS[sv]
                  : cn(SEVERITY_BTN[sv], 'bg-background'),
              )}
              onClick={() => setFilter('severity', sv)}
            >
              {sv}
            </button>
          ))}
        </div>

        {/* Alert type dropdown */}
        <Select
          value={filterType}
          onValueChange={(v) => setFilter('alert_type', v === 'all' ? '' : v)}
        >
          <SelectTrigger className="h-8 w-44 text-xs">
            <SelectValue placeholder="All types" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All types</SelectItem>
            {ALERT_TYPES.map((t) => (
              <SelectItem key={t} value={t}>
                {t}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Bulk acknowledge */}
        {selected.size > 0 && (
          <Button size="sm" variant="outline" onClick={acknowledgeAll}>
            Acknowledge selected ({selected.size})
          </Button>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-md border">
        {isLoading ? (
          <div className="space-y-px p-4">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-14 w-full" />
            ))}
          </div>
        ) : isError ? (
          <p className="py-12 text-center text-sm text-destructive">
            Failed to load alerts. Please try refreshing.
          </p>
        ) : alerts.length === 0 ? (
          <div className="py-16 text-center">
            {hasFilters ? (
              <>
                <p className="text-sm text-muted-foreground">No alerts match your filters.</p>
                <button
                  className="mt-2 text-sm text-primary underline-offset-4 hover:underline"
                  onClick={() => setSearchParams({})}
                >
                  Clear filters
                </button>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                No alerts yet. Run an analysis to detect issues.
              </p>
            )}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">
                  <Checkbox
                    checked={openAlerts.length > 0 && selected.size === openAlerts.length}
                    onCheckedChange={toggleAll}
                    aria-label="Select all open"
                  />
                </TableHead>
                <TableHead>Severity</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Message</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {alerts.map((alert) => (
                <TableRow
                  key={alert.id}
                  className={cn(alert.status === 'RESOLVED' && 'opacity-50')}
                >
                  <TableCell>
                    {alert.status === 'OPEN' && (
                      <Checkbox
                        checked={selected.has(alert.id)}
                        onCheckedChange={() => toggleSelect(alert.id)}
                        aria-label={`Select alert ${alert.id}`}
                      />
                    )}
                  </TableCell>
                  <TableCell>
                    <SeverityBadge severity={alert.severity} />
                  </TableCell>
                  <TableCell className="text-sm">{alert.alert_type}</TableCell>
                  <TableCell className="max-w-xs">
                    <AlertMessage message={alert.message} />
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                    {relativeTime(alert.created_at)}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={alert.status} />
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {alert.status === 'OPEN' && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 text-xs"
                            disabled={acknowledging || resolving}
                            onClick={() => acknowledge(alert.id)}
                          >
                            Acknowledge
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 px-2 text-xs"
                            disabled={acknowledging || resolving}
                            onClick={() => resolve(alert.id)}
                          >
                            Resolve
                          </Button>
                        </>
                      )}
                      {alert.status === 'ACKNOWLEDGED' && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2 text-xs"
                          disabled={resolving}
                          onClick={() => resolve(alert.id)}
                        >
                          Resolve
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

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
  )
}
