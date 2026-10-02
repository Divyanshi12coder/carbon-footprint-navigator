// Types mirror the FastAPI response schemas (backend/app/schemas).

export type Category =
  | 'transport'
  | 'flights'
  | 'energy'
  | 'food'
  | 'waste'
  | 'consumption'
  | 'digital'
  | 'business'
  | 'other'

export type RangeKey = '7d' | '30d' | '90d' | '180d' | '365d' | 'custom'
export type Quality = 'high' | 'medium' | 'low'

export interface OrganizationBrief {
  id: string
  name: string
}

export interface User {
  id: string
  email: string
  full_name: string
  role: 'user' | 'admin'
  onboarding_completed: boolean
  organization: OrganizationBrief | null
  org_role: 'owner' | 'member' | null
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface Profile {
  country: string | null
  region: string | null
  household_size: number | null
  primary_transport: 'car' | 'public_transport' | 'active' | 'mixed' | null
  vehicle_type: 'petrol' | 'diesel' | 'hybrid' | 'plugin_hybrid' | 'electric' | 'none' | null
  weekly_car_km: number | null
  weekly_public_transport_km: number | null
  short_haul_flights_per_year: number | null
  long_haul_flights_per_year: number | null
  monthly_electricity_kwh: number | null
  renewable_share_pct: number | null
  heating_fuel: 'natural_gas' | 'heating_oil' | 'lpg' | 'electric' | 'none' | null
  monthly_heating_kwh: number | null
  diet_type: 'meat_heavy' | 'mixed' | 'low_meat' | 'pescatarian' | 'vegetarian' | 'vegan' | null
  shopping_level: 'low' | 'medium' | 'high' | null
  monthly_clothing_spend_usd: number | null
  monthly_electronics_spend_usd: number | null
  weekly_waste_kg: number | null
  recycling_level: 'none' | 'some' | 'most' | null
  composts: boolean | null
}

export type ProfileInput = Partial<Profile>

export interface OnboardingInput extends ProfileInput {
  organization_name?: string
  organization_industry?: string
  organization_employee_count?: number
}

export interface Preferences {
  distance_unit: 'km' | 'mi'
  default_range: Exclude<RangeKey, 'custom'>
  monthly_budget_kg: number | null
}

export interface BaselineItem {
  factor_key: string
  category: Category
  monthly_quantity: number
  unit: string
  factor_value: number
  monthly_kg: number
}

export interface Baseline {
  basis: 'tracked_activities' | 'onboarding_profile' | 'none'
  monthly_total_kg: number
  annual_total_kg: number
  by_category_monthly_kg: Partial<Record<Category, number>>
  items: BaselineItem[]
  assumptions: string[]
}

// ----- Activity catalogue -----
export interface Choice {
  value: string
  label: string
}

export interface FieldSpec {
  name: string
  label: string
  type: 'select' | 'number' | 'text' | 'boolean' | 'airport'
  required: boolean
  default: string | number | boolean | null
  choices: Choice[]
  min: number | null
  max: number | null
  help: string | null
}

export interface ActivityTypeSpec {
  key: string
  category: Category
  label: string
  description: string
  quantity_label: string
  units: string[]
  fields: FieldSpec[]
  mode: 'standard' | 'flight' | 'custom'
}

export interface Airport {
  iata: string
  name: string
  city: string
  country: string
}

export type ActivityDetails = Record<string, string | number | boolean>

export interface Emission {
  id: string
  co2e_kg: number
  factor_key: string
  factor_value: number
  factor_unit: string
  factor_source: string
  emission_factor_id: string | null
  normalized_quantity: number
  calculation_method: string
  data_quality: Quality
  assumptions: string[]
}

export interface Activity {
  id: string
  category: Category
  activity_type: string
  description: string | null
  quantity: number
  unit: string
  occurred_on: string
  details: ActivityDetails
  source: string
  organization_id: string | null
  created_at: string
  emission: Emission
}

export interface ActivityInput {
  activity_type: string
  quantity: number | null
  unit: string | null
  occurred_on: string
  details: ActivityDetails
  description?: string | null
  for_organization?: boolean
}

export interface Preview {
  category: Category
  co2e_kg: number
  factor_key: string
  factor_value: number
  factor_unit: string
  factor_source: string
  factor_region: string
  normalized_quantity: number
  calculation_method: string
  data_quality: Quality
  assumptions: string[]
  details: ActivityDetails
}

export interface Page<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

// ----- Analytics -----
export interface TimelinePoint {
  period_start: string
  period_end?: string
  total_kg: number
  rolling_7d_kg?: number
  [category: string]: number | string | undefined
}

export interface CategoryRow {
  category: Category
  kg: number
  share_pct: number
  previous_kg: number
  change_pct: number | null
}

export interface DashboardSummary {
  range: { start: string; end: string; days: number }
  previous_range: { start: string; end: string }
  totals: {
    total_kg: number
    previous_total_kg: number
    change_pct: number | null
    daily_average_kg: number
    weekly_average_kg: number
    monthly_equivalent_kg: number
    annualized_kg: number
    activity_count: number
  }
  snapshot: { today_kg: number; last_7_days_kg: number; last_30_days_kg: number; month_to_date_kg: number }
  categories: CategoryRow[]
  granularity: 'day' | 'week'
  timeline: TimelinePoint[]
  top_activity_types: { activity_type: string; count: number; kg: number }[]
  data_quality: Partial<Record<Quality, number>>
  benchmark: { label: string; annual_kg: number; source: string; source_url: string }
}

export interface Timeseries {
  granularity: 'day' | 'week' | 'month'
  category: Category | null
  points: TimelinePoint[]
}

export interface BreakdownRow {
  activity_type: string
  factor_key: string
  category: Category
  unit: string
  count: number
  quantity: number
  kg: number
  avg_kg_per_activity: number
  share_pct: number
}

export interface MonthlyRow {
  month: string
  total_kg: number
  [category: string]: number | string
}

// ----- ML -----
export interface ForecastPoint {
  date: string
  predicted_kg: number
  lower_kg: number
  upper_kg: number
}

export interface Forecast {
  status: 'ok' | 'insufficient_data'
  horizon_days: number
  model_name: string | null
  points: ForecastPoint[]
  history: { date: string; actual_kg: number; rolling_7d_kg: number }[]
  predicted_total_kg: number | null
  lower_total_kg: number | null
  upper_total_kg: number | null
  recent_total_kg: number | null
  metrics: {
    selected_model?: string
    holdout_days?: number
    training_days?: number
    mae_kg_per_day?: number
    rmse_kg_per_day?: number
    skill_vs_moving_average?: number | null
    holdout_bias_kg_per_day?: number
    interval?: string
    candidates?: Record<string, { mae: number; rmse: number; smape: number }>
  }
  notes: string[]
}

export interface Anomaly {
  method: 'weekly_robust_z' | 'isolation_forest'
  category: Category | null
  date: string | null
  period_start: string | null
  period_end: string | null
  observed_kg: number
  expected_kg: number
  pct_above: number
  score: number
  message: string
}

export interface Insight {
  id: string
  insight_type: string
  severity: 'positive' | 'info' | 'warning'
  title: string
  body: string
  category: Category | null
  metric_value: number | null
  data: Record<string, unknown>
  generated_at: string
}

export type RecommendationStatus = 'open' | 'accepted' | 'dismissed' | 'completed'

export interface Recommendation {
  id: string
  rec_key: string
  category: Category
  title: string
  reason: string
  current_behavior: string
  suggested_action: string
  estimated_monthly_reduction_kg: number
  share_of_footprint_pct: number
  difficulty: 'easy' | 'medium' | 'hard'
  calculation_basis: string
  data_basis: 'tracked_activities' | 'onboarding_profile'
  priority_score: number
  status: RecommendationStatus
  updated_at: string
}

export interface ScenarioLevers {
  car_reduction_pct: number
  ev_adoption_pct: number
  flight_reduction_pct: number
  electricity_reduction_pct: number
  renewable_share_pct: number
  heating_reduction_pct: number
  meat_reduction_pct: number
  recycling_improvement_pct: number
}

export interface ScenarioResult {
  basis: Baseline['basis']
  current_monthly_kg: number
  scenario_monthly_kg: number
  reduction_monthly_kg: number
  reduction_pct: number
  current_annual_kg: number
  scenario_annual_kg: number
  current_by_category: Partial<Record<Category, number>>
  scenario_by_category: Partial<Record<Category, number>>
  lever_effects: { lever: keyof ScenarioLevers; label: string; value: number; monthly_reduction_kg: number }[]
  assumptions: string[]
  available_levers: (keyof ScenarioLevers)[]
}

// ----- Goals & achievements -----
export interface GoalProgress {
  target_monthly_kg: number
  current_monthly_kg: number | null
  progress_pct: number
  reduction_achieved_pct: number | null
  on_track: boolean
  days_elapsed: number
  days_remaining: number
  measurement: string
}

export interface Goal {
  id: string
  title: string
  category: Category | null
  baseline_monthly_kg: number
  target_reduction_pct: number
  start_date: string
  deadline: string
  status: 'active' | 'achieved' | 'missed' | 'archived'
  achieved_at: string | null
  created_at: string
  progress: GoalProgress
}

export interface GoalInput {
  title: string
  category: Category | null
  target_reduction_pct: number
  baseline_monthly_kg?: number | null
  deadline: string
}

export interface Achievement {
  code: string
  title: string
  description: string
  achieved: boolean
  achieved_at: string | null
}

// ----- Assistant -----
export interface AssistantStatus {
  mode: 'llm' | 'demo'
  provider: string | null
  model: string | null
  description: string
  suggested_questions: string[]
}

export interface Conversation {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  mode: 'llm' | 'demo' | null
  model: string | null
  validation: { status?: 'verified' | 'flagged'; numbers_checked?: number; unverified?: string[] }
  context_used: { intents?: string[]; topics?: string[]; facts?: Record<string, unknown> }
  created_at: string
}

export interface ConversationDetail extends Conversation {
  messages: ChatMessage[]
}

// ----- Emission factors & organisations -----
export interface EmissionFactor {
  id: string
  key: string
  category: Category
  name: string
  region: string
  unit: string
  co2e_per_unit: number
  source: string
  source_url: string | null
  year: number | null
  quality: Quality
  notes: string | null
  version: number
  is_active: boolean
  change_reason: string | null
  updated_at: string
}

export interface Organization {
  id: string
  name: string
  industry: string | null
  country: string | null
  employee_count: number | null
  join_code: string | null
  created_at: string
}

export interface OrgMember {
  user_id: string
  full_name: string
  org_role: 'owner' | 'member'
  contributed_kg: number
  activity_count: number
}

export interface OrgDashboard extends DashboardSummary {
  by_activity: BreakdownRow[]
  monthly: MonthlyRow[]
}
