import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { FlaskConical, Loader2, RotateCcw } from 'lucide-react'
import { useState } from 'react'

import { mlApi } from '../api/endpoints'
import { images } from '../assets/images'
import { ScenarioCompareChart } from '../charts/CategoryCharts'
import { Panel } from '../components/dashboard/cards'
import { Button, ButtonLink } from '../components/ui/Button'
import { CardSkeleton, EmptyState, ErrorState } from '../components/ui/feedback'
import { AnimatedNumber, PageHeader, ProgressBar } from '../components/ui/misc'
import { useDebounce } from '../hooks/useDebounce'
import type { ScenarioLevers } from '../types/api'
import { formatKg, formatPct } from '../utils/format'

const ZERO: ScenarioLevers = {
  car_reduction_pct: 0, ev_adoption_pct: 0, flight_reduction_pct: 0, electricity_reduction_pct: 0,
  renewable_share_pct: 0, heating_reduction_pct: 0, meat_reduction_pct: 0, recycling_improvement_pct: 0,
}

const LEVERS: { key: keyof ScenarioLevers; label: string; help: string }[] = [
  { key: 'car_reduction_pct', label: 'Drive less', help: 'Cut car kilometres by this share.' },
  { key: 'ev_adoption_pct', label: 'Switch car km to an EV', help: 'Share of remaining combustion-car km driven electric.' },
  { key: 'flight_reduction_pct', label: 'Fly less', help: 'Reduce flight passenger-km.' },
  { key: 'electricity_reduction_pct', label: 'Use less electricity', help: 'Efficiency and behaviour savings.' },
  { key: 'renewable_share_pct', label: 'Renewable electricity', help: 'Target share of electricity from renewables.' },
  { key: 'heating_reduction_pct', label: 'Reduce heating fuel', help: 'Thermostat, insulation, heat pumps.' },
  { key: 'meat_reduction_pct', label: 'Replace meat with vegetarian', help: 'Swap meat meals/days for vegetarian ones.' },
  { key: 'recycling_improvement_pct', label: 'Recycle more', help: 'Divert general waste to recycling.' },
]

const PRESETS: { label: string; levers: Partial<ScenarioLevers> }[] = [
  { label: 'Quick wins', levers: { renewable_share_pct: 100, electricity_reduction_pct: 10, recycling_improvement_pct: 50 } },
  { label: 'Travel smarter', levers: { car_reduction_pct: 25, flight_reduction_pct: 50 } },
  { label: 'Plant-forward', levers: { meat_reduction_pct: 60 } },
  { label: 'Ambitious', levers: { car_reduction_pct: 30, ev_adoption_pct: 100, flight_reduction_pct: 75, renewable_share_pct: 100, heating_reduction_pct: 20, meat_reduction_pct: 70, recycling_improvement_pct: 70 } },
]

export default function ScenarioPage() {
  const [levers, setLevers] = useState<ScenarioLevers>(ZERO)
  const debounced = useDebounce(levers, 200)
  const baseline = useQuery({ queryKey: ['scenario-baseline'], queryFn: mlApi.scenarioBaseline })
  const result = useQuery({
    queryKey: ['scenario', debounced],
    queryFn: () => mlApi.simulate(debounced),
    placeholderData: keepPreviousData,
    enabled: Boolean(baseline.data && baseline.data.basis !== 'none'),
  })

  const r = result.data
  const available = new Set(r?.available_levers ?? [])

  if (baseline.isLoading) return <div className="grid gap-4 lg:grid-cols-2"><CardSkeleton rows={8} /><CardSkeleton rows={8} /></div>
  if (baseline.error) return <div className="card"><ErrorState error={baseline.error} onRetry={() => baseline.refetch()} /></div>
  if (baseline.data?.basis === 'none') {
    return (
      <div>
        <PageHeader eyebrow="What if…" title="Scenario simulator" />
        <div className="card"><EmptyState icon={<FlaskConical className="h-6 w-6" />} title="Nothing to simulate yet"
          body="The simulator works from your tracked activities, or from your onboarding answers until you have two weeks of data."
          action={<ButtonLink to="/app/activities">Log activities</ButtonLink>} /></div>
      </div>
    )
  }

  return (
    <div>
      <PageHeader eyebrow="What if…" title="Scenario simulator"
        description="Move the sliders: the backend re-applies your monthly behaviour to the emission factors and returns the modelled footprint. Substitutions use the substitute’s own factor (e.g. beef → vegetarian meal)." />
      <div className="relative mb-6 h-28 overflow-hidden rounded-2xl sm:h-32">
        <img src={images.solar.src} alt={images.solar.alt} className="h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-r from-forest/90 via-forest/60 to-transparent" aria-hidden />
        <p className="absolute top-1/2 left-6 max-w-md -translate-y-1/2 text-sm font-medium text-white">
          Baseline: {baseline.data?.basis === 'tracked_activities' ? 'your tracked activities' : 'your onboarding estimate'} · {formatKg(baseline.data?.monthly_total_kg)} CO₂e per month
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <Panel title="Levers" actions={<Button size="sm" variant="ghost" onClick={() => setLevers(ZERO)} icon={<RotateCcw className="h-4 w-4" />}>Reset</Button>}>
          <div className="mb-5 flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button key={p.label} type="button" onClick={() => setLevers({ ...ZERO, ...p.levers })}
                className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-semibold text-ink transition hover:border-algae-light hover:bg-mint/60">{p.label}</button>
            ))}
          </div>
          <div className="space-y-5">
            {LEVERS.map((l) => {
              const disabled = r !== undefined && !available.has(l.key)
              const effect = r?.lever_effects.find((e) => e.lever === l.key)
              return (
                <div key={l.key} className={disabled ? 'opacity-45' : ''}>
                  <div className="flex items-baseline justify-between gap-2">
                    <label htmlFor={l.key} className="text-sm font-medium text-ink">{l.label}</label>
                    <span className="text-sm font-bold text-forest tabular-nums">{levers[l.key]}%</span>
                  </div>
                  <input id={l.key} type="range" className="slider mt-1.5 w-full" min={0} max={100} step={5} value={levers[l.key]} disabled={disabled}
                    aria-describedby={`${l.key}-help`} onChange={(e) => setLevers({ ...levers, [l.key]: Number(e.target.value) })} />
                  <p id={`${l.key}-help`} className="text-xs text-muted">
                    {disabled ? 'No matching activity in your data.' : l.help}
                    {effect && effect.monthly_reduction_kg > 0 && <span className="ml-1 font-semibold text-brand-deep">−{formatKg(effect.monthly_reduction_kg)}/mo on its own</span>}
                  </p>
                </div>
              )
            })}
          </div>
        </Panel>

        <div className="space-y-6">
          {result.error ? (
            <div className="card"><ErrorState error={result.error} onRetry={() => result.refetch()} /></div>
          ) : !r ? <CardSkeleton rows={6} /> : (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="card p-5">
                  <p className="text-sm text-muted">Current</p>
                  <p className="font-display text-2xl font-extrabold text-forest">{formatKg(r.current_monthly_kg)}<span className="text-sm font-semibold text-muted"> /mo</span></p>
                  <p className="text-xs text-muted">{formatKg(r.current_annual_kg)} per year</p>
                </div>
                <div className="card bg-gradient-to-br from-brand to-brand-deep p-5 text-white">
                  <p className="flex items-center gap-2 text-sm text-white/85">Projected {result.isFetching && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-label="Updating" />}</p>
                  <p className="font-display text-2xl font-extrabold">{formatKg(r.scenario_monthly_kg)}<span className="text-sm font-semibold text-white/80"> /mo</span></p>
                  <p className="text-xs text-white/80">{formatKg(r.scenario_annual_kg)} per year</p>
                </div>
              </div>
              <div className="card p-5" aria-live="polite">
                <div className="flex flex-wrap items-end justify-between gap-2">
                  <div>
                    <p className="text-sm text-muted">Estimated reduction</p>
                    <p className="font-display text-3xl font-extrabold text-brand">−{formatKg(r.reduction_monthly_kg)} <span className="text-base text-muted">/ month</span></p>
                  </div>
                  <motion.p key={Math.round(r.reduction_pct)} initial={{ scale: 0.9, opacity: 0.6 }} animate={{ scale: 1, opacity: 1 }}
                    className="font-display text-4xl font-extrabold text-forest"><AnimatedNumber value={r.reduction_pct} digits={1} suffix="%" /></motion.p>
                </div>
                <div className="mt-3"><ProgressBar value={r.reduction_pct} label="Percentage reduction" /></div>
                <p className="mt-2 text-xs text-muted">≈ {formatKg(r.reduction_monthly_kg * 12)} avoided per year · {formatPct(r.reduction_pct)} improvement</p>
              </div>
              <Panel title="By category" subtitle="Current vs scenario, kg CO₂e per month">
                <ScenarioCompareChart current={r.current_by_category} scenario={r.scenario_by_category} />
                <ul className="mt-2 flex gap-4 text-xs text-muted" aria-label="Legend">
                  <li className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-[#c3d6cb]" />Current</li>
                  <li className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-brand" />Scenario</li>
                </ul>
              </Panel>
              {r.assumptions.length > 0 && (
                <details className="card p-5 text-sm">
                  <summary className="cursor-pointer font-semibold text-forest">Assumptions</summary>
                  <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-muted">{r.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
                </details>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
