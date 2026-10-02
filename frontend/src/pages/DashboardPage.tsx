import { useQuery } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { CalendarDays, Leaf, ListPlus, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { stagger } from '../animations/variants'
import { analyticsApi, mlApi, profileApi, type RangeParams } from '../api/endpoints'
import { images } from '../assets/images'
import { CategoryDonut, CategoryStackedBars } from '../charts/CategoryCharts'
import { CategoryLegend } from '../charts/common'
import { EmissionsTrendChart } from '../charts/EmissionsTrendChart'
import { CategoryTile, ChangeBadge, KpiCard, Panel } from '../components/dashboard/cards'
import { ButtonLink } from '../components/ui/Button'
import { CardSkeleton, ChartSkeleton, EmptyState, ErrorState } from '../components/ui/feedback'
import { Badge, ProgressBar } from '../components/ui/misc'
import { RangeFilter } from '../components/ui/RangeFilter'
import { useAuth } from '../hooks/useAuth'
import { activityLabel, presentCategories } from '../utils/categories'
import { formatKg, formatPct } from '../utils/format'

const SEVERITY_TONE = { positive: 'green', info: 'blue', warning: 'amber' } as const

export default function DashboardPage() {
  const { user } = useAuth()
  const prefs = useQuery({ queryKey: ['preferences'], queryFn: profileApi.preferences })
  const [range, setRange] = useState<RangeParams | null>(null)
  const effective: RangeParams = range ?? { range: prefs.data?.default_range ?? '30d' }

  const summary = useQuery({ queryKey: ['summary', effective], queryFn: () => analyticsApi.summary(effective), enabled: !prefs.isLoading })
  const anomalies = useQuery({ queryKey: ['anomalies'], queryFn: mlApi.anomalies })
  const insights = useQuery({ queryKey: ['insights'], queryFn: mlApi.insights })

  const s = summary.data
  const anomalyDates = (anomalies.data ?? []).filter((a) => a.date).map((a) => a.date as string)
  const hasData = (s?.totals.activity_count ?? 0) > 0
  const categories = s ? presentCategories(s.categories.map((c) => c.category)) : []

  return (
    <div>
      <div className="relative mb-8 overflow-hidden rounded-3xl bg-forest p-6 text-white sm:p-8">
        <img src={images.forest.src} alt="" aria-hidden className="absolute inset-0 h-full w-full object-cover opacity-30" />
        <div className="absolute inset-0 bg-gradient-to-r from-forest via-forest/85 to-forest/40" aria-hidden />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="eyebrow !text-algae-light">Dashboard</p>
            <h1 className="mt-1 text-2xl font-bold sm:text-3xl">Hello, {user?.full_name.split(' ')[0]}</h1>
            <p className="mt-1 text-sm text-white/75">All figures are calculated from your logged activities and sourced emission factors.</p>
          </div>
          <div className="rounded-2xl bg-white/95 p-1.5"><RangeFilter value={effective} onChange={setRange} /></div>
        </div>
      </div>

      {summary.error ? (
        <div className="card"><ErrorState error={summary.error} onRetry={() => summary.refetch()} /></div>
      ) : summary.isLoading || !s ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} rows={2} />)}</div>
      ) : !hasData ? (
        <div className="card">
          <EmptyState icon={<Leaf className="h-6 w-6" />} title="No activities in this period"
            body="Log a journey, a meter reading or a meal and your dashboard will fill with real numbers. Try a longer date range if you’ve logged older activities."
            action={<ButtonLink to="/app/activities" icon={<ListPlus className="h-4 w-4" />}>Log an activity</ButtonLink>} />
        </div>
      ) : (
        <>
          <motion.div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" variants={stagger} initial="hidden" animate="show">
            <KpiCard highlight label={`Total · ${s.range.days} days`} kg={s.totals.total_kg}
              footer={<span className="text-xs text-white/85">{s.totals.change_pct === null ? 'No previous period data' : `${formatPct(s.totals.change_pct, true)} vs previous ${s.range.days} days`}</span>} />
            <KpiCard label="Daily average" kg={s.totals.daily_average_kg} hint="Total for the range divided by the number of days." footer={<span className="text-xs text-muted">Today so far: {formatKg(s.snapshot.today_kg)}</span>} />
            <KpiCard label="Weekly average" kg={s.totals.weekly_average_kg} footer={<span className="text-xs text-muted">Last 7 days: {formatKg(s.snapshot.last_7_days_kg)}</span>} />
            <KpiCard label="Monthly equivalent" kg={s.totals.monthly_equivalent_kg} hint="Daily average × 30.44 days."
              footer={<span className="text-xs text-muted">Month to date: {formatKg(s.snapshot.month_to_date_kg)}</span>} />
          </motion.div>

          <div className="mt-6 grid gap-6 xl:grid-cols-3">
            <Panel className="xl:col-span-2" title="Emission timeline"
              subtitle={s.granularity === 'day' ? 'Daily totals with 7-day rolling average · red markers = anomalies' : 'Weekly totals'}
              actions={<ChangeBadge pct={s.totals.change_pct} />}>
              <EmissionsTrendChart points={s.timeline} granularity={s.granularity} anomalyDates={anomalyDates} height={430} />
            </Panel>
            <Panel title="Footprint by category" subtitle={`${s.range.start} → ${s.range.end}`}>
              <CategoryDonut rows={s.categories} />
              <ul className="mt-4 space-y-2">
                {s.categories.filter((c) => c.kg > 0).map((c) => (
                  <li key={c.category} className="flex items-center justify-between text-sm">
                    <CategoryLegend categories={[c.category]} />
                    <span className="tabular-nums"><span className="font-semibold">{formatKg(c.kg)}</span> <span className="text-muted">· {formatPct(c.share_pct)}</span></span>
                  </li>
                ))}
              </ul>
            </Panel>
          </div>

          <motion.div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3" variants={stagger} initial="hidden" animate="show">
            {(['transport', 'energy', 'food', 'flights', 'waste', 'consumption'] as const).map((c) => (
              <CategoryTile key={c} category={c} row={s.categories.find((r) => r.category === c)} />
            ))}
          </motion.div>

          <div className="mt-6 grid gap-6 xl:grid-cols-3">
            <Panel className="xl:col-span-2" title="Category breakdown over time" subtitle="Stacked by category" actions={<CategoryLegend categories={categories} />}>
              <CategoryStackedBars data={s.timeline} xKey="period_start" granularity={s.granularity} height={470} />
            </Panel>
            <div className="space-y-6">
              <Panel title="Top activities" subtitle="Largest sources in this range">
                <ol className="space-y-3">
                  {s.top_activity_types.map((t) => (
                    <li key={t.activity_type}>
                      <div className="mb-1 flex justify-between text-sm"><span className="font-medium">{activityLabel(t.activity_type)} <span className="text-muted">×{t.count}</span></span><span className="tabular-nums font-semibold">{formatKg(t.kg)}</span></div>
                      <ProgressBar value={(100 * t.kg) / s.totals.total_kg} label={`${activityLabel(t.activity_type)} share`} />
                    </li>
                  ))}
                </ol>
              </Panel>
              <Panel title="1.5°C lifestyle benchmark" subtitle={<a href={s.benchmark.source_url} target="_blank" rel="noreferrer" className="underline">{s.benchmark.source}</a>}>
                <p className="text-sm text-muted">Your annualised pace for this range vs the {formatKg(s.benchmark.annual_kg)} per-person target.</p>
                <p className="mt-2 font-display text-2xl font-bold text-forest">{formatKg(s.totals.annualized_kg)} / yr</p>
                <div className="relative mt-2 h-2.5 rounded-full bg-mint" aria-hidden>
                  <div className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-algae to-amber-500" style={{ width: '100%' }} />
                  <div className="absolute -top-1 h-4.5 w-1 rounded bg-forest" style={{ left: `${Math.min(100, (100 * s.benchmark.annual_kg) / Math.max(1, s.totals.annualized_kg))}%` }} title="1.5°C target" />
                </div>
                <p className="mt-1 text-[11px] text-muted">Bar = your pace · marker = 1.5°C target</p>
                <p className="mt-2 text-xs text-muted">{(s.totals.annualized_kg / s.benchmark.annual_kg).toFixed(1)}× the target · tracked activities only</p>
              </Panel>
            </div>
          </div>

          <Panel className="mt-6" title="Latest insights" subtitle="Generated from your data after every change"
            actions={<ButtonLink to="/app/insights" variant="secondary" size="sm" icon={<Sparkles className="h-4 w-4" />}>All insights</ButtonLink>}>
            {insights.isLoading ? <ChartSkeleton height={120} /> : insights.error ? <ErrorState error={insights.error} onRetry={() => insights.refetch()} /> : (
              <div className="grid gap-3 md:grid-cols-3">
                {(insights.data ?? []).slice(0, 3).map((i) => (
                  <article key={i.id} className="rounded-xl border border-line bg-offwhite p-4">
                    <Badge tone={SEVERITY_TONE[i.severity]}>{i.severity}</Badge>
                    <h3 className="mt-2 text-sm font-semibold text-forest">{i.title}</h3>
                    <p className="mt-1 text-xs text-muted">{i.body}</p>
                  </article>
                ))}
              </div>
            )}
          </Panel>

          <p className="mt-6 flex items-center gap-2 text-xs text-muted">
            <CalendarDays className="h-4 w-4" aria-hidden /> {s.totals.activity_count} activities · data quality:{' '}
            {Object.entries(s.data_quality).map(([q, n]) => `${n} ${q}`).join(', ')} · <Link to="/methodology" className="underline">methodology</Link>
          </p>
        </>
      )}
    </div>
  )
}
