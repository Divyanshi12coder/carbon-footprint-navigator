import {
  Car,
  Flame,
  Laptop,
  Leaf,
  type LucideIcon,
  Plane,
  Recycle,
  ShoppingBag,
  Briefcase,
  Utensils,
} from 'lucide-react'

import type { Category } from '../types/api'

/**
 * Categorical chart colours. Order and hex values were validated with the dataviz palette
 * validator (lightness band, chroma, adjacent CVD separation, normal-vision floor). The order
 * below is the fixed stacking/legend order — never re-sorted by value, so colour follows the
 * category, not its rank. Low-contrast slots (yellow, magenta) are always paired with labels.
 */
export const CATEGORY_ORDER: Category[] = [
  'flights',
  'energy',
  'transport',
  'food',
  'consumption',
  'waste',
  'digital',
  'business',
  'other',
]

export const CATEGORY_META: Record<Category, { label: string; color: string; icon: LucideIcon }> = {
  flights: { label: 'Flights', color: '#2a78d6', icon: Plane },
  energy: { label: 'Energy', color: '#eb6834', icon: Flame },
  transport: { label: 'Transport', color: '#059669', icon: Car },
  food: { label: 'Food', color: '#eda100', icon: Utensils },
  consumption: { label: 'Consumption', color: '#e87ba4', icon: ShoppingBag },
  waste: { label: 'Waste', color: '#008300', icon: Recycle },
  digital: { label: 'Digital', color: '#4a3aa7', icon: Laptop },
  business: { label: 'Business', color: '#e34948', icon: Briefcase },
  other: { label: 'Other', color: '#8a948f', icon: Leaf },
}

export const categoryLabel = (c: string | null | undefined) =>
  c && c in CATEGORY_META ? CATEGORY_META[c as Category].label : 'All categories'

export const categoryColor = (c: string) => (c in CATEGORY_META ? CATEGORY_META[c as Category].color : '#8a948f')

/** Categories present in data, in the fixed palette order. */
export function presentCategories(keys: Iterable<string>): Category[] {
  const set = new Set(keys)
  return CATEGORY_ORDER.filter((c) => set.has(c))
}

export const ACTIVITY_LABELS: Record<string, string> = {
  car: 'Car journey',
  motorcycle: 'Motorcycle',
  taxi: 'Taxi',
  public_transport: 'Public transport',
  active_travel: 'Walking / cycling',
  flight: 'Flight',
  electricity: 'Electricity',
  natural_gas: 'Natural gas',
  lpg: 'LPG',
  heating_oil: 'Heating oil',
  meal: 'Meals',
  diet_day: 'Day of eating',
  waste: 'Waste',
  purchase: 'Purchase',
  product: 'Product',
  streaming: 'Streaming',
  hotel_stay: 'Hotel stay',
  custom: 'Custom',
}

export const activityLabel = (t: string) => ACTIVITY_LABELS[t] ?? t.replace(/_/g, ' ')
