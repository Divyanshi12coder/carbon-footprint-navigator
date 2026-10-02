import { memo } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { CategoryRow } from '../types/api'
import { categoryColor, categoryLabel, presentCategories } from '../utils/categories'
import { formatDate, formatKg, formatPct } from '../utils/format'
import { AXIS, GRID, OffScaleNote, SURFACE, TooltipCard, offScaleCap, tickDate, tickKg } from './common'

/** Donut of category share. Slices keep fixed category colours; values are listed beside it. */
export const CategoryDonut = memo(function CategoryDonut({ rows, height = 220 }: { rows: CategoryRow[]; height?: number }) {
  const data = presentCategories(rows.filter((r) => r.kg > 0).map((r) => r.category)).map((c) => rows.find((r) => r.category === c)!)
  const total = data.reduce((s, r) => s + r.kg, 0)
  return (
    <div className="relative" style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie data={data} dataKey="kg" nameKey="category" innerRadius="64%" outerRadius="92%" paddingAngle={1.5}
            stroke={SURFACE} strokeWidth={2} isAnimationActive={false}>
            {data.map((r) => <Cell key={r.category} fill={categoryColor(r.category)} />)}
          </Pie>
          <Tooltip content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const r = payload[0].payload as CategoryRow
            return <TooltipCard title={categoryLabel(r.category)} rows={[
              { name: 'Emissions', value: r.kg, color: categoryColor(r.category) },
              { name: 'Share', value: formatPct(r.share_pct) },
            ]} />
          }} />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 grid place-items-center text-center">
        <div>
          <p className="text-xs text-muted">Total</p>
          <p className="font-display text-xl font-bold text-forest">{formatKg(total)}</p>
        </div>
      </div>
    </div>
  )
})

interface StackProps {
  data: Record<string, number | string | undefined>[]
  xKey: string
  granularity: 'day' | 'week' | 'month'
  height?: number
}

/** Stacked category bars over time, stacking in the fixed palette order with 2px surface gaps. */
export const CategoryStackedBars = memo(function CategoryStackedBars({ data, xKey, granularity, height = 280 }: StackProps) {
  const keys = new Set<string>()
  data.forEach((row) => Object.entries(row).forEach(([k, v]) => typeof v === 'number' && v > 0 && keys.add(k)))
  const cats = presentCategories(keys)
  const last = cats[cats.length - 1]
  const totals = data.map((row) => cats.reduce((s, c) => s + (Number(row[c]) || 0), 0))
  const cap = offScaleCap(totals)
  const clipped = cap === null ? [] : data.map((row, i) => ({ row, total: totals[i] })).filter((d) => d.total > cap)
  const fmtLabel = (v: unknown) => (granularity === 'month' ? formatDate(`${v}-01`, { month: 'short', year: 'numeric' }) : formatDate(String(v)))
  return (
    <>
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 10, right: 8, bottom: 0, left: -12 }} barCategoryGap="22%">
        <CartesianGrid {...GRID} />
        <XAxis dataKey={xKey} {...AXIS} tickFormatter={tickDate(granularity)} minTickGap={16} />
        <YAxis {...AXIS} tickFormatter={tickKg} width={52} domain={cap === null ? [0, 'auto'] : [0, cap]} allowDataOverflow={cap !== null} />
        <Tooltip
          cursor={{ fill: '#ddf4e5', opacity: 0.5 }}
          content={({ active, payload, label }) => {
            if (!active || !payload?.length) return null
            const row = payload[0].payload as Record<string, number>
            const title = granularity === 'month' ? formatDate(`${label}-01`, { month: 'long', year: 'numeric' }) : formatDate(String(label))
            const rows = [...cats].reverse().filter((c) => (row[c] ?? 0) > 0).map((c) => ({ name: categoryLabel(c), value: row[c], color: categoryColor(c) }))
            const total = cats.reduce((s, c) => s + (row[c] ?? 0), 0)
            return <TooltipCard title={title} rows={rows} footer={`Total ${formatKg(total)}`} />
          }}
        />
        {cats.map((c) => (
          <Bar key={c} dataKey={c} stackId="cat" fill={categoryColor(c)} stroke={SURFACE} strokeWidth={1}
            radius={c === last ? [4, 4, 0, 0] : 0} isAnimationActive={false} />
        ))}
      </BarChart>
    </ResponsiveContainer>
    <OffScaleNote points={clipped.map((d) => ({ label: fmtLabel(d.row[xKey]), value: d.total }))} />
    </>
  )
})

/** Horizontal bars, current vs scenario, per category (two series: legend + labels in the card). */
export const ScenarioCompareChart = memo(function ScenarioCompareChart({ current, scenario }: {
  current: Record<string, number>
  scenario: Record<string, number>
}) {
  const cats = presentCategories(Object.keys(current))
  const data = cats.map((c) => ({ category: categoryLabel(c), key: c, current: current[c] ?? 0, scenario: scenario[c] ?? 0 }))
  return (
    <ResponsiveContainer width="100%" height={Math.max(180, cats.length * 46)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 8 }} barGap={2} barCategoryGap="28%">
        <CartesianGrid {...GRID} horizontal={false} vertical />
        <XAxis type="number" {...AXIS} tickFormatter={tickKg} />
        <YAxis type="category" dataKey="category" {...AXIS} width={92} />
        <Tooltip cursor={{ fill: '#ddf4e5', opacity: 0.5 }} content={({ active, payload }) => {
          if (!active || !payload?.length) return null
          const r = payload[0].payload as (typeof data)[number]
          return <TooltipCard title={r.category} rows={[
            { name: 'Current', value: r.current, color: '#9fb7ab' },
            { name: 'Scenario', value: r.scenario, color: '#059669' },
            { name: 'Saving', value: r.current - r.scenario },
          ]} />
        }} />
        <Bar dataKey="current" fill="#c3d6cb" radius={[0, 4, 4, 0]} isAnimationActive={false} />
        <Bar dataKey="scenario" fill="#059669" radius={[0, 4, 4, 0]} animationDuration={400} />
      </BarChart>
    </ResponsiveContainer>
  )
})
