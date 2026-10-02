import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Save } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { profileApi } from '../api/endpoints'
import { Panel } from '../components/dashboard/cards'
import { FieldInput, PROFILE_STEPS, validateProfileField } from '../components/profile/profileFields'
import { Button } from '../components/ui/Button'
import { CardSkeleton, ErrorState } from '../components/ui/feedback'
import { PageHeader } from '../components/ui/misc'
import { useAuth } from '../hooks/useAuth'
import type { ProfileInput } from '../types/api'
import { categoryLabel } from '../utils/categories'
import { errorMessage, formatKg } from '../utils/format'

function ProfileForm({ initial }: { initial: ProfileInput }) {
  const qc = useQueryClient()
  const [form, setForm] = useState<ProfileInput>(initial)

  const errors = PROFILE_STEPS.flatMap((s) => s.fields).map((f) => validateProfileField(f, form[f.key])).filter(Boolean)
  const save = useMutation({
    mutationFn: () => profileApi.update(form),
    onSuccess: (p) => {
      qc.setQueryData(['profile'], p)
      ;['baseline', 'scenario-baseline', 'scenario', 'recommendations'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }))
      toast.success('Profile saved — estimates updated')
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  return (
          <form onSubmit={(e: FormEvent) => { e.preventDefault(); if (!errors.length) save.mutate() }} className="space-y-6">
            {PROFILE_STEPS.map((step) => (
              <Panel key={step.title} title={step.title} subtitle={step.description}>
                <div className="grid gap-4 sm:grid-cols-2">
                  {step.fields.map((f) => (
                    <div key={f.key} className={f.type === 'boolean' ? 'sm:col-span-2' : ''}>
                      <FieldInput field={f} value={form[f.key]} onChange={(v) => setForm({ ...form, [f.key]: v })} />
                    </div>
                  ))}
                </div>
              </Panel>
            ))}
            {errors.length > 0 && <p role="alert" className="text-sm text-red-600">{errors[0]}</p>}
            <Button type="submit" size="lg" loading={save.isPending} disabled={errors.length > 0} icon={<Save className="h-4 w-4" />}>Save profile</Button>
          </form>
  )
}

export default function ProfilePage() {
  const { user } = useAuth()
  const profile = useQuery({ queryKey: ['profile'], queryFn: profileApi.get })
  const baseline = useQuery({ queryKey: ['baseline'], queryFn: profileApi.baseline })

  return (
    <div>
      <PageHeader eyebrow="Profile" title={user?.full_name ?? 'Profile'} description={`${user?.email} · these answers drive your estimates until you’ve tracked enough activities.`} />
      {profile.error ? <div className="card"><ErrorState error={profile.error} onRetry={() => profile.refetch()} /></div> : profile.isLoading ? <CardSkeleton rows={8} /> : (
        <div className="grid gap-6 xl:grid-cols-[1fr_320px]">
          <ProfileForm initial={profile.data ?? {}} />
          <Panel className="h-fit xl:sticky xl:top-6" title="Estimate from your answers" subtitle="Onboarding-based, monthly">
            {baseline.isLoading ? <CardSkeleton rows={3} /> : baseline.data && baseline.data.basis !== 'none' ? (
              <>
                <p className="font-display text-3xl font-extrabold text-forest">{formatKg(baseline.data.monthly_total_kg)}</p>
                <p className="text-xs text-muted">≈ {formatKg(baseline.data.annual_total_kg)} per year</p>
                <ul className="mt-3 space-y-1 text-sm">
                  {Object.entries(baseline.data.by_category_monthly_kg).map(([c, kg]) => (
                    <li key={c} className="flex justify-between"><span>{categoryLabel(c)}</span><span className="tabular-nums">{formatKg(kg ?? 0)}</span></li>
                  ))}
                </ul>
              </>
            ) : <p className="text-sm text-muted">Answer a few questions to see an estimate.</p>}
          </Panel>
        </div>
      )}
    </div>
  )
}
