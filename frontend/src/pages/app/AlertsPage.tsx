import * as React from 'react'
import { useState } from 'react'
import { useColumnResize } from '@/hooks/use-column-resize'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ChevronLeft, ChevronRight, ArrowUp, ArrowDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
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
import { getAlertsApi, acknowledgeAlertApi, resolveAlertApi, reopenAlertApi, deleteAlertApi, type Alert } from '@/api/alerts'
import { useAuth } from '@/hooks/use-auth'

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

// ─── resize handle ────────────────────────────────────────────────────────────

function ResizeHandle({ onMouseDown }: { onMouseDown: (e: React.MouseEvent) => void }) {
  return (
    <div
      className="absolute right-0 top-0 h-full w-2 cursor-col-resize select-none group/rh"
      onMouseDown={onMouseDown}
    >
      <div className="absolute right-0 top-1 h-[calc(100%-8px)] w-px bg-border opacity-0 transition-opacity group-hover/rh:opacity-100" />
    </div>
  )
}

// ─── page ─────────────────────────────────────────────────────────────────────

export function AlertsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const canReopen = user?.role === 'owner' || user?.role === 'admin'
  const canDelete = user?.role === 'owner' || user?.role === 'admin'
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [alertToDelete, setAlertToDelete] = useState<string | null>(null)

  // column widths: checkbox, Severity, Type, Message, Created, Status, Actions
  const { widths: colW, sumPx, startResize, containerRef } = useColumnResize([40, 90, 140, 300, 90, 110, 200])

  const filterStatus = searchParams.get('status') ?? ''
  const filterSeverity = searchParams.get('severity') ?? ''
  const filterType = searchParams.get('alert_type') ?? ''
  const sortDir = (searchParams.get('sort') ?? 'desc') as 'asc' | 'desc'
  const page = Math.max(parseInt(searchParams.get('page') ?? '1', 10) || 1, 1)
  const pageSizeParam = searchParams.get('page_size') ?? '25'
  const pageSize = Math.min(Math.max(parseInt(pageSizeParam, 10) || 25, 1), 1000)

  const hasFilters = !!(filterStatus || filterSeverity || filterType)

  function toggleSort() {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('sort', sortDir === 'desc' ? 'asc' : 'desc')
      next.delete('page')
      return next
    })
  }

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

  function setPageSizeParam(ps: string) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('page_size', ps)
      next.delete('page')
      return next
    })
  }

  const {
    data: alertsData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['alerts', filterStatus, filterSeverity, filterType, sortDir, page, pageSize],
    queryFn: () =>
      getAlertsApi({
        status: filterStatus || undefined,
        severity: filterSeverity || undefined,
        alert_type: filterType || undefined,
        ordering: sortDir === 'asc' ? 'created_at' : '-created_at',
        page,
        page_size: pageSize,
      }).then((r) => r.data),
  })

  function handleApiError(err: unknown, fallbackMessage: string) {
    const status = (err as { response?: { status?: number } })?.response?.status
    if (status === 403) {
      toast.error('This action can only be performed by an admin or owner. Contact your admin.')
    } else {
      toast.error(fallbackMessage)
    }
  }

  const { mutate: acknowledge, isPending: acknowledging } = useMutation({
    mutationFn: (id: string) => acknowledgeAlertApi(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setSelected((s) => { const n = new Set(s); n.delete(id); return n })
      toast.success('Alert acknowledged')
    },
    onError: (err: unknown) => handleApiError(err, 'Failed to acknowledge alert'),
  })

  const { mutate: resolve, isPending: resolving } = useMutation({
    mutationFn: (id: string) => resolveAlertApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('Alert resolved')
    },
    onError: (err: unknown) => handleApiError(err, 'Failed to resolve alert'),
  })

  const { mutate: reopen, isPending: reopening } = useMutation({
    mutationFn: (id: string) => reopenAlertApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('Alert reopened')
    },
    onError: (err: unknown) => handleApiError(err, 'Failed to reopen alert'),
  })

  const { mutate: deleteAlert, isPending: deleting } = useMutation({
    mutationFn: (id: string) => deleteAlertApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      toast.success('Alert deleted')
    },
    onError: (err: unknown) => handleApiError(err, 'Failed to delete alert'),
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
  const totalPages = alertsData ? Math.max(1, Math.ceil(alertsData.count / pageSize)) : 1
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
    <>
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Alerts</h1>
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
      <div ref={containerRef} className="overflow-x-auto rounded-md border">
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
          <Table style={{ tableLayout: 'fixed', width: sumPx }}>
            <TableHeader>
              <TableRow>
                <TableHead className="relative" style={{ width: colW[0] }}>
                  <Checkbox
                    checked={openAlerts.length > 0 && selected.size === openAlerts.length}
                    onCheckedChange={toggleAll}
                    aria-label="Select all open"
                  />
                </TableHead>
                <TableHead className="relative" style={{ width: colW[1] }}>
                  Severity
                  <ResizeHandle onMouseDown={(e) => startResize(1, e)} />
                </TableHead>
                <TableHead className="relative" style={{ width: colW[2] }}>
                  Type
                  <ResizeHandle onMouseDown={(e) => startResize(2, e)} />
                </TableHead>
                <TableHead className="relative" style={{ width: colW[3] }}>
                  Message
                  <ResizeHandle onMouseDown={(e) => startResize(3, e)} />
                </TableHead>
                <TableHead className="relative" style={{ width: colW[4] }}>
                  <button
                    className="flex items-center gap-1 font-medium hover:text-foreground"
                    onClick={toggleSort}
                  >
                    Created
                    {sortDir === 'desc'
                      ? <ArrowDown className="size-3.5" />
                      : <ArrowUp className="size-3.5" />}
                  </button>
                  <ResizeHandle onMouseDown={(e) => startResize(4, e)} />
                </TableHead>
                <TableHead className="relative" style={{ width: colW[5] }}>
                  Status
                  <ResizeHandle onMouseDown={(e) => startResize(5, e)} />
                </TableHead>
                <TableHead className="relative" style={{ width: colW[6] }}>
                  Actions
                  <ResizeHandle onMouseDown={(e) => startResize(6, e)} />
                </TableHead>
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
                  <TableCell className="overflow-hidden">
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
                      {alert.status === 'RESOLVED' && canReopen && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2 text-xs"
                          disabled={reopening}
                          onClick={() => reopen(alert.id)}
                        >
                          Reopen
                        </Button>
                      )}
                      {canDelete && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-7 px-2 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
                          disabled={deleting}
                          onClick={() => setAlertToDelete(alert.id)}
                        >
                          Delete
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
      {!isLoading && (alerts.length > 0 || alertsData) && (
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <span>Rows per page:</span>
            <Select value={pageSizeParam} onValueChange={setPageSizeParam}>
              <SelectTrigger className="h-7 w-20 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="25">25</SelectItem>
                <SelectItem value="50">50</SelectItem>
                <SelectItem value="100">100</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
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
      )}
    </div>

    <Dialog open={alertToDelete !== null} onOpenChange={(open) => { if (!open) setAlertToDelete(null) }}>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>Delete alert?</DialogTitle>
          <DialogDescription>This action cannot be undone.</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => setAlertToDelete(null)}>Cancel</Button>
          <Button
            variant="destructive"
            disabled={deleting}
            onClick={() => { if (alertToDelete) { deleteAlert(alertToDelete); setAlertToDelete(null) } }}
          >
            Delete
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
    </>
  )
}
