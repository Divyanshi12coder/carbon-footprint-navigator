import { memo } from 'react'
import { Area, CartesianGrid, ComposedChart, Line, ReferenceDot, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { TimelinePoint } from '../types/api'
import { formatDate } from '../utils/format'
import { AXIS, GRID, OffScaleNote, TooltipCard, offScaleCap, tickDate, tickKg } from './common'

interface Props {
  points: TimelinePoint[]
  granularity: 'day' | 'week' | 'month'
  height?: number
  /** ISO dates to mark as anomalies (from the anomaly detector). */
  anomalyDates?: string[]
  showRolling?: boolean
}

/** Total emissions over time with an optional 7-day rolling mean and anomaly markers. */
export const EmissionsTrendChart = memo(function EmissionsTrendChart({
  points,
  granularity,
  height = 280,
  anomalyDates = [],
  showRolling = true,
}: Props) {
  const marks = new Set(anomalyDates)
  const rolling = showRolling && granularity === 'day'
  const cap = offScaleCap(points.map((p) => p.total_kg))
  const clipped = cap === null ? [] : points.filter((p) => p.total_kg > cap)
  return (
    <>
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={points} margin={{ top: 10, right: 8, bottom: 0, left: -12 }}>
        <defs>
          <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#059669" stopOpacity={0.28} />
            <stop offset="100%" stopColor="#059669" stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="period_start" {...AXIS} tickFormatter={tickDate(granularity)} minTickGap={24} />
        <YAxis {...AXIS} tickFormatter={tickKg} width={52} domain={cap === null ? [0, 'auto'] : [0, cap]} allowDataOverflow={cap !== null} />
        <Tooltip
          cursor={{ stroke: '#3fae72', strokeWidth: 1 }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const p = payload[0].payload as TimelinePoint
            const rows = [{ name: granularity === 'day' ? 'Daily total' : 'Total', value: p.total_kg, color: '#059669' }]
            if (rolling && typeof p.rolling_7d_kg === 'number') rows.push({ name: '7-day average', value: p.rolling_7d_kg, color: '#12372a' })
            const title = p.period_end ? `${formatDate(p.period_start)} – ${formatDate(p.period_end)}` : formatDate(p.period_start, { weekday: 'short', day: 'numeric', month: 'short' })
            return <TooltipCard title={title} rows={rows} footer={marks.has(p.period_start) ? 'Flagged as unusual by anomaly detection' : undefined} />
          }}
        />
        <Area type="monotone" dataKey="total_kg" stroke="#059669" strokeWidth={2} fill="url(#trendFill)" activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }} isAnimationActive={false} />
        {rolling && <Line type="monotone" dataKey="rolling_7d_kg" stroke="#12372a" strokeWidth={2} dot={false} strokeDasharray="5 4" isAnimationActive={false} />}
        {points
          .filter((p) => marks.has(p.period_start))
          .map((p) => (
            <ReferenceDot key={p.period_start} x={p.period_start} y={cap === null ? p.total_kg : Math.min(p.total_kg, cap)} r={6} fill="#e34948" stroke="#fff" strokeWidth={2} />
          ))}
      </ComposedChart>
    </ResponsiveContainer>
    <OffScaleNote points={clipped.map((p) => ({ label: formatDate(p.period_start), value: p.total_kg }))} />
    </>
  )
})
