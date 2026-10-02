import type { ReactNode } from 'react'

import { categoryColor, categoryLabel } from '../utils/categories'
import { formatDate, formatKg } from '../utils/format'

export const AXIS = { stroke: '#cfe0d6', tick: { fill: '#5d786d', fontSize: 12 }, tickLine: false } as const
export const GRID = { stroke: '#e9f2ec', strokeDasharray: '0', vertical: false } as const
export const SURFACE = '#ffffff'

export interface TooltipRow {
  name: string
  value: number | string
  color?: string
}

/** Shared tooltip body: ink-coloured text, colour only on the swatch. */
export function TooltipCard({ title, rows, footer }: { title: string; rows: TooltipRow[]; footer?: ReactNode }) {
  return (
    <div className="min-w-44 rounded-xl border border-line bg-white/95 px-3 py-2.5 text-xs shadow-lg backdrop-blur">
      <p className="mb-1.5 font-semibold text-forest">{title}</p>
      <ul className="space-y-1">
        {rows.map((r) => (
          <li key={r.name} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-muted">
              {r.color && <span className="h-2.5 w-2.5 rounded-sm" style={{ background: r.color }} aria-hidden />}
              {r.name}
            </span>
            <span className="font-semibold text-ink tabular-nums">{typeof r.value === 'number' ? formatKg(r.value) : r.value}</span>
          </li>
        ))}
      </ul>
      {footer && <div className="mt-1.5 border-t border-line pt-1.5 text-muted">{footer}</div>}
    </div>
  )
}

export function CategoryLegend({ categories, values }: { categories: string[]; values?: Record<string, number> }) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs" aria-label="Legend">
      {categories.map((c) => (
        <li key={c} className="flex items-center gap-1.5 text-muted">
          <span className="h-2.5 w-2.5 rounded-sm" style={{ background: categoryColor(c) }} aria-hidden />
          <span className="text-ink">{categoryLabel(c)}</span>
          {values && <span className="tabular-nums">{formatKg(values[c] ?? 0)}</span>}
        </li>
      ))}
    </ul>
  )
}

export const tickDate = (granularity: 'day' | 'week' | 'month') => (v: string) =>
  granularity === 'month' ? formatDate(`${v}-01`, { month: 'short' }) : formatDate(v)

export const tickKg = (v: number) => (Math.abs(v) >= 1000 ? `${(v / 1000).toFixed(1)}t` : `${Math.round(v)}`)

/**
 * Robust y-axis cap so a single extreme day (e.g. a long-haul flight) doesn't flatten the chart.
 * Returns null when no clipping is needed. Clipped points are listed under the chart and the
 * tooltip always shows the true value.
 */
export function offScaleCap(values: number[]): number | null {
  const positive = values.filter((v) => v > 0).sort((a, b) => a - b)
  if (positive.length < 8) return null
  const p90 = positive[Math.floor(0.9 * (positive.length - 1))]
  const max = positive[positive.length - 1]
  const cap = Math.max(p90 * 3, 1)
  return max > cap * 1.15 ? Math.ceil(cap) : null
}

export function OffScaleNote({ points }: { points: { label: string; value: number }[] }) {
  if (!points.length) return null
  return (
    <p className="mt-2 text-xs text-muted">
      <span className="font-semibold text-ink">Off-scale:</span>{' '}
      {points.map((p) => `${p.label} (${formatKg(p.value)})`).join(', ')} — axis capped so everyday variation stays readable.
    </p>
  )
}
