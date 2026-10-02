import { Car, Home, MapPin, ShoppingBag, Utensils, type LucideIcon } from 'lucide-react'

import type { ProfileInput } from '../../types/api'

export type ProfileKey = keyof ProfileInput

interface BaseField {
  key: ProfileKey
  label: string
  help?: string
}
interface SelectField extends BaseField {
  type: 'select'
  options: { value: string; label: string }[]
}
interface NumberField extends BaseField {
  type: 'number'
  min: number
  max: number
  step?: number
  unit?: string
}
interface BoolField extends BaseField {
  type: 'boolean'
}
export type FieldDef = SelectField | NumberField | BoolField

export const COUNTRIES = [
  ['GB', 'United Kingdom'], ['US', 'United States'], ['IN', 'India'], ['DE', 'Germany'], ['FR', 'France'], ['CA', 'Canada'],
  ['AU', 'Australia'], ['CN', 'China'], ['JP', 'Japan'], ['BR', 'Brazil'], ['ES', 'Spain'], ['IT', 'Italy'], ['NL', 'Netherlands'],
  ['SE', 'Sweden'], ['NO', 'Norway'], ['ZA', 'South Africa'], ['SG', 'Singapore'], ['NZ', 'New Zealand'], ['IE', 'Ireland'], ['MX', 'Mexico'],
].map(([value, label]) => ({ value, label }))

export const PROFILE_STEPS: { title: string; description: string; icon: LucideIcon; fields: FieldDef[] }[] = [
  {
    title: 'Where you live',
    description: 'Your country selects the electricity grid factor used for your energy.',
    icon: MapPin,
    fields: [
      { key: 'country', label: 'Country', type: 'select', options: COUNTRIES, help: 'Countries without a specific grid factor use the global average.' },
      { key: 'household_size', label: 'People in your household', type: 'number', min: 1, max: 20, help: 'Household energy and waste are divided by this.' },
    ],
  },
  {
    title: 'How you get around',
    description: 'Typical weekly travel and flights per year.',
    icon: Car,
    fields: [
      { key: 'primary_transport', label: 'Main way of travelling', type: 'select', options: [
        { value: 'car', label: 'Car' }, { value: 'public_transport', label: 'Public transport' },
        { value: 'active', label: 'Walking / cycling' }, { value: 'mixed', label: 'A mix' }] },
      { key: 'vehicle_type', label: 'Car type', type: 'select', options: [
        { value: 'petrol', label: 'Petrol' }, { value: 'diesel', label: 'Diesel' }, { value: 'hybrid', label: 'Hybrid' },
        { value: 'plugin_hybrid', label: 'Plug-in hybrid' }, { value: 'electric', label: 'Electric' }, { value: 'none', label: 'No car' }] },
      { key: 'weekly_car_km', label: 'Car distance per week', type: 'number', min: 0, max: 10000, unit: 'km' },
      { key: 'weekly_public_transport_km', label: 'Public transport per week', type: 'number', min: 0, max: 10000, unit: 'km' },
      { key: 'short_haul_flights_per_year', label: 'Short-haul return flights per year', type: 'number', min: 0, max: 200, help: 'Under ~3,700 km, e.g. within Europe.' },
      { key: 'long_haul_flights_per_year', label: 'Long-haul return flights per year', type: 'number', min: 0, max: 100 },
    ],
  },
  {
    title: 'Home energy',
    description: 'From a recent bill if you have one — monthly figures for the whole household.',
    icon: Home,
    fields: [
      { key: 'monthly_electricity_kwh', label: 'Electricity per month', type: 'number', min: 0, max: 100000, unit: 'kWh' },
      { key: 'renewable_share_pct', label: 'Renewable share of electricity', type: 'number', min: 0, max: 100, unit: '%' },
      { key: 'heating_fuel', label: 'Heating fuel', type: 'select', options: [
        { value: 'natural_gas', label: 'Natural gas' }, { value: 'heating_oil', label: 'Heating oil' }, { value: 'lpg', label: 'LPG' },
        { value: 'electric', label: 'Electric' }, { value: 'none', label: 'None / district heating' }] },
      { key: 'monthly_heating_kwh', label: 'Heating energy per month', type: 'number', min: 0, max: 100000, unit: 'kWh' },
    ],
  },
  {
    title: 'Food & shopping',
    description: 'Your usual diet and spending habits.',
    icon: Utensils,
    fields: [
      { key: 'diet_type', label: 'Diet', type: 'select', options: [
        { value: 'meat_heavy', label: 'Meat-heavy' }, { value: 'mixed', label: 'Mixed' }, { value: 'low_meat', label: 'Low meat' },
        { value: 'pescatarian', label: 'Pescatarian' }, { value: 'vegetarian', label: 'Vegetarian' }, { value: 'vegan', label: 'Vegan' }] },
      { key: 'shopping_level', label: 'Shopping habits', type: 'select', options: [
        { value: 'low', label: 'Minimal' }, { value: 'medium', label: 'Average' }, { value: 'high', label: 'Frequent' }],
        help: 'Used only if you skip the spend fields below.' },
      { key: 'monthly_clothing_spend_usd', label: 'Clothing spend per month', type: 'number', min: 0, max: 100000, unit: 'USD' },
      { key: 'monthly_electronics_spend_usd', label: 'Electronics spend per month', type: 'number', min: 0, max: 100000, unit: 'USD' },
    ],
  },
  {
    title: 'Waste',
    description: 'How much your household throws away and how.',
    icon: ShoppingBag,
    fields: [
      { key: 'weekly_waste_kg', label: 'Household waste per week', type: 'number', min: 0, max: 1000, unit: 'kg', help: 'A full kitchen bin bag is roughly 5–8 kg.' },
      { key: 'recycling_level', label: 'How much do you recycle?', type: 'select', options: [
        { value: 'none', label: 'Rarely' }, { value: 'some', label: 'Some of it' }, { value: 'most', label: 'Most of it' }] },
      { key: 'composts', label: 'I compost food or garden waste', type: 'boolean' },
    ],
  },
]

export function FieldInput({ field, value, onChange }: {
  field: FieldDef
  value: ProfileInput[ProfileKey] | undefined
  onChange: (v: ProfileInput[ProfileKey] | null) => void
}) {
  const id = `pf-${field.key}`
  if (field.type === 'boolean') {
    return (
      <label htmlFor={id} className="flex cursor-pointer items-center gap-3 rounded-xl border border-line bg-white px-3.5 py-3 text-sm">
        <input id={id} type="checkbox" className="h-4 w-4 accent-[#059669]" checked={Boolean(value)} onChange={(e) => onChange(e.target.checked)} />
        {field.label}
      </label>
    )
  }
  return (
    <div>
      <label htmlFor={id} className="label">{field.label}</label>
      {field.type === 'select' ? (
        <select id={id} className="input" value={(value as string | null) ?? ''} onChange={(e) => onChange(e.target.value || null)}>
          <option value="">Prefer not to say</option>
          {field.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      ) : (
        <div className="relative">
          <input id={id} type="number" inputMode="decimal" className="input pr-14" min={field.min} max={field.max} step={field.step ?? 'any'}
            value={value === null || value === undefined ? '' : String(value)}
            onChange={(e) => onChange(e.target.value === '' ? null : Number(e.target.value))} />
          {field.unit && <span className="pointer-events-none absolute top-1/2 right-3.5 -translate-y-1/2 text-xs text-muted">{field.unit}</span>}
        </div>
      )}
      {field.help && <p className="mt-1 text-xs text-muted">{field.help}</p>}
    </div>
  )
}

/** Returns an error message for out-of-range numbers, else null. */
export function validateProfileField(field: FieldDef, value: unknown): string | null {
  if (field.type !== 'number' || value === null || value === undefined) return null
  const n = Number(value)
  if (Number.isNaN(n)) return `${field.label} must be a number.`
  if (n < field.min || n > field.max) return `${field.label} must be between ${field.min} and ${field.max}.`
  return null
}
