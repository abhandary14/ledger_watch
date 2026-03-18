import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { Copy, Check } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { useAuth } from '@/hooks/use-auth'
import { updateProfileApi, changePasswordApi, updateOrganizationApi } from '@/api/settings'

// ─── schemas ──────────────────────────────────────────────────────────────────

const profileSchema = z.object({
  first_name: z.string().max(100),
  last_name: z.string().max(100),
})

const passwordSchema = z
  .object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z.string().min(8, 'New password must be at least 8 characters'),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  })

const orgSchema = z.object({
  name: z.string().min(1, 'Organization name cannot be empty').max(255),
})

type ProfileValues = z.infer<typeof profileSchema>
type PasswordValues = z.infer<typeof passwordSchema>
type OrgValues = z.infer<typeof orgSchema>

// ─── profile tab ─────────────────────────────────────────────────────────────

function ProfileTab() {
  const { user } = useAuth()
  const [editing, setEditing] = useState(false)

  const profileForm = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      first_name: user?.first_name ?? '',
      last_name: user?.last_name ?? '',
    },
  })

  const passwordForm = useForm<PasswordValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: '', new_password: '', confirm_password: '' },
  })

  const { mutate: saveProfile, isPending: savingProfile } = useMutation({
    mutationFn: (data: ProfileValues) => updateProfileApi(data),
    onSuccess: () => {
      toast.success('Profile updated')
      setEditing(false)
    },
    onError: () => toast.error('Failed to update profile'),
  })

  const { mutate: changePassword, isPending: changingPassword } = useMutation({
    mutationFn: (data: PasswordValues) =>
      changePasswordApi({
        current_password: data.current_password,
        new_password: data.new_password,
      }),
    onSuccess: () => {
      toast.success('Password updated')
      passwordForm.reset()
    },
    onError: (err: unknown) => {
      const data = (err as { response?: { data?: Record<string, string[]> } })?.response?.data
      if (data?.current_password) {
        passwordForm.setError('current_password', { message: data.current_password[0] })
      } else if (data?.new_password) {
        passwordForm.setError('new_password', { message: data.new_password[0] })
      } else {
        toast.error('Failed to change password')
      }
    },
  })

  return (
    <div className="space-y-6">
      {/* Profile info */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle className="text-base">Profile Information</CardTitle>
          {!editing && (
            <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
              Edit
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {editing ? (
            <Form {...profileForm}>
              <form
                onSubmit={profileForm.handleSubmit((v) => saveProfile(v))}
                className="space-y-4"
              >
                <div className="grid grid-cols-2 gap-4">
                  <FormField
                    control={profileForm.control}
                    name="first_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>First Name</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={profileForm.control}
                    name="last_name"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Last Name</FormLabel>
                        <FormControl>
                          <Input {...field} />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <div className="flex gap-2">
                  <Button type="submit" size="sm" disabled={savingProfile}>
                    Save
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setEditing(false)
                      profileForm.reset()
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </Form>
          ) : (
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Email</p>
                <p className="font-medium">{user?.email}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Role</p>
                <p className="font-medium capitalize">{(user as unknown as { role?: string })?.role ?? '—'}</p>
              </div>
              <div>
                <p className="text-muted-foreground">First Name</p>
                <p className="font-medium">{user?.first_name || '—'}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Last Name</p>
                <p className="font-medium">{user?.last_name || '—'}</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Change password */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Change Password</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...passwordForm}>
            <form
              onSubmit={passwordForm.handleSubmit((v) => changePassword(v))}
              className="max-w-sm space-y-4"
            >
              <FormField
                control={passwordForm.control}
                name="current_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Current Password</FormLabel>
                    <FormControl>
                      <Input type="password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={passwordForm.control}
                name="new_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>New Password</FormLabel>
                    <FormControl>
                      <Input type="password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={passwordForm.control}
                name="confirm_password"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Confirm New Password</FormLabel>
                    <FormControl>
                      <Input type="password" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" size="sm" disabled={changingPassword}>
                Update Password
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  )
}

// ─── organization tab ─────────────────────────────────────────────────────────

function OrganizationTab() {
  const { user } = useAuth()
  const [copied, setCopied] = useState(false)

  const orgForm = useForm<OrgValues>({
    resolver: zodResolver(orgSchema),
    defaultValues: { name: user?.organization?.name ?? '' },
  })

  const { mutate: saveOrg, isPending: savingOrg } = useMutation({
    mutationFn: (data: OrgValues) => updateOrganizationApi(user!.organization.id, data),
    onSuccess: ({ data }) => {
      toast.success('Organization updated')
      orgForm.setValue('name', data.name)
    },
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { name?: string[]; detail?: string } } })
        ?.response?.data
      if (detail?.name) {
        orgForm.setError('name', { message: detail.name[0] })
      } else {
        toast.error('Failed to update organization')
      }
    },
  })

  async function copyId() {
    if (!user?.organization?.id) return
    await navigator.clipboard.writeText(user.organization.id)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Organization Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Editable name */}
          <Form {...orgForm}>
            <form
              onSubmit={orgForm.handleSubmit((v) => saveOrg(v))}
              className="max-w-sm space-y-3"
            >
              <FormField
                control={orgForm.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Organization Name</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <Button type="submit" size="sm" disabled={savingOrg}>
                Save
              </Button>
            </form>
          </Form>

          {/* Read-only fields */}
          <div className="space-y-4 text-sm">
            <div>
              <Label className="text-muted-foreground">Organization ID</Label>
              <div className="mt-1 flex items-center gap-2">
                <code className="rounded bg-muted px-2 py-1 text-xs font-mono">
                  {user?.organization?.id}
                </code>
                <Button variant="ghost" size="sm" className="h-7 px-2" onClick={copyId}>
                  {copied ? <Check className="size-3" /> : <Copy className="size-3" />}
                </Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

// ─── page ─────────────────────────────────────────────────────────────────────

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
      </div>

      <Tabs defaultValue="profile" className="space-y-4">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="organization">Organization</TabsTrigger>
        </TabsList>
        <TabsContent value="profile">
          <ProfileTab />
        </TabsContent>
        <TabsContent value="organization">
          <OrganizationTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
