import * as React from 'react'
import { cn } from '@/lib/utils'

// ─── section data ─────────────────────────────────────────────────────────────

const SECTIONS = [
  { id: 'overview', label: 'Overview' },
  { id: 'getting-started', label: 'Getting Started' },
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'transactions', label: 'Transactions' },
  { id: 'analysis', label: 'Analysis' },
  { id: 'alerts', label: 'Alerts' },
  { id: 'settings', label: 'Settings' },
  { id: 'organization', label: 'Organization' },
  { id: 'roles', label: 'Roles & Permissions' },
]

// ─── small helpers ────────────────────────────────────────────────────────────

function Badge({ children, color }: { children: React.ReactNode; color: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold border',
        color,
      )}
    >
      {children}
    </span>
  )
}

function Note({ children, variant = 'info' }: { children: React.ReactNode; variant?: 'info' | 'warn' | 'tip' }) {
  const styles = {
    info: 'bg-blue-50 border-blue-200 text-blue-900 dark:bg-blue-950/30 dark:border-blue-800 dark:text-blue-200',
    warn: 'bg-amber-50 border-amber-200 text-amber-900 dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-200',
    tip:  'bg-green-50 border-green-200 text-green-900 dark:bg-green-950/30 dark:border-green-800 dark:text-green-200',
  }
  const label = { info: 'Note', warn: 'Important', tip: 'Tip' }
  return (
    <div className={cn('my-4 rounded-lg border px-4 py-3 text-sm', styles[variant])}>
      <span className="font-semibold">{label[variant]}: </span>
      {children}
    </div>
  )
}

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-6">
      <h2 className="mb-4 text-xl font-semibold text-foreground">{title}</h2>
      <div className="space-y-3 text-sm leading-relaxed text-muted-foreground">{children}</div>
    </section>
  )
}

function Sub({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mt-5">
      <h3 className="mb-2 text-base font-medium text-foreground">{title}</h3>
      <div className="space-y-2">{children}</div>
    </div>
  )
}

function Constraint({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-2">
      <span className="mt-0.5 shrink-0 text-amber-500">▲</span>
      <span>{children}</span>
    </li>
  )
}

function Step({ n, children }: { n: number; children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-3">
      <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
        {n}
      </span>
      <span className="pt-0.5">{children}</span>
    </li>
  )
}

function PermTable() {
  const rows: [string, boolean, boolean, boolean][] = [
    ['View transactions, alerts, analysis', true, true, true],
    ['Import / add transactions', true, true, true],
    ['Run analysis', false, true, true],
    ['Acknowledge / resolve / reopen alerts', false, true, true],
    ['Delete transactions or alerts', false, true, true],
    ['Generate weekly report', false, false, true],
    ['Rename organization', false, false, true],
    ['Add members to the organization', false, false, true],
    ['Edit member roles / remove members', false, false, true],
    ['Transfer ownership', false, false, true],
  ]
  return (
    <div className="overflow-x-auto rounded-lg border text-sm">
      <table className="w-full">
        <thead className="bg-muted/50">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-foreground">Action</th>
            <th className="px-4 py-2 text-center font-medium text-foreground">
              <Badge color="border-gray-300 text-gray-600">Employee</Badge>
            </th>
            <th className="px-4 py-2 text-center font-medium text-foreground">
              <Badge color="border-blue-300 text-blue-700 bg-blue-50">Admin</Badge>
            </th>
            <th className="px-4 py-2 text-center font-medium text-foreground">
              <Badge color="border-purple-300 text-purple-700 bg-purple-50">Owner</Badge>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([action, emp, adm, own]) => (
            <tr key={action} className="border-t">
              <td className="px-4 py-2 text-muted-foreground">{action}</td>
              {[emp, adm, own].map((allowed, i) => (
                <td key={i} className="px-4 py-2 text-center">
                  {allowed ? (
                    <span className="text-green-600">✓</span>
                  ) : (
                    <span className="text-muted-foreground/40">—</span>
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── page ─────────────────────────────────────────────────────────────────────

export function DocsPage() {
  const [activeSection, setActiveSection] = React.useState('overview')

  // Highlight the active TOC entry as the user scrolls
  React.useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActiveSection(entry.target.id)
        }
      },
      { rootMargin: '-20% 0px -70% 0px' },
    )
    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })
    return () => observer.disconnect()
  }, [])

  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <div className="flex gap-10">
      {/* Sticky TOC */}
      <aside className="hidden w-44 shrink-0 xl:block">
        <div className="sticky top-4 space-y-1">
          <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            On this page
          </p>
          {SECTIONS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => scrollTo(id)}
              className={cn(
                'block w-full rounded px-2 py-1 text-left text-sm transition-colors',
                activeSection === id
                  ? 'bg-primary/10 font-medium text-primary'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {label}
            </button>
          ))}
        </div>
      </aside>

      {/* Content */}
      <div className="min-w-0 flex-1 space-y-12">
        <div>
          <h1 className="text-3xl font-bold">Documentation</h1>
          <p className="mt-1 text-muted-foreground">
            A complete guide to using LedgerWatch — features, workflows, and constraints.
          </p>
        </div>

        {/* ── Overview ───────────────────────────────────────────────────── */}
        <Section id="overview" title="Overview">
          <p>
            LedgerWatch is a multi-tenant financial monitoring platform. It lets your organization
            track transactions, detect anomalies through automated analysis, and manage alerts
            generated by those analyses. Every piece of data is scoped to your organization —
            other organizations cannot see your data.
          </p>
          <p>
            The platform is built around a simple workflow:{' '}
            <strong className="text-foreground">import transactions → run analysis → review alerts</strong>.
          </p>
        </Section>

        {/* ── Getting Started ────────────────────────────────────────────── */}
        <Section id="getting-started" title="Getting Started">
          <Sub title="Creating an Account">
            <p>Navigate to the <strong className="text-foreground">Sign Up</strong> page to register.</p>
            <ul className="mt-3 space-y-2 pl-1">
              <Step n={1}>Enter your organization's name. It must be globally unique — registration fails if another organization already uses it.</Step>
              <Step n={2}>Enter your email address. The part before the <code className="rounded bg-muted px-1 py-0.5 text-xs">@</code> determines your role: if it is exactly <code className="rounded bg-muted px-1 py-0.5 text-xs">owner</code> (e.g. <code className="rounded bg-muted px-1 py-0.5 text-xs">owner@acme.com</code>), you become the organization <Badge color="border-purple-300 text-purple-700 bg-purple-50">Owner</Badge>. Any other prefix makes you an <Badge color="border-gray-300 text-gray-600">Employee</Badge>.</Step>
              <Step n={3}>Choose a password and submit.</Step>
            </ul>
            <Note variant="warn">
              Each organization should be created by its owner using an <code className="rounded bg-muted px-1 py-0.5 text-xs">owner@…</code> email. Admins and employees are added afterward from the <strong>Manage Org</strong> page.
            </Note>
          </Sub>

          <Sub title="Signing In">
            <p>
              Enter your email and password on the <strong className="text-foreground">Login</strong> page.
              Check <em>Keep me signed in for 7 days</em> to persist your session using a long-lived
              refresh token stored in your browser. Without it, your session ends when you close the tab.
            </p>
          </Sub>

          <Sub title="Session & Tokens">
            <ul className="list-inside list-disc space-y-1 pl-2">
              <li>Access tokens expire after <strong className="text-foreground">30 minutes</strong> and are refreshed automatically in the background.</li>
              <li>Refresh tokens last <strong className="text-foreground">7 days</strong> and rotate on each use.</li>
              <li>Logging out immediately invalidates your refresh token so no further auto-refresh can occur.</li>
            </ul>
          </Sub>
        </Section>

        {/* ── Dashboard ──────────────────────────────────────────────────── */}
        <Section id="dashboard" title="Dashboard">
          <p>
            The Dashboard gives you a real-time snapshot of your organization's financial health.
            Click the <strong className="text-foreground">LedgerWatch</strong> logo at the top of the
            sidebar at any time to return here.
          </p>

          <Sub title="Summary Cards">
            <p>Four cards at the top show:</p>
            <ul className="list-inside list-disc space-y-1 pl-2">
              <li><strong className="text-foreground">Total Transactions</strong> — count of all transactions in the org.</li>
              <li><strong className="text-foreground">Total Spend</strong> — sum of all transaction amounts.</li>
              <li><strong className="text-foreground">Open Alerts</strong> — alerts with status OPEN.</li>
              <li><strong className="text-foreground">Analyses Run</strong> — total number of analysis runs completed.</li>
            </ul>
          </Sub>

          <Sub title="Spend Over Time Graph">
            <p>
              A bar chart showing your monthly spending. Hover over a bar to see the exact
              amount for that month. Only the most recent months with data are displayed.
            </p>
          </Sub>

          <Sub title="Recent Alerts">
            <p>
              A table of the five most recent open alerts with severity and message. Click
              through to the Alerts page to take action.
            </p>
          </Sub>
        </Section>

        {/* ── Transactions ───────────────────────────────────────────────── */}
        <Section id="transactions" title="Transactions">
          <p>
            Transactions are the core data unit. Every transaction belongs to your organization
            and has a date, vendor, amount, and optional category and description.
          </p>

          <Sub title="Adding a Single Transaction">
            <p>Click <strong className="text-foreground">Add Transaction</strong> (top-right). Fill in:</p>
            <ul className="list-inside list-disc space-y-1 pl-2">
              <li><strong className="text-foreground">Date</strong> — required, pick from the calendar.</li>
              <li><strong className="text-foreground">Vendor</strong> — required, free text.</li>
              <li><strong className="text-foreground">Amount</strong> — required, must be greater than 0, up to 2 decimal places.</li>
              <li><strong className="text-foreground">Category</strong> — optional. Use <code className="rounded bg-muted px-1 py-0.5 text-xs">Revenue</code> (exact) to have the burn-rate analyzer treat the transaction as income.</li>
              <li><strong className="text-foreground">Description</strong> — optional notes.</li>
            </ul>
            <ul className="mt-3 space-y-1 pl-1">
              <Constraint>Amount must be a positive number — zero or negative values are rejected.</Constraint>
              <Constraint>Amounts are stored with 2 decimal places (e.g. 1234.56). Values with more decimal places are rounded by the server.</Constraint>
            </ul>
          </Sub>

          <Sub title="Importing via CSV">
            <p>Click <strong className="text-foreground">Import CSV</strong> to open the 4-step import wizard.</p>
            <ol className="mt-3 space-y-2 pl-1">
              <Step n={1}><strong className="text-foreground">Upload</strong> — drag and drop or browse for a <code className="rounded bg-muted px-1 py-0.5 text-xs">.csv</code> file (max 5 MB).</Step>
              <Step n={2}><strong className="text-foreground">Map Columns</strong> — tell LedgerWatch which CSV columns correspond to Date, Vendor, Amount, Category, and Description. Required: Date, Vendor, Amount.</Step>
              <Step n={3}><strong className="text-foreground">Preview & Confirm</strong> — rows with errors (missing vendor, invalid date, non-positive amount) are highlighted and skipped on import. Valid rows are shown in green.</Step>
              <Step n={4}><strong className="text-foreground">Done</strong> — a summary shows how many transactions were imported.</Step>
            </ol>
            <ul className="mt-3 space-y-1 pl-1">
              <Constraint>Only <code className="rounded bg-muted px-1 py-0.5 text-xs">.csv</code> files are accepted. Excel <code className="rounded bg-muted px-1 py-0.5 text-xs">.xlsx</code> must be exported to CSV first.</Constraint>
              <Constraint>The date column must parse as a valid date (ISO format <code className="rounded bg-muted px-1 py-0.5 text-xs">YYYY-MM-DD</code> is safest).</Constraint>
              <Constraint>Invalid rows are silently skipped — they are not imported but do not block valid rows.</Constraint>
            </ul>
          </Sub>

          <Sub title="Filtering & Sorting">
            <p>Use the filter bar to narrow results by vendor, category, or date range. Clicking <strong className="text-foreground">Date</strong> or <strong className="text-foreground">Amount</strong> column headers cycles through descending → ascending → default sort. Filters are preserved in the URL, so you can share or bookmark a filtered view.</p>
          </Sub>

          <Sub title="Viewing Details">
            <p>Click any row to expand an inline detail panel showing the full record including its internal ID and creation timestamp.</p>
          </Sub>

          <Sub title="Deleting a Transaction">
            <p>Expand a row and click <strong className="text-foreground">Delete</strong> in the detail panel.</p>
            <ul className="mt-2 space-y-1 pl-1">
              <Constraint>Only <Badge color="border-blue-300 text-blue-700 bg-blue-50">Admin</Badge> and <Badge color="border-purple-300 text-purple-700 bg-purple-50">Owner</Badge> roles can delete transactions.</Constraint>
            </ul>
          </Sub>

          <Sub title="Rows per Page">
            <p>Use the <strong className="text-foreground">Rows per page</strong> dropdown at the bottom of the table to display 25, 50, 100, or all transactions at once. The setting is saved in the URL.</p>
            <Note variant="tip">Selecting <strong>All</strong> fetches every row in the dataset. For very large datasets, use filters to narrow results before selecting All.</Note>
          </Sub>
        </Section>

        {/* ── Analysis ───────────────────────────────────────────────────── */}
        <Section id="analysis" title="Analysis">
          <p>
            Analysis runs automated checks against your transaction data and generates alerts for
            detected anomalies. Each run is atomic — it either fully succeeds or is recorded as
            failed with an error message.
          </p>
          <Note variant="warn">
            Running analysis requires <Badge color="border-blue-300 text-blue-700 bg-blue-50">Admin</Badge> or <Badge color="border-purple-300 text-purple-700 bg-purple-50">Owner</Badge> role.
          </Note>

          <Sub title="How to Run">
            <ol className="space-y-2 pl-1">
              <Step n={1}>Go to the <strong className="text-foreground">Analysis</strong> page.</Step>
              <Step n={2}>Select an analysis type from the dropdown.</Step>
              <Step n={3}>Click <strong className="text-foreground">Run Analysis</strong>. The result appears in the history table below.</Step>
            </ol>
          </Sub>

          <Sub title="Analysis Types">
            <div className="space-y-4">
              <div className="rounded-lg border p-4">
                <p className="font-medium text-foreground">Large Transaction</p>
                <p className="mt-1">Flags individual transactions that are unusually large compared to your typical spending.</p>
                <ul className="mt-2 space-y-1 pl-2">
                  <li>Amount &gt; 5× the mean → <Badge color="bg-red-100 text-red-700 border-red-200">HIGH</Badge> alert</li>
                  <li>Amount &gt; a calculated threshold → <Badge color="bg-amber-100 text-amber-700 border-amber-200">MEDIUM</Badge> alert</li>
                </ul>
              </div>
              <div className="rounded-lg border p-4">
                <p className="font-medium text-foreground">Burn Rate</p>
                <p className="mt-1">Calculates your monthly net burn (expenses minus revenue) and projects your runway.</p>
                <ul className="mt-2 space-y-1 pl-2">
                  <li>Runway &lt; 3 months → <Badge color="bg-red-100 text-red-700 border-red-200">HIGH</Badge></li>
                  <li>Runway 3–6 months → <Badge color="bg-amber-100 text-amber-700 border-amber-200">MEDIUM</Badge></li>
                  <li>Net burn &gt; 0 (spending more than earning) → <Badge color="bg-blue-100 text-blue-700 border-blue-200">LOW</Badge></li>
                </ul>
                <Note variant="info">Only transactions with category exactly equal to <code className="rounded bg-muted px-1 py-0.5 text-xs">Revenue</code> are counted as income. All others are treated as expenses.</Note>
              </div>
              <div className="rounded-lg border p-4">
                <p className="font-medium text-foreground">Vendor Spike</p>
                <p className="mt-1">Compares spending per vendor between the two most recent calendar months and flags sudden increases.</p>
                <ul className="mt-2 space-y-1 pl-2">
                  <li>Month-over-month increase ≥ 50% → <Badge color="bg-amber-100 text-amber-700 border-amber-200">MEDIUM</Badge></li>
                  <li>New vendor (no prior month data) or 25–50% increase → <Badge color="bg-blue-100 text-blue-700 border-blue-200">LOW</Badge></li>
                </ul>
              </div>
              <div className="rounded-lg border p-4">
                <p className="font-medium text-foreground">Duplicate Transaction</p>
                <p className="mt-1">Detects transactions with the same vendor and amount recorded within a 48-hour window.</p>
                <ul className="mt-2 space-y-1 pl-2">
                  <li>Any duplicate group → <Badge color="bg-blue-100 text-blue-700 border-blue-200">LOW</Badge> alert</li>
                </ul>
                <Note variant="info">The 48-hour window uses the record creation timestamp, not the transaction date.</Note>
              </div>
            </div>
          </Sub>

          <Sub title="Run History">
            <p>
              All past runs are listed with their type, status (<span className="font-medium text-muted-foreground">PENDING</span> / <span className="font-medium text-green-600">SUCCEEDED</span> / <span className="font-medium text-red-600">FAILED</span>), timestamp, and a summary of findings.
              Failed runs store the error message for debugging.
            </p>
          </Sub>
        </Section>

        {/* ── Alerts ─────────────────────────────────────────────────────── */}
        <Section id="alerts" title="Alerts">
          <p>
            Alerts are created automatically by analysis runs. Each alert has a severity, type,
            message, and a lifecycle status.
          </p>

          <Sub title="Alert Lifecycle">
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
              <Badge color="border-gray-300 text-gray-600">OPEN</Badge>
              <span className="text-muted-foreground">→</span>
              <Badge color="border-yellow-400 text-yellow-700">ACKNOWLEDGED</Badge>
              <span className="text-muted-foreground">→</span>
              <Badge color="border-green-500 text-green-700">RESOLVED</Badge>
              <span className="text-muted-foreground">→ (reopen) →</span>
              <Badge color="border-gray-300 text-gray-600">OPEN</Badge>
            </div>
            <ul className="mt-3 space-y-1 pl-2">
              <li><strong className="text-foreground">Acknowledge</strong> — marks the alert as seen; it stays visible for tracking.</li>
              <li><strong className="text-foreground">Resolve</strong> — marks the issue as handled.</li>
              <li><strong className="text-foreground">Reopen</strong> — moves a resolved alert back to OPEN if the issue recurs.</li>
            </ul>
            <ul className="mt-3 space-y-1 pl-1">
              <Constraint>Acknowledging, resolving, reopening, and deleting alerts requires <Badge color="border-blue-300 text-blue-700 bg-blue-50">Admin</Badge> or <Badge color="border-purple-300 text-purple-700 bg-purple-50">Owner</Badge> role.</Constraint>
              <Constraint>You cannot acknowledge an alert that is already ACKNOWLEDGED; you cannot resolve an alert that is already RESOLVED.</Constraint>
            </ul>
          </Sub>

          <Sub title="Bulk Acknowledge">
            <p>
              Use the checkbox in each row (only available for OPEN alerts) to select multiple alerts,
              then click <strong className="text-foreground">Acknowledge selected (n)</strong> to
              acknowledge them all in one action.
            </p>
          </Sub>

          <Sub title="Filtering & Sorting">
            <p>Filter alerts by status (All / OPEN / ACKNOWLEDGED / RESOLVED), severity (All / HIGH / MEDIUM / LOW), and type. Click the <strong className="text-foreground">Created</strong> column header to toggle sort direction.</p>
          </Sub>

          <Sub title="Rows per Page">
            <p>Use the <strong className="text-foreground">Rows per page</strong> dropdown at the bottom to display 25, 50, 100, or all alerts. The setting is preserved in the URL.</p>
          </Sub>
        </Section>

        {/* ── Settings ───────────────────────────────────────────────────── */}
        <Section id="settings" title="Settings">
          <p>Access your personal and organization settings from the <strong className="text-foreground">Settings</strong> page in the sidebar.</p>

          <Sub title="Profile">
            <p>Update your first and last name. Your email address cannot be changed after registration.</p>
          </Sub>

          <Sub title="Change Password">
            <p>Enter your current password to verify identity, then enter and confirm a new password.</p>
            <ul className="mt-2 space-y-1 pl-1">
              <Constraint>Changing your password immediately invalidates all existing refresh tokens across all devices. You will be logged out and must sign in again.</Constraint>
            </ul>
          </Sub>

          <Sub title="Organization Name">
            <p>Owners can rename the organization from this page.</p>
            <ul className="mt-2 space-y-1 pl-1">
              <Constraint>Organization names must be globally unique. If the name is already taken, the update will fail.</Constraint>
              <Constraint>Only the <Badge color="border-purple-300 text-purple-700 bg-purple-50">Owner</Badge> can rename the organization.</Constraint>
            </ul>
          </Sub>
        </Section>

        {/* ── Organization ───────────────────────────────────────────────── */}
        <Section id="organization" title="Organization Management">
          <Note variant="warn">
            The full Manage Org page is only visible to <Badge color="border-purple-300 text-purple-700 bg-purple-50">Owner</Badge> accounts. Other roles can view the member directory from <strong>See Organization</strong> in the sidebar.
          </Note>

          <Sub title="Adding Members">
            <p>Owners can invite new members by entering their email and assigning them a role of <Badge color="border-blue-300 text-blue-700 bg-blue-50">Admin</Badge> or <Badge color="border-gray-300 text-gray-600">Employee</Badge>.</p>
            <ul className="mt-2 space-y-1 pl-1">
              <Constraint>The new member's email must not already be registered in the system.</Constraint>
              <Constraint>You cannot add a second Owner — there is always exactly one owner per organization.</Constraint>
              <Constraint>New members receive credentials through an out-of-band process (share the password you set for them directly).</Constraint>
            </ul>
          </Sub>

          <Sub title="Changing Member Roles">
            <p>Owners can promote an Employee to Admin or demote an Admin to Employee.</p>
            <ul className="mt-2 space-y-1 pl-1">
              <Constraint>The owner's own role cannot be changed here — use Transfer Ownership instead.</Constraint>
            </ul>
          </Sub>

          <Sub title="Removing Members">
            <p>Owners can remove any member from the organization.</p>
            <ul className="mt-2 space-y-1 pl-1">
              <Constraint>You cannot remove yourself (the owner).</Constraint>
              <Constraint>Removing a member immediately invalidates all their sessions.</Constraint>
            </ul>
          </Sub>

          <Sub title="Transfer Ownership">
            <p>The owner can transfer their role to an existing Admin. This is an irreversible action:</p>
            <ol className="mt-2 space-y-2 pl-1">
              <Step n={1}>The selected Admin is promoted to Owner and their email is updated to <code className="rounded bg-muted px-1 py-0.5 text-xs">owner@&lt;their-domain&gt;</code>.</Step>
              <Step n={2}>Your account is permanently deleted and all your sessions are invalidated.</Step>
              <Step n={3}>You are redirected to the login page.</Step>
            </ol>
            <Note variant="warn">
              Ownership transfer is permanent. Once completed, the previous owner's account no longer exists and cannot be recovered.
            </Note>
          </Sub>
        </Section>

        {/* ── Roles ──────────────────────────────────────────────────────── */}
        <Section id="roles" title="Roles & Permissions">
          <p>Every user in LedgerWatch has one of three roles. Roles control what actions are available in the UI and are enforced independently on the server.</p>

          <div className="mt-4 flex flex-wrap gap-4 text-sm">
            <div className="flex items-center gap-2">
              <Badge color="border-purple-300 text-purple-700 bg-purple-50">Owner</Badge>
              <span>— Full access, one per organization.</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge color="border-blue-300 text-blue-700 bg-blue-50">Admin</Badge>
              <span>— Operational access; no member management.</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge color="border-gray-300 text-gray-600">Employee</Badge>
              <span>— Read access; can import transactions.</span>
            </div>
          </div>

          <div className="mt-6">
            <PermTable />
          </div>
        </Section>
      </div>
    </div>
  )
}
