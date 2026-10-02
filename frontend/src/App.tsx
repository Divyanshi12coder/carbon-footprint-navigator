import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'

import { GuestOnly, RequireAdmin, RequireAuth } from './components/RouteGuards'
import { AppLayout } from './layouts/AppLayout'
import { PublicLayout } from './layouts/PublicLayout'
import LandingPage from './pages/LandingPage'

// Route-level code splitting: the landing page loads eagerly, everything else on demand.
const LoginPage = lazy(() => import('./pages/auth/LoginPage'))
const RegisterPage = lazy(() => import('./pages/auth/RegisterPage'))
const MethodologyPage = lazy(() => import('./pages/MethodologyPage'))
const OnboardingPage = lazy(() => import('./pages/OnboardingPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const ActivitiesPage = lazy(() => import('./pages/ActivitiesPage'))
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'))
const InsightsPage = lazy(() => import('./pages/InsightsPage'))
const RecommendationsPage = lazy(() => import('./pages/RecommendationsPage'))
const ScenarioPage = lazy(() => import('./pages/ScenarioPage'))
const GoalsPage = lazy(() => import('./pages/GoalsPage'))
const AssistantPage = lazy(() => import('./pages/AssistantPage'))
const OrganizationPage = lazy(() => import('./pages/OrganizationPage'))
const ProfilePage = lazy(() => import('./pages/ProfilePage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const AdminFactorsPage = lazy(() => import('./pages/AdminFactorsPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

export default function App() {
  return (
    <Suspense fallback={null}>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route index element={<LandingPage />} />
          <Route path="methodology" element={<MethodologyPage />} />
        </Route>
        <Route path="login" element={<GuestOnly><LoginPage /></GuestOnly>} />
        <Route path="register" element={<GuestOnly><RegisterPage /></GuestOnly>} />
        <Route path="onboarding" element={<RequireAuth allowOnboarding><OnboardingPage /></RequireAuth>} />
        <Route path="app" element={<RequireAuth><AppLayout /></RequireAuth>}>
          <Route index element={<DashboardPage />} />
          <Route path="activities" element={<ActivitiesPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="insights" element={<InsightsPage />} />
          <Route path="recommendations" element={<RecommendationsPage />} />
          <Route path="scenarios" element={<ScenarioPage />} />
          <Route path="goals" element={<GoalsPage />} />
          <Route path="assistant" element={<AssistantPage />} />
          <Route path="organization" element={<OrganizationPage />} />
          <Route path="profile" element={<ProfilePage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="admin/factors" element={<RequireAdmin><AdminFactorsPage /></RequireAdmin>} />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
