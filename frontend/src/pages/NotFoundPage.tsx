import { Compass } from 'lucide-react'

import { ButtonLink } from '../components/ui/Button'
import { Logo } from '../components/ui/misc'

export default function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center bg-gradient-to-b from-mint/60 to-offwhite px-4 text-center">
      <div>
        <Logo />
        <Compass className="mx-auto mt-10 h-12 w-12 text-brand" aria-hidden />
        <h1 className="mt-4 text-3xl font-extrabold text-forest">Page not found</h1>
        <p className="mt-2 text-muted">This path doesn’t lead anywhere — let’s get you back on course.</p>
        <div className="mt-6 flex justify-center gap-2">
          <ButtonLink to="/">Home</ButtonLink>
          <ButtonLink to="/app" variant="secondary">Dashboard</ButtonLink>
        </div>
      </div>
    </main>
  )
}
