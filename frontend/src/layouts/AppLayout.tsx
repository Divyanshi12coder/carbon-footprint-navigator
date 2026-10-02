import { clsx } from 'clsx'
import { AnimatePresence, motion } from 'framer-motion'
import {
  BarChart3,
  Bot,
  Building2,
  FlaskConical,
  Lightbulb,
  LayoutDashboard,
  ListPlus,
  LogOut,
  Menu,
  Settings,
  Sparkles,
  Target,
  UserRound,
  X,
} from 'lucide-react'
import { Suspense, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'

import { ErrorBoundary } from '../components/ErrorBoundary'
import { CardSkeleton } from '../components/ui/feedback'
import { Logo } from '../components/ui/misc'
import { useAuth } from '../hooks/useAuth'

export const NAV = [
  { to: '/app', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/app/activities', label: 'Activities', icon: ListPlus },
  { to: '/app/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/app/insights', label: 'Insights', icon: Sparkles },
  { to: '/app/recommendations', label: 'Recommendations', icon: Lightbulb },
  { to: '/app/scenarios', label: 'Scenario Simulator', icon: FlaskConical },
  { to: '/app/goals', label: 'Goals', icon: Target },
  { to: '/app/assistant', label: 'AI Assistant', icon: Bot },
  { to: '/app/organization', label: 'Organization', icon: Building2 },
  { to: '/app/profile', label: 'Profile', icon: UserRound },
  { to: '/app/settings', label: 'Settings', icon: Settings },
] as const

const MOBILE_TABS = [NAV[0], NAV[1], NAV[5], NAV[7]]

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <ul className="space-y-1">
      {NAV.map(({ to, label, icon: Icon, ...rest }) => (
        <li key={to}>
          <NavLink
            to={to}
            end={'end' in rest}
            onClick={onNavigate}
            className={({ isActive }) =>
              clsx(
                'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition',
                isActive ? 'bg-brand text-white shadow-[0_8px_20px_-10px_rgb(5_150_105/0.8)]' : 'text-white/75 hover:bg-white/10 hover:text-white',
              )
            }
          >
            <Icon className="h-[18px] w-[18px] shrink-0" aria-hidden />
            {label}
          </NavLink>
        </li>
      ))}
    </ul>
  )
}

function UserFooter() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  return (
    <div className="mt-auto border-t border-white/10 pt-4">
      <div className="mb-3 flex items-center gap-3 px-1">
        <div className="grid h-9 w-9 place-items-center rounded-full bg-algae text-sm font-bold text-white" aria-hidden>
          {user?.full_name.slice(0, 1).toUpperCase()}
        </div>
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-white">{user?.full_name}</p>
          <p className="truncate text-xs text-white/60">{user?.email}</p>
        </div>
      </div>
      <button
        type="button"
        onClick={async () => {
          await logout()
          navigate('/login', { replace: true })
        }}
        className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-white/75 transition hover:bg-white/10 hover:text-white"
      >
        <LogOut className="h-[18px] w-[18px]" aria-hidden /> Sign out
      </button>
    </div>
  )
}

export function AppLayout() {
  const [drawer, setDrawer] = useState(false)
  const location = useLocation()

  return (
    <div className="min-h-screen bg-offwhite lg:pl-72">
      <a href="#app-main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2">Skip to content</a>

      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 flex-col bg-forest bg-[radial-gradient(120%_60%_at_0%_0%,rgba(63,174,114,0.25),transparent_60%)] p-5 lg:flex" aria-label="Application">
        <Link to="/" className="mb-8 px-1"><Logo light /></Link>
        <nav className="overflow-y-auto" aria-label="App sections"><NavItems /></nav>
        <UserFooter />
      </aside>

      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-line bg-white/90 px-4 backdrop-blur lg:hidden">
        <Link to="/app" aria-label="Dashboard"><Logo compact /></Link>
        <button type="button" onClick={() => setDrawer(true)} aria-label="Open navigation" aria-expanded={drawer} className="rounded-lg p-2 text-forest">
          <Menu className="h-6 w-6" />
        </button>
      </header>

      {/* Mobile drawer */}
      <AnimatePresence>
        {drawer && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <motion.div className="absolute inset-0 bg-forest/50" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setDrawer(false)} />
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'tween', duration: 0.25 }}
              className="absolute inset-y-0 left-0 flex w-[82%] max-w-xs flex-col bg-forest p-5"
              aria-label="Navigation"
            >
              <div className="mb-6 flex items-center justify-between">
                <Logo light />
                <button type="button" onClick={() => setDrawer(false)} aria-label="Close navigation" className="rounded-lg p-1.5 text-white/80 hover:bg-white/10">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <nav className="overflow-y-auto"><NavItems onNavigate={() => setDrawer(false)} /></nav>
              <UserFooter />
            </motion.aside>
          </div>
        )}
      </AnimatePresence>

      <main id="app-main" className="mx-auto max-w-7xl px-4 pt-6 pb-28 sm:px-6 lg:px-10 lg:pt-10 lg:pb-12">
        <Suspense fallback={<div className="grid gap-4 md:grid-cols-2"><CardSkeleton rows={5} /><CardSkeleton rows={5} /></div>}>
          <ErrorBoundary resetKey={location.pathname}>
            <motion.div key={location.pathname} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
              <Outlet />
            </motion.div>
          </ErrorBoundary>
        </Suspense>
      </main>

      {/* Mobile bottom navigation */}
      <nav className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-4 border-t border-line bg-white/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden" aria-label="Quick navigation">
        {MOBILE_TABS.map(({ to, label, icon: Icon, ...rest }) => (
          <NavLink key={to} to={to} end={'end' in rest}
            className={({ isActive }) => clsx('flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium', isActive ? 'text-brand' : 'text-muted')}>
            <Icon className="h-5 w-5" aria-hidden />
            {label.replace('Scenario Simulator', 'Scenarios').replace('AI Assistant', 'Assistant')}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
