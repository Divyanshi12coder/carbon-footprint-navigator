import { useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { ArrowLeft, ArrowRight, Building2, CheckCircle2 } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { profileApi } from '../api/endpoints'
import { FieldInput, PROFILE_STEPS, validateProfileField } from '../components/profile/profileFields'
import { Button } from '../components/ui/Button'
import { CardSkeleton } from '../components/ui/feedback'
import { Logo, ProgressBar } from '../components/ui/misc'
import { useAuth } from '../hooks/useAuth'
import type { OnboardingInput } from '../types/api'
import { categoryColor, categoryLabel } from '../utils/categories'
import { errorMessage, formatKg } from '../utils/format'

export default function OnboardingPage() {
  const { user, setUser } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [data, setData] = useState<OnboardingInput>({})
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)
  const total = PROFILE_STEPS.length + 1

  const baseline = useQuery({ queryKey: ['baseline'], queryFn: profileApi.baseline, enabled: done })

  const current = PROFILE_STEPS[step]
  const stepErrors = current ? current.fields.map((f) => validateProfileField(f, data[f.key])).filter(Boolean) : []

  const submit = async () => {
    setSaving(true)
    try {
      const clean = Object.fromEntries(Object.entries(data).filter(([, v]) => v !== null && v !== undefined && v !== '')) as OnboardingInput
      const updated = await profileApi.onboarding(clean)
      setUser(updated)
      setDone(true)
    } catch (err) {
      toast.error(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const next = () => (step < total - 1 ? setStep(step + 1) : submit())

  return (
    <div className="min-h-screen bg-gradient-to-b from-mint/60 to-offwhite px-4 py-8">
      <div className="mx-auto max-w-2xl">
        <Logo />
        {!done ? (
          <>
            <div className="mt-8 mb-6">
              <p className="eyebrow">Step {step + 1} of {total}</p>
              <ProgressBar value={((step + 1) / total) * 100} label="Onboarding progress" />
            </div>
            <AnimatePresence mode="wait">
              <motion.section key={step} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }}
                className="card p-6 sm:p-8" aria-labelledby="step-title">
                {current ? (
                  <>
                    <current.icon className="h-7 w-7 text-brand" aria-hidden />
                    <h1 id="step-title" className="mt-3 text-2xl font-bold text-forest">{current.title}</h1>
                    <p className="mt-1 text-sm text-muted">{current.description} Every question is optional.</p>
                    <div className="mt-6 grid gap-4 sm:grid-cols-2">
                      {current.fields.map((f) => (
                        <div key={f.key} className={f.type === 'boolean' ? 'sm:col-span-2' : ''}>
                          <FieldInput field={f} value={data[f.key]} onChange={(v) => setData({ ...data, [f.key]: v })} />
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <>
                    <Building2 className="h-7 w-7 text-brand" aria-hidden />
                    <h1 id="step-title" className="mt-3 text-2xl font-bold text-forest">Tracking for an organisation?</h1>
                    <p className="mt-1 text-sm text-muted">
                      Optional. Creates a company workspace where you and colleagues can log business travel and office energy.
                      You can also join an existing organisation later with a join code.
                    </p>
                    <div className="mt-6 grid gap-4 sm:grid-cols-2">
                      <div className="sm:col-span-2">
                        <label htmlFor="org-name" className="label">Organisation name</label>
                        <input id="org-name" className="input" maxLength={160} value={data.organization_name ?? ''}
                          onChange={(e) => setData({ ...data, organization_name: e.target.value || undefined })} />
                      </div>
                      <div>
                        <label htmlFor="org-industry" className="label">Industry</label>
                        <input id="org-industry" className="input" maxLength={120} value={data.organization_industry ?? ''}
                          onChange={(e) => setData({ ...data, organization_industry: e.target.value || undefined })} />
                      </div>
                      <div>
                        <label htmlFor="org-size" className="label">Employees</label>
                        <input id="org-size" type="number" min={1} className="input" value={data.organization_employee_count ?? ''}
                          onChange={(e) => setData({ ...data, organization_employee_count: e.target.value ? Number(e.target.value) : undefined })} />
                      </div>
                    </div>
                  </>
                )}
                {stepErrors.length > 0 && <p role="alert" className="mt-4 text-sm text-red-600">{stepErrors[0]}</p>}
                <div className="mt-8 flex items-center justify-between gap-3">
                  <Button variant="ghost" onClick={() => setStep(step - 1)} disabled={step === 0} icon={<ArrowLeft className="h-4 w-4" />}>Back</Button>
                  <div className="flex gap-2">
                    <Button variant="secondary" onClick={next} disabled={saving}>Skip</Button>
                    <Button onClick={next} loading={saving} disabled={stepErrors.length > 0} icon={step === total - 1 ? <CheckCircle2 className="h-4 w-4" /> : <ArrowRight className="h-4 w-4" />}>
                      {step === total - 1 ? 'Finish' : 'Continue'}
                    </Button>
                  </div>
                </div>
              </motion.section>
            </AnimatePresence>
          </>
        ) : (
          <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="card mt-8 p-6 sm:p-8">
            <CheckCircle2 className="h-8 w-8 text-brand" aria-hidden />
            <h1 className="mt-3 text-2xl font-bold text-forest">You’re set up, {user?.full_name.split(' ')[0]}</h1>
            {baseline.isLoading ? (
              <CardSkeleton className="mt-6" rows={4} />
            ) : baseline.data && baseline.data.basis !== 'none' ? (
              <>
                <p className="mt-2 text-sm text-muted">Estimated from your answers using the same emission factors as the calculation engine:</p>
                <p className="mt-4 font-display text-4xl font-extrabold text-forest">{formatKg(baseline.data.monthly_total_kg)}<span className="text-lg font-semibold text-muted"> CO₂e / month</span></p>
                <p className="text-sm text-muted">≈ {formatKg(baseline.data.annual_total_kg)} per year</p>
                <ul className="mt-5 space-y-2">
                  {Object.entries(baseline.data.by_category_monthly_kg).sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0)).map(([c, kg]) => (
                    <li key={c} className="flex items-center justify-between text-sm">
                      <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-sm" style={{ background: categoryColor(c) }} />{categoryLabel(c)}</span>
                      <span className="font-semibold tabular-nums">{formatKg(kg ?? 0)}</span>
                    </li>
                  ))}
                </ul>
                {baseline.data.assumptions.length > 0 && (
                  <details className="mt-4 text-xs text-muted"><summary className="cursor-pointer font-medium">Assumptions used</summary>
                    <ul className="mt-2 list-disc space-y-1 pl-5">{baseline.data.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
                  </details>
                )}
              </>
            ) : (
              <p className="mt-2 text-sm text-muted">You skipped the questions, so there’s no estimate yet — logging activities will build your real footprint.</p>
            )}
            <Button className="mt-8" size="lg" onClick={() => navigate('/app/activities', { replace: true })} icon={<ArrowRight className="h-4 w-4" />}>
              Log your first activity
            </Button>
            <Button className="mt-8 ml-2" size="lg" variant="secondary" onClick={() => navigate('/app', { replace: true })}>Go to dashboard</Button>
          </motion.section>
        )}
      </div>
    </div>
  )
}
