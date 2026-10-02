import { useQuery } from '@tanstack/react-query'
import { clsx } from 'clsx'
import { Calculator, Loader2, Save } from 'lucide-react'
import { useMemo, useState, type FormEvent } from 'react'

import { ApiError } from '../../api/client'
import { activityApi, profileApi } from '../../api/endpoints'
import { useAuth } from '../../hooks/useAuth'
import { useDebounce } from '../../hooks/useDebounce'
import type { Activity, ActivityDetails, ActivityInput, ActivityTypeSpec, Category } from '../../types/api'
import { CATEGORY_META } from '../../utils/categories'
import { formatKg, todayIso } from '../../utils/format'
import { Button } from '../ui/Button'
import { ErrorState, Skeleton } from '../ui/feedback'
import { QualityBadge } from '../ui/misc'

const GROUPS: { category: Category; label: string }[] = [
  { category: 'transport', label: 'Transport' },
  { category: 'flights', label: 'Flights' },
  { category: 'energy', label: 'Energy' },
  { category: 'food', label: 'Food' },
  { category: 'waste', label: 'Waste' },
  { category: 'consumption', label: 'Consumption' },
  { category: 'digital', label: 'Digital' },
  { category: 'business', label: 'Business' },
  { category: 'other', label: 'Other' },
]

function defaultsFor(spec: ActivityTypeSpec): ActivityDetails {
  const d: ActivityDetails = {}
  spec.fields.forEach((f) => {
    if (f.default !== null && f.default !== undefined) d[f.name] = f.default
  })
  return d
}

interface Props {
  initial?: Activity
  onSaved: (activity: Activity) => void
  submitLabel?: string
}

export function ActivityForm({ initial, onSaved, submitLabel = 'Save activity' }: Props) {
  const { user } = useAuth()
  const types = useQuery({ queryKey: ['activity-types'], queryFn: activityApi.types, staleTime: Infinity })
  const airports = useQuery({ queryKey: ['airports'], queryFn: activityApi.airports, staleTime: Infinity })
  const prefs = useQuery({ queryKey: ['preferences'], queryFn: profileApi.preferences })
  const distanceUnit = prefs.data?.distance_unit ?? 'km'

  const [group, setGroup] = useState<Category>(initial?.category ?? 'transport')
  const [typeKey, setTypeKey] = useState(initial?.activity_type ?? 'car')
  const [quantity, setQuantity] = useState<string>(initial ? String(initial.quantity) : '')
  const [unit, setUnit] = useState<string>(initial?.unit ?? '')
  const [details, setDetails] = useState<ActivityDetails>(initial?.details ?? {})
  const [date, setDate] = useState(initial?.occurred_on ?? todayIso())
  const [description, setDescription] = useState(initial?.description ?? '')
  const [forOrg, setForOrg] = useState(Boolean(initial?.organization_id))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const spec = types.data?.find((t) => t.key === typeKey)
  const groupTypes = useMemo(() => (types.data ?? []).filter((t) => t.category === group), [types.data, group])

  const effectiveUnit = unit || (spec ? (spec.units.includes(distanceUnit) ? distanceUnit : spec.units[0] ?? '') : '')
  const effectiveDetails: ActivityDetails = spec ? { ...defaultsFor(spec), ...details } : details

  /** Switching activity type resets its type-specific inputs to the catalogue defaults. */
  const selectType = (key: string) => {
    setTypeKey(key)
    setDetails({})
    setUnit('')
  }

  const isFlightRoute = spec?.mode === 'flight' && Boolean(effectiveDetails.origin || effectiveDetails.destination)
  const qty = quantity === '' ? null : Number(quantity)
  const quantityInvalid = !isFlightRoute && spec?.mode !== 'flight' && (qty === null || Number.isNaN(qty) || qty < 0)
  const dateInvalid = !date || date > todayIso()

  const previewInput = useDebounce({ activity_type: typeKey, quantity: isFlightRoute ? null : qty, unit: isFlightRoute ? null : effectiveUnit || null, details: effectiveDetails }, 350)
  const preview = useQuery({
    queryKey: ['preview', previewInput],
    queryFn: () => activityApi.preview(previewInput),
    enabled: Boolean(spec) && (spec?.mode === 'flight' || (previewInput.quantity !== null && !Number.isNaN(previewInput.quantity))),
    retry: false,
  })

  if (types.error) return <ErrorState error={types.error} onRetry={() => types.refetch()} />
  if (types.isLoading || !types.data) return <div className="space-y-3"><Skeleton className="h-10" /><Skeleton className="h-24" /><Skeleton className="h-10" /></div>

  const setDetail = (name: string, value: string | number | boolean | null) => {
    const next = { ...effectiveDetails }
    if (value === null || value === '') delete next[name]
    else next[name] = value
    setDetails(next)
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (quantityInvalid || dateInvalid) return
    setSaving(true)
    setError(null)
    const body: ActivityInput = {
      activity_type: typeKey,
      quantity: isFlightRoute ? null : qty,
      unit: isFlightRoute ? null : effectiveUnit || null,
      occurred_on: date,
      details: effectiveDetails,
      description: description.trim() || null,
      for_organization: forOrg,
    }
    try {
      const saved = initial ? await activityApi.update(initial.id, body) : await activityApi.create(body)
      onSaved(saved)
      if (!initial) {
        setQuantity('')
        setDescription('')
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save the activity.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-5" noValidate>
      <fieldset>
        <legend className="label">Category</legend>
        <div className="flex flex-wrap gap-2">
          {GROUPS.filter((g) => types.data.some((t) => t.category === g.category)).map((g) => {
            const Icon = CATEGORY_META[g.category].icon
            return (
              <button key={g.category} type="button" aria-pressed={group === g.category}
                onClick={() => {
                  setGroup(g.category)
                  const first = types.data.find((t) => t.category === g.category)
                  if (first) selectType(first.key)
                }}
                className={clsx('inline-flex items-center gap-1.5 rounded-xl border px-3 py-2 text-sm font-medium transition',
                  group === g.category ? 'border-brand bg-brand text-white' : 'border-line bg-white text-ink hover:border-algae-light hover:bg-mint/50')}>
                <Icon className="h-4 w-4" aria-hidden />{g.label}
              </button>
            )
          })}
        </div>
      </fieldset>

      {groupTypes.length > 1 && (
        <div>
          <label htmlFor="activity-type" className="label">Activity</label>
          <select id="activity-type" className="input" value={typeKey} onChange={(e) => selectType(e.target.value)}>
            {groupTypes.map((t) => <option key={t.key} value={t.key}>{t.label}</option>)}
          </select>
        </div>
      )}
      {spec && <p className="-mt-2 text-xs text-muted">{spec.description}</p>}

      {spec && (
        <div className="grid gap-4 sm:grid-cols-2">
          {spec.fields.map((f) => {
            const id = `f-${f.name}`
            const value = effectiveDetails[f.name]
            if (f.type === 'boolean') {
              return (
                <label key={f.name} htmlFor={id} className="flex cursor-pointer items-center gap-3 self-end rounded-xl border border-line bg-white px-3.5 py-2.5 text-sm">
                  <input id={id} type="checkbox" className="h-4 w-4 accent-[#059669]" checked={Boolean(value)} onChange={(e) => setDetail(f.name, e.target.checked)} />
                  {f.label}
                </label>
              )
            }
            return (
              <div key={f.name}>
                <label htmlFor={id} className="label">{f.label}{f.required && <span className="text-red-600"> *</span>}</label>
                {f.type === 'select' ? (
                  <select id={id} className="input" value={String(value ?? '')} onChange={(e) => setDetail(f.name, e.target.value)}>
                    {f.choices.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
                  </select>
                ) : f.type === 'airport' ? (
                  <>
                    <input id={id} className="input uppercase" list="airport-list" maxLength={3} placeholder={f.help ?? ''} value={String(value ?? '')}
                      onChange={(e) => setDetail(f.name, e.target.value.toUpperCase())} />
                  </>
                ) : (
                  <input id={id} className="input" type={f.type === 'number' ? 'number' : 'text'} min={f.min ?? undefined} max={f.max ?? undefined}
                    step="any" value={String(value ?? '')}
                    onChange={(e) => setDetail(f.name, f.type === 'number' ? (e.target.value === '' ? null : Number(e.target.value)) : e.target.value)} />
                )}
                {f.help && f.type !== 'airport' && <p className="mt-1 text-xs text-muted">{f.help}</p>}
              </div>
            )
          })}
          <datalist id="airport-list">
            {(airports.data ?? []).map((a) => <option key={a.iata} value={a.iata}>{`${a.city} — ${a.name}`}</option>)}
          </datalist>
        </div>
      )}

      {spec && (
        <div className="grid gap-4 sm:grid-cols-[1fr_auto_1fr]">
          <div>
            <label htmlFor="quantity" className="label">{spec.quantity_label}</label>
            <input id="quantity" className="input" type="number" min={0} step="any" inputMode="decimal" value={quantity}
              disabled={isFlightRoute} placeholder={isFlightRoute ? 'Calculated from airports' : ''}
              aria-invalid={quantityInvalid && quantity !== ''} onChange={(e) => setQuantity(e.target.value)} />
          </div>
          <div>
            <label htmlFor="unit" className="label">Unit</label>
            {spec.mode === 'custom' ? (
              <input id="unit" className="input sm:w-32" maxLength={24} value={unit} onChange={(e) => setUnit(e.target.value)} placeholder="e.g. item" />
            ) : (
              <select id="unit" className="input sm:w-32" value={effectiveUnit} disabled={isFlightRoute} onChange={(e) => setUnit(e.target.value)}>
                {spec.units.map((u) => <option key={u} value={u}>{u.replace('_', ' ')}</option>)}
              </select>
            )}
          </div>
          <div>
            <label htmlFor="date" className="label">Date</label>
            <input id="date" className="input" type="date" max={todayIso()} value={date} aria-invalid={dateInvalid} onChange={(e) => setDate(e.target.value)} />
          </div>
        </div>
      )}

      <div>
        <label htmlFor="description" className="label">Note <span className="font-normal text-muted">(optional)</span></label>
        <input id="description" className="input" maxLength={300} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. Commute to the office" />
      </div>

      {user?.organization && (
        <label className="flex cursor-pointer items-center gap-3 text-sm">
          <input type="checkbox" className="h-4 w-4 accent-[#059669]" checked={forOrg} onChange={(e) => setForOrg(e.target.checked)} />
          Log for <strong>{user.organization.name}</strong> (counts towards the organisation, not your personal footprint)
        </label>
      )}

      <div className="rounded-2xl border border-algae-light/60 bg-mint/50 p-4" aria-live="polite">
        <div className="flex items-center gap-2 text-sm font-semibold text-forest">
          <Calculator className="h-4 w-4" aria-hidden /> Live estimate
          {preview.isFetching && <Loader2 className="h-3.5 w-3.5 animate-spin text-brand" aria-label="Calculating" />}
        </div>
        {preview.data && !preview.error ? (
          <div className="mt-2 space-y-1.5">
            <p className="font-display text-2xl font-extrabold text-forest">{formatKg(preview.data.co2e_kg, { precise: true })} <span className="text-sm font-semibold text-muted">CO₂e</span></p>
            <p className="font-mono text-xs break-words text-ink">{preview.data.calculation_method}</p>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
              <QualityBadge quality={preview.data.data_quality} />
              <span>{preview.data.factor_key} · {preview.data.factor_region} · {preview.data.factor_source}</span>
            </div>
            {preview.data.assumptions.map((a) => <p key={a} className="text-xs text-muted">• {a}</p>)}
          </div>
        ) : preview.error ? (
          <p className="mt-2 text-sm text-red-700">{preview.error instanceof Error ? preview.error.message : 'Invalid input'}</p>
        ) : (
          <p className="mt-2 text-sm text-muted">Enter a quantity to see the calculated CO₂e and the factor used.</p>
        )}
      </div>

      {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</p>}
      {dateInvalid && <p className="text-xs text-red-600">Choose a date that isn’t in the future.</p>}
      <Button type="submit" size="lg" className="w-full" loading={saving} disabled={quantityInvalid || dateInvalid || Boolean(preview.error)} icon={<Save className="h-4 w-4" />}>
        {submitLabel}
      </Button>
    </form>
  )
}
