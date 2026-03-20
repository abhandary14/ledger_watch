import * as React from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import Papa from 'papaparse'
import type { ParseResult } from 'papaparse'
import {
  ChevronDown,
  ChevronUp,
  ChevronsUpDown,
  ChevronRight,
  ChevronLeft,
  Upload,
  Plus,
  CalendarIcon,
  X,
  Trash2,
} from 'lucide-react'
import { format } from 'date-fns'

import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

import {
  getTransactionsApi,
  getTransactionFilterOptionsApi,
  importTransactionsApi,
  deleteTransactionApi,
  type Transaction,
  type TransactionImportRow,
} from '@/api/transactions'
import { useAuth } from '@/hooks/use-auth'
import { useColumnResize } from '@/hooks/use-column-resize'

// ─── helpers ────────────────────────────────────────────────────────────────

function formatUSD(value: string | number): string {
  const n = typeof value === 'string' ? parseFloat(value) : value
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(n)
}

function isoDate(date: Date): string {
  return date.toISOString().split('T')[0]
}

const PAGE_SIZE_OPTIONS = ['25', '50', '100', 'all'] as const

// ─── date picker ─────────────────────────────────────────────────────────────

interface DatePickerProps {
  value: Date | undefined
  onChange: (date: Date | undefined) => void
  placeholder?: string
}

function DatePicker({ value, onChange, placeholder = 'Pick a date' }: DatePickerProps) {
  const [open, setOpen] = React.useState(false)
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            'h-9 w-[140px] justify-start text-left text-sm font-normal',
            !value && 'text-muted-foreground',
          )}
        >
          <CalendarIcon className="mr-2 size-4 shrink-0" />
          {value ? format(value, 'MMM d, yyyy') : placeholder}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={value}
          onSelect={(d) => {
            onChange(d)
            setOpen(false)
          }}
          initialFocus
        />
      </PopoverContent>
    </Popover>
  )
}

// ─── row detail panel ────────────────────────────────────────────────────────

function TransactionDetail({
  tx,
  canDelete,
  onDelete,
}: {
  tx: Transaction
  canDelete: boolean
  onDelete: (id: string) => void
}) {
  return (
    <tr>
      <td colSpan={6} className="bg-muted/30 px-4 py-3">
        <dl className="grid grid-cols-2 gap-x-8 gap-y-1 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-xs font-medium text-muted-foreground">ID</dt>
            <dd className="font-mono text-xs">{tx.id}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-muted-foreground">Date</dt>
            <dd>{tx.date}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-muted-foreground">Vendor</dt>
            <dd>{tx.vendor}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-muted-foreground">Category</dt>
            <dd>{tx.category || '—'}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-muted-foreground">Amount</dt>
            <dd>{formatUSD(tx.amount)}</dd>
          </div>
          <div>
            <dt className="text-xs font-medium text-muted-foreground">Created</dt>
            <dd>{new Date(tx.created_at).toLocaleString()}</dd>
          </div>
          {tx.description && (
            <div className="col-span-full">
              <dt className="text-xs font-medium text-muted-foreground">Description</dt>
              <dd className="whitespace-pre-wrap">{tx.description}</dd>
            </div>
          )}
        </dl>
        {canDelete && (
          <div className="mt-3 flex justify-end">
            <Button
              variant="outline"
              size="sm"
              className="h-7 px-2 text-xs text-destructive hover:bg-destructive/10 hover:text-destructive"
              onClick={(e) => {
                e.stopPropagation()
                onDelete(tx.id)
              }}
            >
              <Trash2 className="mr-1 size-3" />
              Delete
            </Button>
          </div>
        )}
      </td>
    </tr>
  )
}

// ─── add transaction dialog ───────────────────────────────────────────────────

const addSchema = z.object({
  date: z.date({ required_error: 'Date is required' }),
  vendor: z.string().min(1, 'Vendor is required'),
  amount: z
    .string()
    .min(1, 'Amount is required')
    .refine((v) => !isNaN(parseFloat(v)) && parseFloat(v) > 0, 'Amount must be greater than 0'),
  category: z.string().optional(),
  description: z.string().optional(),
})
type AddFormValues = z.infer<typeof addSchema>

interface AddTransactionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function AddTransactionDialog({ open, onOpenChange }: AddTransactionDialogProps) {
  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors },
  } = useForm<AddFormValues>({
    resolver: zodResolver(addSchema),
    defaultValues: { date: new Date() },
  })

  const { mutate, isPending } = useMutation({
    mutationFn: (row: TransactionImportRow) => importTransactionsApi([row]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      toast.success('Transaction added')
      onOpenChange(false)
      reset({ date: new Date() })
    },
    onError: () => toast.error('Failed to add transaction'),
  })

  function onSubmit(values: AddFormValues) {
    mutate({
      date: isoDate(values.date),
      vendor: values.vendor,
      amount: values.amount,
      category: values.category || undefined,
      description: values.description || undefined,
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Transaction</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* Date */}
          <div className="space-y-1">
            <Label>Date</Label>
            <Controller
              control={control}
              name="date"
              render={({ field }) => (
                <DatePicker value={field.value} onChange={field.onChange} />
              )}
            />
            {errors.date && <p className="text-xs text-destructive">{errors.date.message}</p>}
          </div>

          {/* Vendor */}
          <div className="space-y-1">
            <Label htmlFor="add-vendor">Vendor</Label>
            <Input id="add-vendor" placeholder="Acme Corp" {...register('vendor')} />
            {errors.vendor && (
              <p className="text-xs text-destructive">{errors.vendor.message}</p>
            )}
          </div>

          {/* Amount */}
          <div className="space-y-1">
            <Label htmlFor="add-amount">Amount</Label>
            <Input
              id="add-amount"
              type="number"
              step="0.01"
              min="0.01"
              placeholder="0.00"
              {...register('amount')}
            />
            {errors.amount && (
              <p className="text-xs text-destructive">{errors.amount.message}</p>
            )}
          </div>

          {/* Category */}
          <div className="space-y-1">
            <Label htmlFor="add-category">Category (optional)</Label>
            <Input id="add-category" placeholder="e.g. Software" {...register('category')} />
          </div>

          {/* Description */}
          <div className="space-y-1">
            <Label htmlFor="add-description">Description (optional)</Label>
            <textarea
              id="add-description"
              className="flex min-h-[72px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:border-ring disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="Optional notes"
              {...register('description')}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Adding…' : 'Add Transaction'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ─── CSV import dialog ────────────────────────────────────────────────────────

type CsvRow = Record<string, string>

interface ColumnMapping {
  date: string
  vendor: string
  amount: string
  category: string
  description: string
}

const REQUIRED_MAPPINGS = ['date', 'vendor', 'amount'] as const
const OPTIONAL_MAPPINGS = ['category', 'description'] as const
const ALL_MAPPINGS = [...REQUIRED_MAPPINGS, ...OPTIONAL_MAPPINGS] as const
type MappingKey = (typeof ALL_MAPPINGS)[number]

const MAPPING_LABELS: Record<MappingKey, string> = {
  date: 'Date',
  vendor: 'Vendor',
  amount: 'Amount',
  category: 'Category (optional)',
  description: 'Description (optional)',
}

function autoMap(headers: string[]): ColumnMapping {
  const lower = headers.map((h) => h.toLowerCase())
  function match(key: MappingKey): string {
    const idx = lower.findIndex((h) => h === key || h.includes(key))
    return idx >= 0 ? headers[idx] : ''
  }
  return {
    date: match('date'),
    vendor: match('vendor'),
    amount: match('amount'),
    category: match('category'),
    description: match('description'),
  }
}

interface ValidationResult {
  row: CsvRow
  mapped: TransactionImportRow
  error: string | null
}

function validateRow(row: CsvRow, mapping: ColumnMapping): ValidationResult {
  const date = row[mapping.date]?.trim() ?? ''
  const vendor = row[mapping.vendor]?.trim() ?? ''
  const amount = row[mapping.amount]?.trim() ?? ''

  let error: string | null = null
  if (!vendor) error = 'Missing vendor'
  else if (!date || isNaN(new Date(date).getTime())) error = 'Invalid date'
  else if (!amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0)
    error = 'Amount must be > 0'

  const mapped: TransactionImportRow = {
    date,
    vendor,
    amount,
    category: mapping.category ? row[mapping.category]?.trim() || undefined : undefined,
    description: mapping.description ? row[mapping.description]?.trim() || undefined : undefined,
  }

  return { row, mapped, error }
}

interface ImportCsvDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

function ImportCsvDialog({ open, onOpenChange }: ImportCsvDialogProps) {
  const queryClient = useQueryClient()
  const [step, setStep] = React.useState<1 | 2 | 3 | 4>(1)
  const [fileName, setFileName] = React.useState('')
  const [csvRows, setCsvRows] = React.useState<CsvRow[]>([])
  const [headers, setHeaders] = React.useState<string[]>([])
  const [mapping, setMapping] = React.useState<ColumnMapping>({
    date: '',
    vendor: '',
    amount: '',
    category: '',
    description: '',
  })
  const [validationResults, setValidationResults] = React.useState<ValidationResult[]>([])
  const [importResult, setImportResult] = React.useState<{
    success?: number
    skipped?: number
    error?: string
  } | null>(null)
  const [isDragging, setIsDragging] = React.useState(false)
  const fileInputRef = React.useRef<HTMLInputElement>(null)

  const { mutate: doImport, isPending: importing } = useMutation({
    mutationFn: (rows: TransactionImportRow[]) => importTransactionsApi(rows),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      setImportResult({ success: res.data.imported, skipped: res.data.skipped })
      setStep(4)
    },
    onError: (err: unknown) => {
      let msg = 'Import failed. Please check your data and try again.'
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        if (axiosErr.response?.data?.detail) {
          msg = axiosErr.response.data.detail
        }
      }
      setImportResult({ error: msg })
      setStep(4)
    },
  })

  function resetDialog() {
    setStep(1)
    setFileName('')
    setCsvRows([])
    setHeaders([])
    setMapping({ date: '', vendor: '', amount: '', category: '', description: '' })
    setValidationResults([])
    setImportResult(null)
    setIsDragging(false)
  }

  function handleOpenChange(val: boolean) {
    if (!val) resetDialog()
    onOpenChange(val)
  }

  function parseFile(file: File) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      toast.error('Please upload a .csv file')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error('File is too large (max 5MB)')
      return
    }
    Papa.parse<CsvRow>(file, {
      header: true,
      skipEmptyLines: true,
      complete: (result: ParseResult<CsvRow>) => {
        if (result.data.length === 0) {
          toast.error('CSV file has no rows')
          return
        }
        const hdrs = result.meta.fields ?? []
        setFileName(file.name)
        setHeaders(hdrs)
        setCsvRows(result.data)
        setMapping(autoMap(hdrs))
        setStep(2)
      },
    })
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) parseFile(file)
    e.target.value = ''
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) parseFile(file)
  }

  function handleStep2Next() {
    const missing = REQUIRED_MAPPINGS.filter((k) => !mapping[k])
    if (missing.length > 0) {
      toast.error(`Please map required columns: ${missing.join(', ')}`)
      return
    }
    const results = csvRows.map((row) => validateRow(row, mapping))
    setValidationResults(results)
    setStep(3)
  }

  function handleImport() {
    const valid = validationResults.filter((r) => !r.error).map((r) => r.mapped)
    if (valid.length === 0) {
      toast.error('No valid rows to import')
      return
    }
    doImport(valid)
  }

  const validCount = validationResults.filter((r) => !r.error).length
  const invalidCount = validationResults.filter((r) => r.error).length

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            Import CSV &mdash; Step {step} of 4:{' '}
            {step === 1
              ? 'Upload File'
              : step === 2
                ? 'Map Columns'
                : step === 3
                  ? 'Preview & Confirm'
                  : 'Done'}
          </DialogTitle>
        </DialogHeader>

        {/* Step 1 — Upload */}
        {step === 1 && (
          <div className="space-y-4">
            <div
              className={cn(
                'flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-10 transition-colors',
                isDragging ? 'border-primary bg-primary/5' : 'border-border',
              )}
              onDragOver={(e) => {
                e.preventDefault()
                setIsDragging(true)
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
            >
              <Upload className="size-8 text-muted-foreground" />
              <div className="text-center">
                <p className="text-sm font-medium">Drag and drop a CSV file here</p>
                <p className="text-xs text-muted-foreground">or click to browse</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
                Browse File
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleFileChange}
              />
              <p className="text-xs text-muted-foreground">Max 5MB, .csv only</p>
            </div>
          </div>
        )}

        {/* Step 2 — Column Mapping */}
        {step === 2 && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              File: <span className="font-medium text-foreground">{fileName}</span> &mdash;{' '}
              {csvRows.length} rows
            </p>

            <div className="grid grid-cols-2 gap-3">
              {ALL_MAPPINGS.map((key) => (
                <div key={key} className="space-y-1">
                  <Label className="text-xs">{MAPPING_LABELS[key]}</Label>
                  <Select
                    value={mapping[key]}
                    onValueChange={(val) =>
                      setMapping((prev) => ({ ...prev, [key]: val === '__none__' ? '' : val }))
                    }
                  >
                    <SelectTrigger className="h-8 w-full text-xs">
                      <SelectValue placeholder="Select column" />
                    </SelectTrigger>
                    <SelectContent>
                      {OPTIONAL_MAPPINGS.includes(key as (typeof OPTIONAL_MAPPINGS)[number]) && (
                        <SelectItem value="__none__">— none —</SelectItem>
                      )}
                      {headers.map((h) => (
                        <SelectItem key={h} value={h}>
                          {h}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              ))}
            </div>

            {/* Live preview */}
            {csvRows.length > 0 && mapping.date && mapping.vendor && mapping.amount && (
              <div className="space-y-1">
                <p className="text-xs font-medium text-muted-foreground">Preview (first 5 rows)</p>
                <div className="overflow-x-auto rounded border">
                  <table className="w-full text-xs">
                    <thead className="bg-muted/50">
                      <tr>
                        <th className="px-2 py-1 text-left">Date</th>
                        <th className="px-2 py-1 text-left">Vendor</th>
                        <th className="px-2 py-1 text-right">Amount</th>
                        {mapping.category && <th className="px-2 py-1 text-left">Category</th>}
                        {mapping.description && (
                          <th className="px-2 py-1 text-left">Description</th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {csvRows.slice(0, 5).map((row, i) => (
                        <tr key={i} className="border-t">
                          <td className="px-2 py-1">{row[mapping.date] ?? ''}</td>
                          <td className="px-2 py-1">{row[mapping.vendor] ?? ''}</td>
                          <td className="px-2 py-1 text-right">{row[mapping.amount] ?? ''}</td>
                          {mapping.category && (
                            <td className="px-2 py-1">{row[mapping.category] ?? ''}</td>
                          )}
                          {mapping.description && (
                            <td className="px-2 py-1">{row[mapping.description] ?? ''}</td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            <DialogFooter>
              <Button variant="outline" onClick={() => setStep(1)}>
                Back
              </Button>
              <Button onClick={handleStep2Next}>Next</Button>
            </DialogFooter>
          </div>
        )}

        {/* Step 3 — Preview & Confirm */}
        {step === 3 && (
          <div className="space-y-4">
            <p className="text-sm">
              <span className="font-medium text-green-600">{validCount} valid</span>
              {invalidCount > 0 && (
                <>
                  {', '}
                  <span className="font-medium text-red-600">{invalidCount} invalid</span>
                  {'. Invalid rows will be skipped.'}
                </>
              )}
            </p>

            <div className="max-h-72 overflow-y-auto rounded border">
              <table className="w-full text-xs">
                <thead className="sticky top-0 bg-muted/50">
                  <tr>
                    <th className="px-2 py-1 text-left">#</th>
                    <th className="px-2 py-1 text-left">Date</th>
                    <th className="px-2 py-1 text-left">Vendor</th>
                    <th className="px-2 py-1 text-right">Amount</th>
                    <th className="px-2 py-1 text-left">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {validationResults.map((r, i) => (
                    <tr
                      key={i}
                      className={cn(
                        'border-t',
                        r.error ? 'bg-red-50 text-red-800 dark:bg-red-950/30 dark:text-red-400' : '',
                      )}
                    >
                      <td className="px-2 py-1">{i + 1}</td>
                      <td className="px-2 py-1">{r.mapped.date}</td>
                      <td className="px-2 py-1">{r.mapped.vendor}</td>
                      <td className="px-2 py-1 text-right">{r.mapped.amount}</td>
                      <td className="px-2 py-1">
                        {r.error ? (
                          <span className="font-medium">{r.error}</span>
                        ) : (
                          <span className="text-green-600">Valid</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setStep(2)}>
                Back
              </Button>
              <Button onClick={handleImport} disabled={importing || validCount === 0}>
                {importing ? 'Importing…' : `Import ${validCount} Transaction${validCount !== 1 ? 's' : ''}`}
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* Step 4 — Result */}
        {step === 4 && (
          <div className="space-y-4">
            {importResult?.error ? (
              <div className="rounded-md bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-400">
                <p className="font-medium">Import failed</p>
                <p className="mt-1">{importResult.error}</p>
              </div>
            ) : (
              <div className="rounded-md bg-green-50 p-4 text-sm text-green-700 dark:bg-green-950/30 dark:text-green-400">
                <p className="font-medium">
                  Successfully imported {importResult?.success ?? validCount} transaction
                  {(importResult?.success ?? validCount) !== 1 ? 's' : ''}
                </p>
                {(importResult?.skipped ?? 0) > 0 && (
                  <p className="mt-1 text-amber-600 dark:text-amber-400">
                    {importResult!.skipped} duplicate transaction{importResult!.skipped !== 1 ? 's were' : ' was'} skipped (already imported).
                  </p>
                )}
              </div>
            )}
            <DialogFooter>
              <Button onClick={() => handleOpenChange(false)}>Done</Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

// ─── resize handle ────────────────────────────────────────────────────────────

function ResizeHandle({ onMouseDown }: { onMouseDown: (e: React.MouseEvent) => void }) {
  return (
    <div
      className="absolute right-0 top-0 h-full w-2 cursor-col-resize select-none group/rh"
      onMouseDown={(e) => { e.stopPropagation(); onMouseDown(e) }}
    >
      <div className="absolute right-0 top-1 h-[calc(100%-8px)] w-px bg-border opacity-0 transition-opacity group-hover/rh:opacity-100" />
    </div>
  )
}

// ─── filter bar ───────────────────────────────────────────────────────────────

interface FilterBarProps {
  vendor: string
  category: string
  dateFrom: Date | undefined
  dateTo: Date | undefined
  vendors: string[]
  categories: string[]
  onVendorChange: (v: string) => void
  onCategoryChange: (v: string) => void
  onDateFromChange: (d: Date | undefined) => void
  onDateToChange: (d: Date | undefined) => void
  onClear: () => void
  hasFilters: boolean
}

function FilterBar({
  vendor,
  category,
  dateFrom,
  dateTo,
  vendors,
  categories,
  onVendorChange,
  onCategoryChange,
  onDateFromChange,
  onDateToChange,
  onClear,
  hasFilters,
}: FilterBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select value={vendor || '__all__'} onValueChange={(v) => onVendorChange(v === '__all__' ? '' : v)}>
        <SelectTrigger className="h-9 w-44 text-sm">
          <SelectValue placeholder="All vendors" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">All vendors</SelectItem>
          {vendors.map((v) => (
            <SelectItem key={v} value={v}>{v}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Select value={category || '__all__'} onValueChange={(v) => onCategoryChange(v === '__all__' ? '' : v)}>
        <SelectTrigger className="h-9 w-44 text-sm">
          <SelectValue placeholder="All categories" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="__all__">All categories</SelectItem>
          {categories.map((c) => (
            <SelectItem key={c} value={c}>{c}</SelectItem>
          ))}
        </SelectContent>
      </Select>
      <DatePicker value={dateFrom} onChange={onDateFromChange} placeholder="Date from" />
      <DatePicker value={dateTo} onChange={onDateToChange} placeholder="Date to" />
      {hasFilters && (
        <Button variant="ghost" size="sm" className="h-9 px-2" onClick={onClear}>
          <X className="mr-1 size-3.5" />
          Clear
        </Button>
      )}
    </div>
  )
}

// ─── page ─────────────────────────────────────────────────────────────────────

type SortField = 'date' | 'amount'
type SortDir = 'asc' | 'desc'

function SortIcon({ field, sortField, sortDir }: { field: SortField; sortField: SortField | null; sortDir: SortDir }) {
  if (sortField !== field) return <ChevronsUpDown className="ml-1 inline size-3.5 text-muted-foreground/50" />
  return sortDir === 'asc'
    ? <ChevronUp className="ml-1 inline size-3.5" />
    : <ChevronDown className="ml-1 inline size-3.5" />
}

export function TransactionsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [addOpen, setAddOpen] = React.useState(false)
  const [importOpen, setImportOpen] = React.useState(false)
  const [expandedId, setExpandedId] = React.useState<string | null>(null)
  const queryClient = useQueryClient()
  const { user } = useAuth()
  const canDelete = user?.role === 'owner' || user?.role === 'admin'

  // column widths: Date, Vendor, Category, Amount, Description, chevron
  const { widths: colW, sumPx, startResize, containerRef } = useColumnResize([90, 160, 130, 110, 220, 32])

  const { mutate: deleteTransaction } = useMutation({
    mutationFn: (id: string) => deleteTransactionApi(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transactions'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard'] })
      setExpandedId(null)
      toast.success('Transaction deleted')
    },
    onError: () => toast.error('Failed to delete transaction'),
  })

  // Read filter + sort state from URL
  const urlVendor = searchParams.get('vendor') ?? ''
  const urlCategory = searchParams.get('category') ?? ''
  const urlDateFrom = searchParams.get('date_from') ?? ''
  const urlDateTo = searchParams.get('date_to') ?? ''
  const urlOrdering = searchParams.get('ordering') ?? ''
  const page = parseInt(searchParams.get('page') ?? '1', 10)
  const pageSizeParam = searchParams.get('page_size') ?? '25'
  // 'all' is passed as-is to the backend; numeric strings are parsed for local totalPages math.
  const pageSize = pageSizeParam === 'all' ? null : parseInt(pageSizeParam, 10)

  const dateFrom = urlDateFrom ? new Date(urlDateFrom) : undefined
  const dateTo = urlDateTo ? new Date(urlDateTo) : undefined

  // Derive sort field/dir from ordering param
  const sortField: SortField | null =
    urlOrdering.replace('-', '') === 'date' ? 'date'
    : urlOrdering.replace('-', '') === 'amount' ? 'amount'
    : null
  const sortDir: SortDir = urlOrdering.startsWith('-') ? 'desc' : 'asc'

  const hasFilters = !!(urlVendor || urlCategory || urlDateFrom || urlDateTo)

  function updateParam(key: string, value: string | undefined) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (value) {
        next.set(key, value)
      } else {
        next.delete(key)
      }
      next.set('page', '1')
      return next
    })
  }

  function handleVendorChange(v: string) {
    updateParam('vendor', v || undefined)
  }

  function handleCategoryChange(v: string) {
    updateParam('category', v || undefined)
  }

  function handleDateFromChange(d: Date | undefined) {
    updateParam('date_from', d ? isoDate(d) : undefined)
  }

  function handleDateToChange(d: Date | undefined) {
    updateParam('date_to', d ? isoDate(d) : undefined)
  }

  function handleClearFilters() {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.delete('vendor')
      next.delete('category')
      next.delete('date_from')
      next.delete('date_to')
      next.set('page', '1')
      return next
    })
  }

  function handleSort(field: SortField) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      next.set('page', '1')
      if (sortField === field) {
        if (sortDir === 'desc') {
          // desc → asc
          next.set('ordering', field)
        } else {
          // asc → clear (back to default)
          next.delete('ordering')
        }
      } else {
        // new field → desc first
        next.set('ordering', `-${field}`)
      }
      return next
    })
  }

  // Build query params
  const queryParams: Record<string, string> = {
    page: String(page),
    page_size: pageSizeParam,  // send 'all' literally when selected
  }
  if (urlVendor) queryParams.vendor = urlVendor
  if (urlCategory) queryParams.category = urlCategory
  if (urlDateFrom) queryParams.date_from = urlDateFrom
  if (urlDateTo) queryParams.date_to = urlDateTo
  if (urlOrdering) queryParams.ordering = urlOrdering

  const { data, isLoading, isError } = useQuery({
    queryKey: ['transactions', queryParams],
    queryFn: () => getTransactionsApi(queryParams).then((r) => r.data),
    placeholderData: (prev) => prev,
  })

  const { data: filterOptions } = useQuery({
    queryKey: ['transactions', 'filter-options'],
    queryFn: () => getTransactionFilterOptionsApi().then((r) => r.data),
    staleTime: 60_000,
  })

  const totalPages = data && pageSize ? Math.max(1, Math.ceil(data.count / pageSize)) : 1

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
      next.set('page', '1')
      return next
    })
  }

  function toggleExpand(id: string) {
    setExpandedId((prev) => (prev === id ? null : id))
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Transactions</h1>
          <p className="text-sm text-muted-foreground">
            {data ? `${data.count.toLocaleString()} total` : 'Loading…'}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setImportOpen(true)}>
            <Upload className="size-4" />
            Import CSV
          </Button>
          <Button size="sm" onClick={() => setAddOpen(true)}>
            <Plus className="size-4" />
            Add Transaction
          </Button>
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        vendor={urlVendor}
        category={urlCategory}
        dateFrom={dateFrom}
        dateTo={dateTo}
        vendors={filterOptions?.vendors ?? []}
        categories={filterOptions?.categories ?? []}
        onVendorChange={handleVendorChange}
        onCategoryChange={handleCategoryChange}
        onDateFromChange={handleDateFromChange}
        onDateToChange={handleDateToChange}
        onClear={handleClearFilters}
        hasFilters={hasFilters}
      />

      {/* Table */}
      <div ref={containerRef} className="overflow-x-auto rounded-lg border">
        <Table style={{ tableLayout: 'fixed', width: sumPx }}>
          <TableHeader>
            <TableRow>
              <TableHead
                className="relative whitespace-nowrap"
                style={{ width: colW[0] }}
              >
                <button
                  className="flex cursor-pointer select-none items-center"
                  onClick={() => handleSort('date')}
                >
                  Date <SortIcon field="date" sortField={sortField} sortDir={sortDir} />
                </button>
                <ResizeHandle onMouseDown={(e) => startResize(0, e)} />
              </TableHead>
              <TableHead className="relative" style={{ width: colW[1] }}>
                Vendor
                <ResizeHandle onMouseDown={(e) => startResize(1, e)} />
              </TableHead>
              <TableHead className="relative" style={{ width: colW[2] }}>
                Category
                <ResizeHandle onMouseDown={(e) => startResize(2, e)} />
              </TableHead>
              <TableHead
                className="relative whitespace-nowrap text-right"
                style={{ width: colW[3] }}
              >
                <button
                  className="ml-auto flex cursor-pointer select-none items-center"
                  onClick={() => handleSort('amount')}
                >
                  Amount <SortIcon field="amount" sortField={sortField} sortDir={sortDir} />
                </button>
                <ResizeHandle onMouseDown={(e) => startResize(3, e)} />
              </TableHead>
              <TableHead className="relative" style={{ width: colW[4] }}>
                Description
                <ResizeHandle onMouseDown={(e) => startResize(4, e)} />
              </TableHead>
              <TableHead style={{ width: colW[5] }} />
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <TableRow key={i}>
                  <TableCell>
                    <Skeleton className="h-4 w-24" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-32" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-24" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="ml-auto h-4 w-20" />
                  </TableCell>
                  <TableCell>
                    <Skeleton className="h-4 w-40" />
                  </TableCell>
                  <TableCell />
                </TableRow>
              ))
            ) : isError ? (
              <TableRow>
                <TableCell colSpan={6} className="py-12 text-center text-sm text-destructive">
                  Failed to load transactions. Please try again.
                </TableCell>
              </TableRow>
            ) : data?.results.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="py-12 text-center text-sm text-muted-foreground">
                  {hasFilters ? 'No transactions match your filters.' : 'No transactions yet. Import a CSV or add one manually.'}
                </TableCell>
              </TableRow>
            ) : (
              data?.results.map((tx) => (
                <React.Fragment key={tx.id}>
                  <TableRow
                    className="cursor-pointer"
                    onClick={() => toggleExpand(tx.id)}
                  >
                    <TableCell className="text-sm">{tx.date}</TableCell>
                    <TableCell className="truncate text-sm font-medium">
                      {tx.vendor}
                    </TableCell>
                    <TableCell className="truncate text-sm text-muted-foreground">
                      {tx.category || '—'}
                    </TableCell>
                    <TableCell className="text-right text-sm font-mono">
                      {formatUSD(tx.amount)}
                    </TableCell>
                    <TableCell className="truncate text-sm text-muted-foreground">
                      {tx.description || '—'}
                    </TableCell>
                    <TableCell className="text-center">
                      {expandedId === tx.id ? (
                        <ChevronDown className="size-4 text-muted-foreground" />
                      ) : (
                        <ChevronRight className="size-4 text-muted-foreground" />
                      )}
                    </TableCell>
                  </TableRow>
                  {expandedId === tx.id && (
                    <TransactionDetail
                      tx={tx}
                      canDelete={canDelete}
                      onDelete={deleteTransaction}
                    />
                  )}
                </React.Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {!isLoading && data && data.count > 0 && (
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <span>Rows per page:</span>
            <Select value={pageSizeParam} onValueChange={setPageSizeParam}>
              <SelectTrigger className="h-7 w-20 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZE_OPTIONS.map((o) => (
                  <SelectItem key={o} value={o}>
                    {o === 'all' ? 'All' : o}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {pageSizeParam !== 'all' && totalPages > 1 && (
            <div className="flex items-center gap-3">
              <span className="text-muted-foreground">
                Page {page} of {totalPages}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  <ChevronLeft className="size-4" />
                  Prev
                </Button>
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
            </div>
          )}
        </div>
      )}

      {/* Dialogs */}
      <AddTransactionDialog open={addOpen} onOpenChange={setAddOpen} />
      <ImportCsvDialog open={importOpen} onOpenChange={setImportOpen} />
    </div>
  )
}
