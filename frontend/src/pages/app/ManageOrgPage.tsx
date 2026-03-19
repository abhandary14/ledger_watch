import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { UserPlus, Trash2, Crown, Pencil, ArrowUpDown, ArrowUp, ArrowDown, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
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
import {
  getOrgMembersApi,
  createOrgMemberApi,
  updateMemberRoleApi,
  deleteMemberApi,
  transferOwnershipApi,
  getSecurityChallengeApi,
  type OrgMember,
} from '@/api/organizations'

// ─── constants ───────────────────────────────────────────────────────────────

const ROLE_CLASS: Record<OrgMember['role'], string> = {
  owner: 'bg-purple-100 text-purple-700 border-purple-200',
  admin: 'bg-blue-100 text-blue-700 border-blue-200',
  employee: 'bg-gray-100 text-gray-600 border-gray-200',
}

// ─── helpers ─────────────────────────────────────────────────────────────────

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

// ─── add member dialog ────────────────────────────────────────────────────────

const addMemberSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  role: z.enum(['admin', 'employee']),
  first_name: z.string().max(100).optional(),
  last_name: z.string().max(100).optional(),
})
type AddMemberForm = z.infer<typeof addMemberSchema>

function AddMemberDialog() {
  const [open, setOpen] = useState(false)
  const queryClient = useQueryClient()

  const { register, handleSubmit, setValue, reset, formState: { errors } } = useForm<AddMemberForm>({
    resolver: zodResolver(addMemberSchema),
    defaultValues: { role: 'employee' },
  })

  const { mutate: createMember, isPending } = useMutation({
    mutationFn: createOrgMemberApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-members'] })
      toast.success('Member added successfully')
      reset()
      setOpen(false)
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { email?: string[] } } })?.response?.data?.email?.[0] ??
        'Failed to add member'
      toast.error(msg)
    },
  })

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) reset()
    setOpen(nextOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="sm">
          <UserPlus className="mr-2 size-4" />
          Add Member
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add Organization Member</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit((data) => createMember(data))} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="first_name">First name</Label>
              <Input id="first_name" placeholder="Jane" {...register('first_name')} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="last_name">Last name</Label>
              <Input id="last_name" placeholder="Doe" {...register('last_name')} />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="email">Email <span className="text-destructive">*</span></Label>
            <Input id="email" type="email" placeholder="jane@example.com" {...register('email')} />
            {errors.email && <p className="text-xs text-destructive">{errors.email.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Password <span className="text-destructive">*</span></Label>
            <Input id="password" type="password" placeholder="Min. 8 characters" {...register('password')} />
            {errors.password && <p className="text-xs text-destructive">{errors.password.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="role">Role</Label>
            <Select defaultValue="employee" onValueChange={(v) => setValue('role', v as 'admin' | 'employee')}>
              <SelectTrigger id="role"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="employee">Employee</SelectItem>
                <SelectItem value="admin">Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => { reset(); setOpen(false) }}>Cancel</Button>
            <Button type="submit" disabled={isPending}>{isPending ? 'Adding…' : 'Add Member'}</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ─── edit role dialog ─────────────────────────────────────────────────────────

function EditRoleDialog({ member }: { member: OrgMember }) {
  const [open, setOpen] = useState(false)
  const [selectedRole, setSelectedRole] = useState<'admin' | 'employee'>(
    member.role === 'owner' ? 'admin' : member.role,
  )
  const queryClient = useQueryClient()

  const initialRole: 'admin' | 'employee' = member.role === 'owner' ? 'admin' : member.role

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen)
    if (nextOpen) setSelectedRole(initialRole)
  }

  const { mutate: updateRole, isPending } = useMutation({
    mutationFn: () => updateMemberRoleApi(member.id, selectedRole),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-members'] })
      toast.success('Role updated')
      setOpen(false)
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to update role'
      toast.error(msg)
    },
  })

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 w-7 p-0">
          <Pencil className="size-3.5" />
          <span className="sr-only">Edit role</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xs">
        <DialogHeader>
          <DialogTitle>Edit Role</DialogTitle>
          <DialogDescription>{member.email}</DialogDescription>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <Label>Role</Label>
          <Select
            value={selectedRole}
            onValueChange={(v) => setSelectedRole(v as 'admin' | 'employee')}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="employee">Employee</SelectItem>
              <SelectItem value="admin">Admin</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={() => updateRole()} disabled={isPending || selectedRole === member.role}>
            {isPending ? 'Saving…' : 'Save'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── remove member dialog ─────────────────────────────────────────────────────

function RemoveMemberDialog({ member }: { member: OrgMember }) {
  const [open, setOpen] = useState(false)
  const [challenge, setChallenge] = useState('')
  const [password, setPassword] = useState('')
  const [challengeInput, setChallengeInput] = useState('')
  const [challengeError, setChallengeError] = useState(false)
  const queryClient = useQueryClient()

  const { refetch: fetchChallenge, isFetching: isFetchingChallenge } = useQuery({
    queryKey: ['security-challenge'],
    queryFn: () => getSecurityChallengeApi().then((r) => r.data.challenge),
    enabled: false,
  })

  function loadChallenge() {
    setChallengeError(false)
    setChallenge('')
    fetchChallenge()
      .then(({ data }) => { if (data) setChallenge(data) })
      .catch(() => { setChallengeError(true) })
  }

  function handleOpen(value: boolean) {
    setOpen(value)
    if (value) {
      setPassword('')
      setChallengeInput('')
      loadChallenge()
    }
  }

  const { mutate: removeMember, isPending } = useMutation({
    mutationFn: () => deleteMemberApi(member.id, password, challengeInput),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org-members'] })
      toast.success('Member removed')
      setOpen(false)
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to remove member'
      toast.error(msg)
      setChallengeInput('')
      loadChallenge()
    },
  })

  const canSubmit = password.length > 0 && challengeInput === challenge && challenge.length > 0

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-destructive hover:bg-destructive/10 hover:text-destructive">
          <Trash2 className="size-3.5" />
          <span className="sr-only">Remove</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Remove Member</DialogTitle>
          <DialogDescription>
            To remove <strong>{member.email}</strong>, confirm your identity below. This action cannot be undone.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-1">
          <div className="space-y-1.5">
            <Label htmlFor="rm-password">Your password</Label>
            <Input
              id="rm-password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Security challenge</Label>
            {challengeError ? (
              <div className="flex items-center gap-2 rounded border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                <span>Failed to load challenge.</span>
                <button
                  type="button"
                  className="ml-auto underline hover:no-underline"
                  onClick={loadChallenge}
                >
                  Retry
                </button>
              </div>
            ) : isFetchingChallenge || !challenge ? (
              <div className="h-8 animate-pulse rounded bg-muted" />
            ) : (
              <code
                className="block rounded border bg-muted px-3 py-2 font-mono text-sm tracking-widest select-none"
                onCopy={(e) => e.preventDefault()}
              >
                {challenge}
              </code>
            )}
            <p className="text-xs text-muted-foreground">Type the string above exactly to confirm.</p>
            <Input
              placeholder="Type the challenge string"
              value={challengeInput}
              onChange={(e) => setChallengeInput(e.target.value)}
              className="font-mono text-sm"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button variant="destructive" onClick={() => removeMember()} disabled={isPending || !canSubmit || challengeError}>
            {isPending ? 'Removing…' : 'Remove'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── transfer ownership dialog ────────────────────────────────────────────────

function TransferOwnershipDialog({ member }: { member: OrgMember }) {
  const [open, setOpen] = useState(false)
  const [challenge, setChallenge] = useState('')
  const [password, setPassword] = useState('')
  const [challengeInput, setChallengeInput] = useState('')
  const [challengeError, setChallengeError] = useState(false)
  const { logout } = useAuth()
  const navigate = useNavigate()

  const newEmail = `owner@${member.email.split('@')[1]}`

  const { refetch: fetchChallenge, isFetching: isFetchingChallenge } = useQuery({
    queryKey: ['security-challenge'],
    queryFn: () => getSecurityChallengeApi().then((r) => r.data.challenge),
    enabled: false,
  })

  function loadChallenge() {
    setChallengeError(false)
    setChallenge('')
    fetchChallenge()
      .then(({ data }) => { if (data) setChallenge(data) })
      .catch(() => { setChallengeError(true) })
  }

  function handleOpen(value: boolean) {
    setOpen(value)
    if (value) {
      setPassword('')
      setChallengeInput('')
      loadChallenge()
    }
  }

  const { mutate: transfer, isPending } = useMutation({
    mutationFn: () => transferOwnershipApi(member.id, password, challengeInput),
    onSuccess: async () => {
      toast.success('Ownership transferred. You have been signed out.')
      setOpen(false)
      await logout()
      navigate('/login')
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to transfer ownership'
      toast.error(msg)
      setChallengeInput('')
      loadChallenge()
    },
  })

  const canSubmit = password.length > 0 && challengeInput === challenge && challenge.length > 0

  return (
    <Dialog open={open} onOpenChange={handleOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-amber-600 hover:bg-amber-50 hover:text-amber-700">
          <Crown className="size-3.5" />
          <span className="sr-only">Transfer ownership</span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Transfer Ownership</DialogTitle>
          <DialogDescription>
            This will make <strong>{member.email}</strong> the new owner.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          <p className="font-medium">What will happen:</p>
          <ul className="ml-4 list-disc space-y-1 text-xs">
            <li><strong>{member.email}</strong> becomes the new owner</li>
            <li>Their email changes to <strong>{newEmail}</strong></li>
            <li>Your account will be <strong>permanently deleted</strong></li>
            <li>You will be signed out immediately</li>
          </ul>
        </div>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="to-password">Your password</Label>
            <Input
              id="to-password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Security challenge</Label>
            {challengeError ? (
              <div className="flex items-center gap-2 rounded border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                <span>Failed to load challenge.</span>
                <button
                  type="button"
                  className="ml-auto underline hover:no-underline"
                  onClick={loadChallenge}
                >
                  Retry
                </button>
              </div>
            ) : isFetchingChallenge || !challenge ? (
              <div className="h-8 animate-pulse rounded bg-muted" />
            ) : (
              <code
                className="block rounded border bg-muted px-3 py-2 font-mono text-sm tracking-widest select-none"
                onCopy={(e) => e.preventDefault()}
              >
                {challenge}
              </code>
            )}
            <p className="text-xs text-muted-foreground">Type the string above exactly to confirm.</p>
            <Input
              placeholder="Type the challenge string"
              value={challengeInput}
              onChange={(e) => setChallengeInput(e.target.value)}
              className="font-mono text-sm"
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button
            variant="destructive"
            onClick={() => transfer()}
            disabled={isPending || !canSubmit || challengeError}
          >
            {isPending ? 'Transferring…' : 'Transfer & Sign Out'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── page ─────────────────────────────────────────────────────────────────────

type SortField = 'name' | 'joined'
type SortDir = 'asc' | 'desc'

function SortIcon({ field, active, dir }: { field: SortField; active: SortField | null; dir: SortDir }) {
  if (active !== field) return <ArrowUpDown className="ml-1 inline size-3.5 opacity-40" />
  return dir === 'asc'
    ? <ArrowUp className="ml-1 inline size-3.5" />
    : <ArrowDown className="ml-1 inline size-3.5" />
}

export function ManageOrgPage() {
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
      if (sortDir === 'asc') setParam('dir', 'desc')
      else {
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
    queryKey: ['org-members'],
    queryFn: () => getOrgMembersApi().then((r) => r.data),
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
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Manage Organization</h1>
          <p className="text-sm text-muted-foreground">
            {user?.organization.name}
          </p>
        </div>
        <AddMemberDialog />
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
          <p className="py-12 text-center text-sm text-muted-foreground">No members match the current filter.</p>
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
                <TableHead className="w-28">Actions</TableHead>
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
                  <TableCell>
                    {member.role !== 'owner' && (
                      <div className="flex items-center gap-1">
                        <EditRoleDialog member={member} />
                        {member.role === 'admin' && (
                          <TransferOwnershipDialog member={member} />
                        )}
                        <RemoveMemberDialog member={member} />
                      </div>
                    )}
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
