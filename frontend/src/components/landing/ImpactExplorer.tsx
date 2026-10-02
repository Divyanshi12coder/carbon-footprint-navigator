import { useMemo, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { AXIS, GRID, TooltipCard } from '../../charts/common'
import { useFactors } from '../../hooks/useFactors'
import { formatKg } from '../../utils/format'
import { ErrorState, Skeleton } from '../ui/feedback'
import { Segmented } from '../ui/misc'

type Mode = 'travel' | 'meal' | 'grid'

const SETS: Record<Mode, { title: string; unitQty: number; unitLabel: string; items: { label: string; key: string; region?: string }[] }> = {
  travel: {
    title: 'CO₂e for 100 km per person',
    unitQty: 100,
    unitLabel: 'per 100 km',
    items: [
      { label: 'Petrol car', key: 'transport.car.petrol' },
      { label: 'Diesel car', key: 'transport.car.diesel' },
      { label: 'Hybrid car', key: 'transport.car.hybrid' },
      { label: 'Electric car', key: 'transport.car.electric' },
      { label: 'Bus', key: 'transport.bus' },
      { label: 'Train', key: 'transport.rail' },
      { label: 'Short-haul flight', key: 'flights.short_haul.economy' },
      { label: 'Bicycle', key: 'transport.bicycle' },
    ],
  },
  meal: {
    title: 'CO₂e for one meal',
    unitQty: 1,
    unitLabel: 'per serving',
    items: [
      { label: 'Beef', key: 'food.meal.beef' },
      { label: 'Lamb', key: 'food.meal.lamb' },
      { label: 'Cheese-heavy', key: 'food.meal.dairy_heavy' },
      { label: 'Fish', key: 'food.meal.fish' },
      { label: 'Pork', key: 'food.meal.pork' },
      { label: 'Chicken', key: 'food.meal.chicken' },
      { label: 'Vegetarian', key: 'food.meal.vegetarian' },
      { label: 'Vegan', key: 'food.meal.vegan' },
    ],
  },
  grid: {
    title: 'CO₂e for 1,000 kWh of grid electricity',
    unitQty: 1000,
    unitLabel: 'per 1,000 kWh',
    items: [
      { label: 'India', key: 'energy.electricity.grid', region: 'IN' },
      { label: 'Australia', key: 'energy.electricity.grid', region: 'AU' },
      { label: 'Germany', key: 'energy.electricity.grid', region: 'DE' },
      { label: 'United States', key: 'energy.electricity.grid', region: 'US' },
      { label: 'United Kingdom', key: 'energy.electricity.grid', region: 'GB' },
      { label: 'France', key: 'energy.electricity.grid', region: 'FR' },
      { label: 'Norway', key: 'energy.electricity.grid', region: 'NO' },
    ],
  },
}

/** Interactive comparison built directly from the public emission-factor dataset. */
export function ImpactExplorer() {
  const [mode, setMode] = useState<Mode>('travel')
  const { factor, isLoading, error, refetch } = useFactors()
  const set = SETS[mode]
  const data = useMemo(
    () =>
      set.items
        .map((it) => {
          const f = factor(it.key, it.region)
          return f ? { label: it.label, kg: f.co2e_per_unit * set.unitQty, source: f.source, factor: f.co2e_per_unit, unit: f.unit } : null
        })
        .filter((d): d is NonNullable<typeof d> => d !== null)
        .sort((a, b) => b.kg - a.kg),
    [factor, set],
  )
  const max = data[0]?.kg ?? 0

  return (
    <div className="card p-5 sm:p-7">
      <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-bold text-forest">{set.title}</h3>
          <p className="text-sm text-muted">Computed live from the platform’s emission-factor table.</p>
        </div>
        <Segmented label="Comparison" value={mode} onChange={setMode}
          options={[{ value: 'travel', label: 'Travel' }, { value: 'meal', label: 'Food' }, { value: 'grid', label: 'Electricity' }]} />
      </div>
      {error ? (
        <ErrorState error={error} onRetry={() => refetch()} />
      ) : isLoading ? (
        <div className="space-y-3">{Array.from({ length: 7 }).map((_, i) => <Skeleton key={i} className="h-7" />)}</div>
      ) : (
        <ResponsiveContainer width="100%" height={data.length * 42 + 20}>
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 72, bottom: 0, left: 8 }}>
            <CartesianGrid {...GRID} horizontal={false} vertical />
            <XAxis type="number" hide domain={[0, max * 1.05]} />
            <YAxis type="category" dataKey="label" {...AXIS} width={118} />
            <Tooltip cursor={{ fill: '#ddf4e5', opacity: 0.5 }} content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const d = payload[0].payload as (typeof data)[number]
              return <TooltipCard title={d.label} rows={[{ name: set.unitLabel, value: d.kg, color: '#059669' },
                { name: 'Factor', value: `${d.factor} kg/${d.unit}` }]} footer={d.source} />
            }} />
            <Bar dataKey="kg" radius={[0, 4, 4, 0]} barSize={22} animationDuration={500}>
              {data.map((d) => <Cell key={d.label} fill={d.kg === max ? '#12372a' : '#3fae72'} />)}
              <LabelList dataKey="kg" position="right" formatter={(v) => formatKg(Number(v))} className="fill-ink text-xs font-semibold" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
