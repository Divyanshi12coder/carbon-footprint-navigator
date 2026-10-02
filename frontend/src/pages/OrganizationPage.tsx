import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, Copy, LogOut, Users } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { authApi, orgApi, type RangeParams } from '../api/endpoints'
import { CategoryDonut, CategoryStackedBars } from '../charts/CategoryCharts'
import { CategoryLegend } from '../charts/common'
import { KpiCard, Panel } from '../components/dashboard/cards'
import { Button } from '../components/ui/Button'
import { CardSkeleton, ChartSkeleton, EmptyState, ErrorState } from '../components/ui/feedback'
import { PageHeader } from '../components/ui/misc'
import { RangeFilter } from '../components/ui/RangeFilter'
import { useAuth } from '../hooks/useAuth'
import { activityLabel, presentCategories } from '../utils/categories'
import { errorMessage, formatKg, formatPct } from '../utils/format'

function NoOrganization() {
  const { setUser } = useAuth()
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [industry, setIndustry] = useState('')
  const [code, setCode] = useState('')
  const done = async () => {
    setUser(await authApi.me())
    qc.invalidateQueries({ queryKey: ['org'] })
  }
  const create = useMutation({ mutationFn: () => orgApi.create({ name, industry: industry || undefined }), onSuccess: async () => { await done(); toast.success('Organisation created') }, onError: (e) => toast.error(errorMessage(e)) })
  const join = useMutation({ mutationFn: () => orgApi.join(code), onSuccess: async (o) => { await done(); toast.success(`Joined ${o.name}`) }, onError: (e) => toast.error(errorMessage(e)) })
  return (
    <div className="grid gap-6 md:grid-cols-2">
      <Panel title="Create an organisation" subtitle="You become the owner and receive a join code to share.">
        <form className="space-y-3" onSubmit={(e: FormEvent) => { e.preventDefault(); if (name.trim().length >= 2) create.mutate() }}>
          <div><label htmlFor="o-name" className="label">Name</label><input id="o-name" className="input" maxLength={160} value={name} onChange={(e) => setName(e.target.value)} /></div>
          <div><label htmlFor="o-ind" className="label">Industry (optional)</label><input id="o-ind" className="input" maxLength={120} value={industry} onChange={(e) => setIndustry(e.target.value)} /></div>
          <Button type="submit" loading={create.isPending} disabled={name.trim().length < 2} icon={<Building2 className="h-4 w-4" />}>Create</Button>
        </form>
      </Panel>
      <Panel title="Join with a code" subtitle="Ask your organisation owner for the join code.">
        <form className="space-y-3" onSubmit={(e: FormEvent) => { e.preventDefault(); if (code.trim().length >= 6) join.mutate() }}>
          <div><label htmlFor="o-code" className="label">Join code</label><input id="o-code" className="input uppercase tracking-widest" maxLength={16} value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} /></div>
          <Button type="submit" variant="secondary" loading={join.isPending} disabled={code.trim().length < 6} icon={<Users className="h-4 w-4" />}>Join</Button>
        </form>
      </Panel>
    </div>
  )
}

export default function OrganizationPage() {
  const { user, setUser } = useAuth()
  const qc = useQueryClient()
  const [range, setRange] = useState<RangeParams>({ range: '90d' })
  const inOrg = Boolean(user?.organization)
  const org = useQuery({ queryKey: ['org'], queryFn: orgApi.mine, enabled: inOrg })
  const members = useQuery({ queryKey: ['org', 'members'], queryFn: orgApi.members, enabled: inOrg })
  const dash = useQuery({ queryKey: ['org-dashboard', range], queryFn: () => orgApi.dashboard(range), enabled: inOrg })
  const leave = useMutation({
    mutationFn: orgApi.leave,
    onSuccess: async () => { setUser(await authApi.me()); qc.removeQueries({ queryKey: ['org'] }); toast.success('You left the organisation') },
    onError: (e) => toast.error(errorMessage(e)),
  })

  if (!inOrg) {
    return (
      <div>
        <PageHeader eyebrow="Organisation mode" title="Organisation" description="Track business travel, office energy and company activities as a shared footprint." />
        <NoOrganization />
      </div>
    )
  }

  const d = dash.data
  return (
    <div>
      <PageHeader eyebrow="Organisation mode" title={org.data?.name ?? user!.organization!.name}
        description="Built from activities members log “for the organisation”. Personal activities are never included."
        actions={<RangeFilter value={range} onChange={setRange} />} />
      {org.data?.join_code && (
        <div className="mb-6 flex flex-wrap items-center gap-3 rounded-2xl border border-algae-light/60 bg-mint/50 p-4 text-sm">
          <span>Join code for colleagues:</span>
          <code className="rounded-lg bg-white px-3 py-1 font-bold tracking-widest text-forest">{org.data.join_code}</code>
          <Button size="sm" variant="ghost" icon={<Copy className="h-4 w-4" />} onClick={() => { void navigator.clipboard?.writeText(org.data!.join_code!); toast.success('Copied') }}>Copy</Button>
        </div>
      )}
      {dash.error ? <div className="card"><ErrorState error={dash.error} onRetry={() => dash.refetch()} /></div> : dash.isLoading || !d ? <CardSkeleton rows={6} /> : d.totals.activity_count === 0 ? (
        <div className="card"><EmptyState icon={<Building2 className="h-6 w-6" />} title="No organisation activities yet"
          body="When logging an activity, tick “Log for organisation” to add business travel or office energy here." /></div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard highlight label={`Company total · ${d.range.days} days`} kg={d.totals.total_kg}
              footer={<span className="text-xs text-white/85">{d.totals.change_pct === null ? 'No previous data' : `${formatPct(d.totals.change_pct, true)} vs previous period`}</span>} />
            <KpiCard label="Monthly equivalent" kg={d.totals.monthly_equivalent_kg} />
            <KpiCard label="Weekly average" kg={d.totals.weekly_average_kg} />
            <KpiCard label="Annualised" kg={d.totals.annualized_kg} footer={<span className="text-xs text-muted">{d.totals.activity_count} activities</span>} />
          </div>
          <div className="mt-6 grid gap-6 xl:grid-cols-3">
            <Panel className="xl:col-span-2" title="Monthly trend" actions={<CategoryLegend categories={presentCategories(d.monthly.flatMap((m) => Object.keys(m)))} />}>
              <CategoryStackedBars data={d.monthly} xKey="month" granularity="month" />
            </Panel>
            <Panel title="Category breakdown"><CategoryDonut rows={d.categories} /></Panel>
          </div>
          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <Panel title="By activity">
              <ul className="divide-y divide-line text-sm">
                {d.by_activity.map((b) => (
                  <li key={`${b.activity_type}-${b.factor_key}`} className="flex justify-between py-2"><span>{activityLabel(b.activity_type)} <span className="text-xs text-muted">· {b.factor_key}</span></span><span className="font-semibold tabular-nums">{formatKg(b.kg)}</span></li>
                ))}
              </ul>
            </Panel>
            <Panel title="Members" subtitle="Contribution to organisation activities (all time)">
              {members.isLoading ? <ChartSkeleton height={100} /> : (
                <ul className="divide-y divide-line text-sm">
                  {(members.data ?? []).map((m) => (
                    <li key={m.user_id} className="flex justify-between py-2"><span>{m.full_name} <span className="text-xs text-muted">· {m.org_role}</span></span><span className="tabular-nums">{formatKg(m.contributed_kg)} · {m.activity_count} activities</span></li>
                  ))}
                </ul>
              )}
            </Panel>
          </div>
        </>
      )}
      <div className="mt-8">
        <Button variant="ghost" loading={leave.isPending} onClick={() => leave.mutate()} icon={<LogOut className="h-4 w-4" />}>Leave organisation</Button>
      </div>
    </div>
  )
}
