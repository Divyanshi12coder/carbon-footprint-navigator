import { CalendarRange } from 'lucide-react'
import { useState } from 'react'

import type { RangeParams } from '../../api/endpoints'
import type { RangeKey } from '../../types/api'
import { addDaysIso, todayIso } from '../../utils/format'
import { Segmented } from './misc'

const OPTIONS: { value: RangeKey; label: string }[] = [
  { value: '7d', label: '7D' },
  { value: '30d', label: '30D' },
  { value: '90d', label: '3M' },
  { value: '180d', label: '6M' },
  { value: '365d', label: '1Y' },
  { value: 'custom', label: 'Custom' },
]

/** Date-range control used above every analytics view; one row, applies to all charts below it. */
export function RangeFilter({ value, onChange }: { value: RangeParams; onChange: (v: RangeParams) => void }) {
  const [start, setStart] = useState(value.start ?? addDaysIso(-29))
  const [end, setEnd] = useState(value.end ?? todayIso())
  const invalid = start > end

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Segmented
        label="Date range"
        value={value.range}
        options={OPTIONS}
        onChange={(range) => onChange(range === 'custom' ? { range, start, end } : { range })}
      />
      {value.range === 'custom' && (
        <form
          className="flex flex-wrap items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault()
            if (!invalid) onChange({ range: 'custom', start, end })
          }}
        >
          <CalendarRange className="h-4 w-4 text-muted" aria-hidden />
          <label className="sr-only" htmlFor="range-start">Start date</label>
          <input id="range-start" type="date" className="input h-9 w-auto py-1" value={start} max={todayIso()}
            onChange={(e) => setStart(e.target.value)} />
          <span className="text-muted">–</span>
          <label className="sr-only" htmlFor="range-end">End date</label>
          <input id="range-end" type="date" className="input h-9 w-auto py-1" value={end} max={todayIso()}
            onChange={(e) => setEnd(e.target.value)} />
          <button type="submit" disabled={invalid}
            className="h-9 rounded-lg bg-forest px-3 text-xs font-semibold text-white disabled:opacity-50">
            Apply
          </button>
          {invalid && <span className="text-xs text-red-600" role="alert">Start must be before end</span>}
        </form>
      )}
    </div>
  )
}
