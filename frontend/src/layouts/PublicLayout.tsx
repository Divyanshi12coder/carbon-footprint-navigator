import { clsx } from 'clsx'
import { AnimatePresence, motion } from 'framer-motion'
import { Menu, X } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'

import { ButtonLink } from '../components/ui/Button'
import { Logo } from '../components/ui/misc'
import { useAuth } from '../hooks/useAuth'

const YEAR = new Date().getFullYear()

const LINKS = [
  { href: '/#features', label: 'Features' },
  { href: '/#how-it-works', label: 'How it works' },
  { href: '/#analytics', label: 'Analytics' },
  { href: '/#sustainability', label: 'Sustainability' },
  { href: '/methodology', label: 'Methodology' },
]

function Navbar() {
  const { status } = useAuth()
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header className={clsx('fixed inset-x-0 top-0 z-40 transition duration-300', scrolled ? 'glass shadow-[var(--shadow-soft)]' : 'bg-transparent')}>
      <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6" aria-label="Main">
        <Link to="/" aria-label="Carbon Footprint Navigator home"><Logo /></Link>
        <ul className="hidden items-center gap-1 lg:flex">
          {LINKS.map((l) => (
            <li key={l.href}>
              <a href={l.href} className="rounded-lg px-3 py-2 text-sm font-medium text-ink/80 transition hover:bg-mint/70 hover:text-forest">{l.label}</a>
            </li>
          ))}
        </ul>
        <div className="hidden items-center gap-2 lg:flex">
          {status === 'authenticated' ? (
            <ButtonLink to="/app" size="sm">Open dashboard</ButtonLink>
          ) : (
            <>
              <ButtonLink to="/login" variant="ghost" size="sm">Sign in</ButtonLink>
              <ButtonLink to="/register" size="sm">Get started</ButtonLink>
            </>
          )}
        </div>
        <button type="button" className="rounded-lg p-2 text-forest lg:hidden" aria-label={open ? 'Close menu' : 'Open menu'}
          aria-expanded={open} onClick={() => setOpen((o) => !o)}>
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </nav>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
            className="glass overflow-hidden border-t border-line lg:hidden">
            <ul className="space-y-1 px-4 py-3">
              {LINKS.map((l) => (
                <li key={l.href}><a href={l.href} onClick={() => setOpen(false)} className="block rounded-lg px-3 py-2.5 font-medium text-ink hover:bg-mint">{l.label}</a></li>
              ))}
            </ul>
            <div className="flex gap-2 px-4 pb-4">
              {status === 'authenticated' ? (
                <ButtonLink to="/app" className="flex-1" onClick={() => setOpen(false)}>Open dashboard</ButtonLink>
              ) : (
                <>
                  <ButtonLink to="/login" variant="secondary" className="flex-1" onClick={() => setOpen(false)}>Sign in</ButtonLink>
                  <ButtonLink to="/register" className="flex-1" onClick={() => setOpen(false)}>Get started</ButtonLink>
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}

function Footer() {
  return (
    <footer className="bg-forest text-white/80">
      <div className="mx-auto grid max-w-7xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-4">
        <div className="md:col-span-2">
          <Logo light />
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-white/70">
            Activity-based carbon accounting with transparent emission factors, machine-learning insights and
            honest, explainable recommendations. Estimates, not exact measurements.
          </p>
        </div>
        <div>
          <h2 className="mb-3 text-sm font-semibold text-white">Product</h2>
          <ul className="space-y-2 text-sm">
            <li><a className="hover:text-algae-light" href="/#features">Features</a></li>
            <li><a className="hover:text-algae-light" href="/#how-it-works">How it works</a></li>
            <li><NavLink className="hover:text-algae-light" to="/register">Create account</NavLink></li>
          </ul>
        </div>
        <div>
          <h2 className="mb-3 text-sm font-semibold text-white">Transparency</h2>
          <ul className="space-y-2 text-sm">
            <li><NavLink className="hover:text-algae-light" to="/methodology">Assumptions &amp; methodology</NavLink></li>
            <li><NavLink className="hover:text-algae-light" to="/methodology#factors">Emission-factor dataset</NavLink></li>
            <li><NavLink className="hover:text-algae-light" to="/methodology#credits">Image credits</NavLink></li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10 py-5 text-center text-xs text-white/50">
        © {YEAR} Carbon Footprint Navigator · MIT licensed
      </div>
    </footer>
  )
}

export function PublicLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2">Skip to content</a>
      <Navbar />
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
