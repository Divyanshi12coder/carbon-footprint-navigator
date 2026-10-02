import { Loader2 } from 'lucide-react'
import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '../hooks/useAuth'

function FullPageSpinner() {
  return (
    <div className="grid min-h-screen place-items-center" role="status" aria-label="Loading">
      <Loader2 className="h-8 w-8 animate-spin text-brand" />
    </div>
  )
}

/** Requires a signed-in user; sends new users through onboarding first. */
export function RequireAuth({ children, allowOnboarding = false }: { children: ReactNode; allowOnboarding?: boolean }) {
  const { status, user } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <FullPageSpinner />
  if (status === 'anonymous' || !user) return <Navigate to="/login" replace state={{ from: location.pathname }} />
  if (!user.onboarding_completed && !allowOnboarding) return <Navigate to="/onboarding" replace />
  return <>{children}</>
}

export function RequireAdmin({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  if (user?.role !== 'admin') return <Navigate to="/app" replace />
  return <>{children}</>
}

export function GuestOnly({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  if (status === 'loading') return <FullPageSpinner />
  if (status === 'authenticated') return <Navigate to="/app" replace />
  return <>{children}</>
}
