import type {
  Achievement,
  Activity,
  ActivityInput,
  ActivityTypeSpec,
  Airport,
  Anomaly,
  AssistantStatus,
  Baseline,
  BreakdownRow,
  ChatMessage,
  Conversation,
  ConversationDetail,
  DashboardSummary,
  EmissionFactor,
  Forecast,
  Goal,
  GoalInput,
  Insight,
  MonthlyRow,
  OnboardingInput,
  OrgDashboard,
  OrgMember,
  Organization,
  Page,
  Preferences,
  Preview,
  Profile,
  ProfileInput,
  RangeKey,
  Recommendation,
  RecommendationStatus,
  ScenarioLevers,
  ScenarioResult,
  Timeseries,
  TokenResponse,
  User,
} from '../types/api'
import { api, json } from './client'

export interface RangeParams {
  range: RangeKey
  start?: string
  end?: string
}

const qs = (params: object) => {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

export const authApi = {
  register: (body: { email: string; password: string; full_name: string }) =>
    api<TokenResponse>('/auth/register', { method: 'POST', body: json(body), auth: false }),
  login: (body: { email: string; password: string }) =>
    api<TokenResponse>('/auth/login', { method: 'POST', body: json(body), auth: false }),
  me: () => api<User>('/auth/me'),
  logout: () => api<{ detail: string }>('/auth/logout', { method: 'POST' }),
  changePassword: (body: { current_password: string; new_password: string }) =>
    api<TokenResponse>('/auth/change-password', { method: 'POST', body: json(body) }),
}

export const profileApi = {
  get: () => api<Profile | null>('/profile'),
  update: (body: ProfileInput) => api<Profile>('/profile', { method: 'PUT', body: json(body) }),
  onboarding: (body: OnboardingInput) => api<User>('/profile/onboarding', { method: 'POST', body: json(body) }),
  baseline: () => api<Baseline>('/profile/baseline'),
  preferences: () => api<Preferences>('/profile/preferences'),
  updatePreferences: (body: Partial<Preferences>) =>
    api<Preferences>('/profile/preferences', { method: 'PUT', body: json(body) }),
}

export interface ActivityQuery {
  page?: number
  page_size?: number
  category?: string
  activity_type?: string
  date_from?: string
  date_to?: string
  search?: string
  scope?: 'personal' | 'organization' | 'all'
  sort?: 'occurred_on' | 'created_at' | 'co2e_kg' | 'category'
  order?: 'asc' | 'desc'
}

export const activityApi = {
  types: () => api<ActivityTypeSpec[]>('/activities/types', { auth: false }),
  airports: () => api<Airport[]>('/activities/airports', { auth: false }),
  list: (q: ActivityQuery) => api<Page<Activity>>(`/activities${qs(q)}`),
  create: (body: ActivityInput) => api<Activity>('/activities', { method: 'POST', body: json(body) }),
  update: (id: string, body: Partial<ActivityInput>) =>
    api<Activity>(`/activities/${id}`, { method: 'PATCH', body: json(body) }),
  remove: (id: string) => api<void>(`/activities/${id}`, { method: 'DELETE' }),
  preview: (body: Pick<ActivityInput, 'activity_type' | 'quantity' | 'unit' | 'details'>) =>
    api<Preview>('/activities/preview', { method: 'POST', body: json(body) }),
}

export const analyticsApi = {
  summary: (p: RangeParams) => api<DashboardSummary>(`/dashboard/summary${qs(p)}`),
  timeseries: (p: RangeParams & { granularity?: 'day' | 'week' | 'month'; category?: string }) =>
    api<Timeseries>(`/emissions/timeseries${qs(p)}`),
  breakdown: (p: RangeParams) => api<BreakdownRow[]>(`/emissions/breakdown${qs(p)}`),
  monthly: (months = 12) => api<MonthlyRow[]>(`/emissions/monthly${qs({ months })}`),
}

export const mlApi = {
  forecast: (horizon: number) => api<Forecast>(`/forecast${qs({ horizon })}`),
  anomalies: () => api<Anomaly[]>('/anomalies'),
  insights: () => api<Insight[]>('/insights'),
  refreshInsights: () => api<Insight[]>('/insights/refresh', { method: 'POST' }),
  recommendations: (includeDismissed = false) =>
    api<Recommendation[]>(`/recommendations${qs({ include_dismissed: includeDismissed || undefined })}`),
  refreshRecommendations: () => api<Recommendation[]>('/recommendations/refresh', { method: 'POST' }),
  setRecommendationStatus: (id: string, status: RecommendationStatus) =>
    api<Recommendation>(`/recommendations/${id}`, { method: 'PATCH', body: json({ status }) }),
  scenarioBaseline: () => api<Baseline>('/scenarios/baseline'),
  simulate: (levers: ScenarioLevers) =>
    api<ScenarioResult>('/scenarios/simulate', { method: 'POST', body: json(levers) }),
}

export const goalApi = {
  list: () => api<Goal[]>('/goals'),
  create: (body: GoalInput) => api<Goal>('/goals', { method: 'POST', body: json(body) }),
  update: (id: string, body: Partial<Pick<Goal, 'title' | 'deadline'>> & { status?: 'active' | 'archived' }) =>
    api<Goal>(`/goals/${id}`, { method: 'PATCH', body: json(body) }),
  remove: (id: string) => api<void>(`/goals/${id}`, { method: 'DELETE' }),
  achievements: () => api<Achievement[]>('/achievements'),
}

export const assistantApi = {
  status: () => api<AssistantStatus>('/assistant/status'),
  conversations: () => api<Conversation[]>('/assistant/conversations'),
  create: () => api<Conversation>('/assistant/conversations', { method: 'POST', body: json({}) }),
  get: (id: string) => api<ConversationDetail>(`/assistant/conversations/${id}`),
  remove: (id: string) => api<void>(`/assistant/conversations/${id}`, { method: 'DELETE' }),
  ask: (id: string, question: string) =>
    api<ChatMessage>(`/assistant/conversations/${id}/messages`, { method: 'POST', body: json({ question }) }),
}

export const factorApi = {
  list: (p: { category?: string; search?: string; include_inactive?: boolean } = {}) =>
    api<EmissionFactor[]>(`/emission-factors${qs(p)}`),
  history: (id: string) => api<EmissionFactor[]>(`/emission-factors/${id}/history`),
  update: (id: string, body: Partial<Pick<EmissionFactor, 'co2e_per_unit' | 'source' | 'source_url' | 'year' | 'quality' | 'notes' | 'name'>> & { change_reason: string }) =>
    api<EmissionFactor>(`/emission-factors/${id}`, { method: 'PUT', body: json(body) }),
  deactivate: (id: string) => api<EmissionFactor>(`/emission-factors/${id}`, { method: 'DELETE' }),
}

export const orgApi = {
  mine: () => api<Organization>('/organizations/me'),
  create: (body: { name: string; industry?: string; country?: string; employee_count?: number }) =>
    api<Organization>('/organizations', { method: 'POST', body: json(body) }),
  join: (join_code: string) => api<Organization>('/organizations/join', { method: 'POST', body: json({ join_code }) }),
  leave: () => api<{ detail: string }>('/organizations/leave', { method: 'POST' }),
  members: () => api<OrgMember[]>('/organizations/me/members'),
  dashboard: (p: RangeParams) => api<OrgDashboard>(`/organizations/me/dashboard${qs(p)}`),
}
