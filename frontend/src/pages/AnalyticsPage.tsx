import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, BrainCircuit, Target } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { analyticsApi, goalApi, mlApi, type RangeParams } from '../api/endpoints'
import { CategoryStackedBars } from '../charts/CategoryCharts'
import { CategoryLegend } from '../charts/common'
import { EmissionsTrendChart } from '../charts/EmissionsTrendChart'
import { ForecastChart } from '../charts/ForecastChart'
import { Panel } from '../components/dashboard/cards'
import { ChartSkeleton, EmptyState, ErrorState } from '../components/ui/feedback'
import { Badge, InfoTip, PageHeader, ProgressBar, Segmented } from '../components/ui/misc'
import { RangeFilter } from '../components/ui/RangeFilter'
import { CATEGORY_META, CATEGORY_ORDER, activityLabel, categoryLabel, presentCategories } from '../utils/categories'
import { formatDate, formatKg, formatNumber, formatPct, titleCase } from '../utils/format'

const MODEL_LABELS: Record<string, string> = {
  moving_average_28: '28-day moving average',
  seasonal_weekday_28: 'Weekday-seasonal mean (28 days)',
  ridge_trend_weekday: 'Ridge regression (trend + weekday)',
}

function ForecastPanel() {
  const [horizon, setHorizon] = useState<'7' | '30' | '90'>('30')
  const fc = useQuery({ queryKey: ['forecast', horizon], queryFn: () => mlApi.forecast(Number(horizon)) })
  const f = fc.data
  return (
    <Panel title="Forecast" subtitle="Historical emissions → forecast → 80% interval"
      actions={<Segmented label="Forecast horizon" value={horizon} onChange={setHorizon}
        options={[{ value: '7', label: '7 days' }, { value: '30', label: '30 days' }, { value: '90', label: '90 days' }]} />}>
      {fc.error ? <ErrorState error={fc.error} onRetry={() => fc.refetch()} /> : fc.isLoading || !f ? <ChartSkeleton /> : f.status !== 'ok' ? (
        <EmptyState icon={<BrainCircuit className="h-6 w-6" />} title="Not enough history to forecast yet" body={f.notes.join(' ')} />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
          <div>
            <ForecastChart forecast={f} historyDays={horizon === '90' ? 120 : 60} />
            <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted" aria-label="Legend">
              <li className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-[#c3d6cb]" />Actual daily</li>
              <li className="flex items-center gap-1.5"><span className="h-0.5 w-4 bg-forest" />7-day average</li>
              <li className="flex items-center gap-1.5"><span className="h-0.5 w-4 border-t-2 border-dashed border-brand" />Forecast</li>
              <li className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-algae-light/60" />80% interval</li>
            </ul>
          </div>
          <div className="space-y-3 text-sm">
            <div className="rounded-xl bg-mint/60 p-4">
              <p className="text-xs font-medium text-muted">Next {f.horizon_days} days</p>
              <p className="font-display text-2xl font-extrabold text-forest">{formatKg(f.predicted_total_kg)}</p>
              <p className="text-xs text-muted">80% range {formatKg(f.lower_total_kg)} – {formatKg(f.upper_total_kg)}</p>
              {f.recent_total_kg !== null && <p className="mt-1 text-xs text-muted">Previous {f.horizon_days} days: {formatKg(f.recent_total_kg)}</p>}
            </div>
            <dl className="space-y-1.5 text-xs">
              <div className="flex justify-between gap-2"><dt className="text-muted">Selected model</dt><dd className="text-right font-semibold">{MODEL_LABELS[f.model_name ?? ''] ?? f.model_name}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Back-test MAE</dt><dd className="font-semibold">{formatNumber(f.metrics.mae_kg_per_day, 2)} kg/day</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Skill vs moving average</dt><dd className="font-semibold">{f.metrics.skill_vs_moving_average == null ? '—' : formatPct(f.metrics.skill_vs_moving_average * 100)}</dd></div>
              <div className="flex justify-between"><dt className="text-muted">Training / hold-out</dt><dd className="font-semibold">{f.metrics.training_days} / {f.metrics.holdout_days} days</dd></div>
            </dl>
            {f.metrics.candidates && (
              <details className="text-xs"><summary className="cursor-pointer font-medium text-brand">All candidate scores</summary>
                <table className="mt-2 w-full text-left">
                  <thead><tr className="text-muted"><th className="font-medium">Model</th><th className="font-medium">MAE</th><th className="font-medium">RMSE</th></tr></thead>
                  <tbody>{Object.entries(f.metrics.candidates).map(([k, v]) => (
                    <tr key={k} className={k === f.model_name ? 'font-semibold text-forest' : ''}><td>{MODEL_LABELS[k] ?? k}</td><td>{v.mae.toFixed(2)}</td><td>{v.rmse.toFixed(2)}</td></tr>
                  ))}</tbody>
                </table>
              </details>
            )}
            {f.notes.map((n) => <p key={n} className="text-xs text-muted">• {n}</p>)}
          </div>
        </div>
      )}
    </Panel>
  )
}

export default function AnalyticsPage() {
  const [range, setRange] = useState<RangeParams>({ range: '90d' })
  const [granularity, setGranularity] = useState<'day' | 'week'>('day')
  const [category, setCategory] = useState('')

  const ts = useQuery({ queryKey: ['timeseries', range, granularity, category], queryFn: () => analyticsApi.timeseries({ ...range, granularity, category: category || undefined }) })
  const monthly = useQuery({ queryKey: ['monthly'], queryFn: () => analyticsApi.monthly(12) })
  const breakdown = useQuery({ queryKey: ['breakdown', range], queryFn: () => analyticsApi.breakdown(range) })
  const anomalies = useQuery({ queryKey: ['anomalies'], queryFn: mlApi.anomalies })
  const goals = useQuery({ queryKey: ['goals'], queryFn: goalApi.list })

  const anomalyDates = (anomalies.data ?? []).filter((a) => a.date && (!category || a.category === category)).map((a) => a.date as string)
  const monthlyCats = presentCategories((monthly.data ?? []).flatMap((r) => Object.keys(r)))

  return (
    <div>
      <PageHeader eyebrow="Analytics" title="Emission analytics" description="Trends, contributions, forecasts and anomalies — all computed from your stored records."
        actions={<RangeFilter value={range} onChange={setRange} />} />

      <Panel title="Emission trend" subtitle={category ? `${categoryLabel(category)} only` : 'All categories'}
        actions={
          <div className="flex flex-wrap gap-2">
            <label className="sr-only" htmlFor="trend-cat">Category</label>
            <select id="trend-cat" className="input h-9 w-auto py-1 text-xs" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All categories</option>
              {CATEGORY_ORDER.map((c) => <option key={c} value={c}>{CATEGORY_META[c].label}</option>)}
            </select>
            <Segmented label="Granularity" value={granularity} onChange={setGranularity} options={[{ value: 'day', label: 'Daily' }, { value: 'week', label: 'Weekly' }]} />
          </div>
        }>
        {ts.error ? <ErrorState error={ts.error} onRetry={() => ts.refetch()} /> : ts.isLoading || !ts.data ? <ChartSkeleton /> : (
          <>
            <EmissionsTrendChart points={ts.data.points} granularity={ts.data.granularity} anomalyDates={anomalyDates} height={300} />
            <ul className="mt-3 flex flex-wrap gap-x-4 text-xs text-muted" aria-label="Legend">
              <li className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-sm bg-brand" />{granularity === 'day' ? 'Daily total' : 'Weekly total'}</li>
              {granularity === 'day' && <li className="flex items-center gap-1.5"><span className="h-0.5 w-4 border-t-2 border-dashed border-forest" />7-day rolling average</li>}
              <li className="flex items-center gap-1.5"><span className="h-2.5 w-2.5 rounded-full bg-[#e34948]" />Anomaly</li>
            </ul>
          </>
        )}
      </Panel>

      <div className="mt-6 grid gap-6 xl:grid-cols-2">
        <Panel title="Monthly comparison" subtitle="Last 12 calendar months" actions={<CategoryLegend categories={monthlyCats} />}>
          {monthly.error ? <ErrorState error={monthly.error} onRetry={() => monthly.refetch()} /> : monthly.isLoading || !monthly.data ? <ChartSkeleton /> : (
            <>
              <CategoryStackedBars data={monthly.data} xKey="month" granularity="month" />
              <details className="mt-3 text-xs">
                <summary className="cursor-pointer font-medium text-brand">Show as table</summary>
                <div className="mt-2 overflow-x-auto">
                  <table className="w-full text-left tabular-nums">
                    <thead><tr className="text-muted"><th className="py-1 font-medium">Month</th>{monthlyCats.map((c) => <th key={c} className="font-medium">{categoryLabel(c)}</th>)}<th className="font-medium">Total</th></tr></thead>
                    <tbody>{monthly.data.map((r) => (
                      <tr key={r.month} className="border-t border-line"><td className="py-1">{r.month}</td>{monthlyCats.map((c) => <td key={c}>{formatNumber(Number(r[c] ?? 0), 0)}</td>)}<td className="font-semibold">{formatNumber(r.total_kg, 0)}</td></tr>
                    ))}</tbody>
                  </table>
                </div>
              </details>
            </>
          )}
        </Panel>

        <Panel title="Anomalies" subtitle="Robust weekly z-scores + Isolation Forest on daily features">
          {anomalies.error ? <ErrorState error={anomalies.error} onRetry={() => anomalies.refetch()} /> : anomalies.isLoading ? <ChartSkeleton height={160} /> : (anomalies.data ?? []).length === 0 ? (
            <EmptyState icon={<AlertTriangle className="h-6 w-6" />} title="No unusual spikes detected" body="Detection needs about 5 weeks of history for weekly patterns and 30 days for the daily model." />
          ) : (
            <ul className="space-y-3">
              {anomalies.data!.map((a, i) => (
                <li key={i} className="rounded-xl border border-amber-200 bg-amber-50/60 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge tone="amber"><AlertTriangle className="h-3 w-3" />{a.method === 'weekly_robust_z' ? 'Weekly pattern' : 'Daily outlier'}</Badge>
                    {a.category && <Badge tone="gray">{categoryLabel(a.category)}</Badge>}
                    <span className="text-xs text-muted">{a.date ? formatDate(a.date) : `${formatDate(a.period_start!)} – ${formatDate(a.period_end!)}`}</span>
                  </div>
                  <p className="mt-2 text-sm text-ink">{a.message}</p>
                  <p className="mt-1 text-xs text-muted">Observed {formatKg(a.observed_kg)} · expected {formatKg(a.expected_kg)} · {a.method === 'weekly_robust_z' ? `robust z = ${a.score}` : `isolation score ${a.score}`}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="mt-6"><ForecastPanel /></div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.5fr_1fr]">
        <Panel title="Per-activity analysis" subtitle="Grouped by activity type and emission factor">
          {breakdown.error ? <ErrorState error={breakdown.error} onRetry={() => breakdown.refetch()} /> : breakdown.isLoading ? <ChartSkeleton height={200} /> : (breakdown.data ?? []).length === 0 ? (
            <EmptyState title="No activities in this range" />
          ) : (
            <div className="-mx-2 overflow-x-auto">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead><tr className="text-xs text-muted"><th className="px-2 py-2 font-medium">Activity</th><th className="px-2 font-medium">Factor</th><th className="px-2 text-right font-medium">Count</th>
                  <th className="px-2 text-right font-medium">Quantity</th><th className="px-2 text-right font-medium">CO₂e</th><th className="px-2 text-right font-medium">Share</th></tr></thead>
                <tbody>
                  {breakdown.data!.map((b) => (
                    <tr key={`${b.activity_type}-${b.factor_key}`} className="border-t border-line">
                      <td className="px-2 py-2"><span className="mr-2 inline-block h-2.5 w-2.5 rounded-sm" style={{ background: CATEGORY_META[b.category].color }} aria-hidden />{activityLabel(b.activity_type)}</td>
                      <td className="px-2 text-xs text-muted">{b.factor_key}</td>
                      <td className="px-2 text-right tabular-nums">{b.count}</td>
                      <td className="px-2 text-right whitespace-nowrap tabular-nums">{formatNumber(b.quantity, 0)} {b.unit.replace('_', ' ')}</td>
                      <td className="px-2 text-right font-semibold whitespace-nowrap tabular-nums">{formatKg(b.kg)}</td>
                      <td className="px-2 text-right tabular-nums">{formatPct(b.share_pct)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
        <Panel title="Goal progress" actions={<Link to="/app/goals" className="text-xs font-semibold text-brand hover:underline">Manage goals</Link>}>
          {goals.isLoading ? <ChartSkeleton height={120} /> : (goals.data ?? []).length === 0 ? (
            <EmptyState icon={<Target className="h-6 w-6" />} title="No goals yet" body={<Link className="text-brand underline" to="/app/goals">Create a reduction goal</Link>} />
          ) : (
            <ul className="space-y-4">
              {goals.data!.map((g) => (
                <li key={g.id}>
                  <div className="mb-1 flex justify-between text-sm"><span className="font-medium">{g.title}</span><Badge tone={g.status === 'achieved' ? 'green' : g.status === 'missed' ? 'red' : 'mint'}>{titleCase(g.status)}</Badge></div>
                  <ProgressBar value={g.progress.progress_pct} label={`${g.title} progress`} />
                  <p className="mt-1 text-xs text-muted">{formatPct(g.progress.progress_pct)} · now {formatKg(g.progress.current_monthly_kg)}/mo → target {formatKg(g.progress.target_monthly_kg)}/mo <InfoTip text={g.progress.measurement} /></p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </div>
  )
}
