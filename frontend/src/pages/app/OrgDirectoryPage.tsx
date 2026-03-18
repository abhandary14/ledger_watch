import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowDown, ArrowUp, ArrowUpDown, X } from 'lucide-react'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
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
import { useAuth } from '@/hooks/use-auth'
import { getOrgDirectoryApi, type OrgMember } from '@/api/organizations'

// ─── helpers ─────────────────────────────────────────────────────────────────

const ROLE_CLASS: Record<OrgMember['role'], string> = {
  owner: 'bg-purple-100 text-purple-700 border-purple-200',
  admin: 'bg-blue-100 text-blue-700 border-blue-200',
  employee: 'bg-gray-100 text-gray-600 border-gray-200',
}

function RoleBadge({ role }: { role: OrgMember['role'] }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize',
        ROLE_CLASS[role],
      )}
    >
      {role}
    </span>
  )
}

type SortField = 'name' | 'joined'
type SortDir = 'asc' | 'desc'

function SortIcon({ field, active, dir }: { field: SortField; active: SortField | null; dir: SortDir }) {
  if (active !== field) return <ArrowUpDown className="ml-1 inline size-3.5 opacity-40" />
  return dir === 'asc'
    ? <ArrowUp className="ml-1 inline size-3.5" />
    : <ArrowDown className="ml-1 inline size-3.5" />
}

// ─── page ─────────────────────────────────────────────────────────────────────

export function OrgDirectoryPage() {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()

  const roleFilter = searchParams.get('role') as OrgMember['role'] | null
  const sortField = (searchParams.get('sort') as SortField | null) ?? null
  const sortDir = (searchParams.get('dir') as SortDir | null) ?? 'asc'

  function setParam(key: string, value: string | null) {
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev)
      if (value === null) next.delete(key)
      else next.set(key, value)
      return next
    })
  }

  function toggleSort(field: SortField) {
    if (sortField === field) {
      if (sortDir === 'asc') {
        setParam('dir', 'desc')
      } else {
        setSearchParams((prev) => {
          const next = new URLSearchParams(prev)
          next.delete('sort')
          next.delete('dir')
          return next
        })
      }
    } else {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev)
        next.set('sort', field)
        next.set('dir', 'asc')
        return next
      })
    }
  }

  const { data: members, isLoading, isError } = useQuery({
    queryKey: ['org-directory'],
    queryFn: () => getOrgDirectoryApi().then((r) => r.data),
  })

  const displayed = (() => {
    if (!members) return []
    let list = roleFilter ? members.filter((m) => m.role === roleFilter) : [...members]
    if (sortField === 'name') {
      list.sort((a, b) => {
        const na = `${a.first_name} ${a.last_name}`.trim() || a.email
        const nb = `${b.first_name} ${b.last_name}`.trim() || b.email
        return sortDir === 'asc' ? na.localeCompare(nb) : nb.localeCompare(na)
      })
    } else if (sortField === 'joined') {
      list.sort((a, b) => {
        const diff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        return sortDir === 'asc' ? diff : -diff
      })
    }
    return list
  })()

  const hasFilters = roleFilter !== null || sortField !== null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">See Organization</h1>
        <p className="text-sm text-muted-foreground">
          {user?.organization.name} · all members
        </p>
      </div>

      {/* filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        <Select
          value={roleFilter ?? 'all'}
          onValueChange={(v) => setParam('role', v === 'all' ? null : v)}
        >
          <SelectTrigger className="h-8 w-36 text-sm">
            <SelectValue placeholder="All roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All roles</SelectItem>
            <SelectItem value="owner">Owner</SelectItem>
            <SelectItem value="admin">Admin</SelectItem>
            <SelectItem value="employee">Employee</SelectItem>
          </SelectContent>
        </Select>

        {hasFilters && (
          <Button
            variant="ghost"
            size="sm"
            className="h-8 px-2 text-xs text-muted-foreground"
            onClick={() => setSearchParams({})}
          >
            <X className="mr-1 size-3" />
            Clear
          </Button>
        )}
      </div>

      <div className="overflow-x-auto rounded-md border">
        {isLoading ? (
          <div className="space-y-px p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        ) : isError ? (
          <p className="py-12 text-center text-sm text-destructive">
            Failed to load members. Please try refreshing.
          </p>
        ) : !members || members.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">No members found.</p>
        ) : displayed.length === 0 ? (
          <p className="py-12 text-center text-sm text-muted-foreground">
            No members match the current filter.
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>
                  <button
                    className="flex items-center font-medium hover:text-foreground"
                    onClick={() => toggleSort('name')}
                  >
                    Name <SortIcon field="name" active={sortField} dir={sortDir} />
                  </button>
                </TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>
                  <button
                    className="flex items-center font-medium hover:text-foreground"
                    onClick={() => toggleSort('joined')}
                  >
                    Joined <SortIcon field="joined" active={sortField} dir={sortDir} />
                  </button>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {displayed.map((member) => (
                <TableRow key={member.id}>
                  <TableCell className="font-medium">
                    {member.first_name || member.last_name
                      ? `${member.first_name} ${member.last_name}`.trim()
                      : '—'}
                  </TableCell>
                  <TableCell className="text-sm">{member.email}</TableCell>
                  <TableCell>
                    <RoleBadge role={member.role} />
                  </TableCell>
                  <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                    {new Date(member.created_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>
    </div>
  )
}
