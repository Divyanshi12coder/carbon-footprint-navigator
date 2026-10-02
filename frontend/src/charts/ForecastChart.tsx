import { memo, useMemo } from 'react'
import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import type { Forecast } from '../types/api'
import { formatDate } from '../utils/format'
import { AXIS, GRID, OffScaleNote, TooltipCard, offScaleCap, tickKg } from './common'

interface Row {
  date: string
  actual?: number
  rolling?: number
  predicted?: number
  band?: [number, number]
}

/** History (actual + 7-day mean) → forecast with its 80% interval band. */
export const ForecastChart = memo(function ForecastChart({ forecast, historyDays = 60, height = 300 }: {
  forecast: Forecast
  historyDays?: number
  height?: number
}) {
  const data = useMemo<Row[]>(() => {
    const hist: Row[] = forecast.history.slice(-historyDays).map((h) => ({ date: h.date, actual: h.actual_kg, rolling: h.rolling_7d_kg }))
    const last = hist[hist.length - 1]
    // Bridge the last observed rolling value into the forecast so the lines connect.
    if (last && forecast.points.length) last.predicted = last.rolling
    const fut = forecast.points.map((p) => ({ date: p.date, predicted: p.predicted_kg, band: [p.lower_kg, p.upper_kg] as [number, number] }))
    return [...hist, ...fut]
  }, [forecast, historyDays])
  const today = forecast.history[forecast.history.length - 1]?.date
  const cap = offScaleCap(data.flatMap((r) => [r.actual ?? 0, r.rolling ?? 0, r.band?.[1] ?? 0]))
  const clipped = cap === null ? [] : data.filter((r) => (r.actual ?? 0) > cap)

  return (
    <>
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 10, right: 8, bottom: 0, left: -12 }}>
        <CartesianGrid {...GRID} />
        <XAxis dataKey="date" {...AXIS} tickFormatter={(v: string) => formatDate(v)} minTickGap={28} />
        <YAxis {...AXIS} tickFormatter={tickKg} width={52} domain={cap === null ? [0, 'auto'] : [0, cap]} allowDataOverflow={cap !== null} />
        <Tooltip
          cursor={{ stroke: '#3fae72', strokeWidth: 1 }}
          content={({ active, payload }) => {
            if (!active || !payload?.length) return null
            const r = payload[0].payload as Row
            const rows = []
            if (r.actual !== undefined) rows.push({ name: 'Actual', value: r.actual, color: '#9fb7ab' })
            if (r.rolling !== undefined) rows.push({ name: '7-day average', value: r.rolling, color: '#12372a' })
            if (r.band) {
              rows.push({ name: 'Forecast', value: r.predicted ?? 0, color: '#059669' })
              rows.push({ name: '80% range', value: `${r.band[0].toFixed(1)}–${r.band[1].toFixed(1)} kg` })
            }
            return <TooltipCard title={formatDate(r.date, { weekday: 'short', day: 'numeric', month: 'short' })} rows={rows} />
          }}
        />
        <Area dataKey="band" stroke="none" fill="#8bcf9b" fillOpacity={0.35} isAnimationActive={false} />
        <Area dataKey="actual" type="monotone" stroke="#c3d6cb" strokeWidth={1} fill="#e9f2ec" fillOpacity={0.6} isAnimationActive={false} />
        <Line dataKey="rolling" type="monotone" stroke="#12372a" strokeWidth={2} dot={false} isAnimationActive={false} />
        <Line dataKey="predicted" type="monotone" stroke="#059669" strokeWidth={2} strokeDasharray="6 4" dot={false} isAnimationActive={false} />
        {today && <ReferenceLine x={today} stroke="#5d786d" strokeDasharray="3 3" label={{ value: 'Today', fill: '#5d786d', fontSize: 11, position: 'insideTopLeft' }} />}
      </ComposedChart>
    </ResponsiveContainer>
    <OffScaleNote points={clipped.map((r) => ({ label: formatDate(r.date), value: r.actual ?? 0 }))} />
    </>
  )
})
