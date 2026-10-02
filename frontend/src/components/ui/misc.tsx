import { clsx } from 'clsx'
import { animate, motion, useInView, useMotionValue, useReducedMotion, useTransform } from 'framer-motion'
import { Info, X } from 'lucide-react'
import { useEffect, useId, useRef, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'

import { formatNumber } from '../../utils/format'

export function PageHeader({ eyebrow, title, description, actions }: {
  eyebrow?: string
  title: string
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && <p className="eyebrow mb-1.5">{eyebrow}</p>}
        <h1 className="text-2xl font-bold text-forest sm:text-3xl">{title}</h1>
        {description && <p className="mt-1.5 max-w-2xl text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  )
}

type Tone = 'green' | 'mint' | 'amber' | 'red' | 'gray' | 'blue'
const tones: Record<Tone, string> = {
  green: 'bg-brand/10 text-brand-deep ring-brand/20',
  mint: 'bg-mint text-forest ring-algae-light/50',
  amber: 'bg-amber-50 text-amber-800 ring-amber-200',
  red: 'bg-red-50 text-red-700 ring-red-200',
  gray: 'bg-gray-100 text-gray-700 ring-gray-200',
  blue: 'bg-sky-50 text-sky-800 ring-sky-200',
}

export function Badge({ tone = 'mint', children, className }: { tone?: Tone; children: ReactNode; className?: string }) {
  return (
    <span className={clsx('inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset', tones[tone], className)}>
      {children}
    </span>
  )
}

export function QualityBadge({ quality }: { quality: 'high' | 'medium' | 'low' }) {
  const tone: Tone = quality === 'high' ? 'green' : quality === 'medium' ? 'blue' : 'amber'
  return <Badge tone={tone}>{quality} confidence</Badge>
}

export function ProgressBar({ value, label, tone = 'brand' }: { value: number; label: string; tone?: 'brand' | 'amber' }) {
  const pct = Math.max(0, Math.min(100, value))
  return (
    <div role="progressbar" aria-label={label} aria-valuenow={Math.round(pct)} aria-valuemin={0} aria-valuemax={100}
      className="h-2.5 w-full overflow-hidden rounded-full bg-mint">
      <motion.div
        className={clsx('h-full rounded-full', tone === 'brand' ? 'bg-gradient-to-r from-algae to-brand' : 'bg-amber-400')}
        initial={{ width: 0 }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
      />
    </div>
  )
}

/** Counts up to `value` when scrolled into view (respects reduced-motion). */
export function AnimatedNumber({ value, digits = 0, suffix = '' }: { value: number; digits?: number; suffix?: string }) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true })
  const reduce = useReducedMotion()
  const mv = useMotionValue(0)
  const text = useTransform(mv, (v) => `${formatNumber(v, digits)}${suffix}`)
  useEffect(() => {
    if (!inView) return
    if (reduce) {
      mv.set(value)
      return
    }
    const controls = animate(mv, value, { duration: 1.1, ease: 'easeOut' })
    return () => controls.stop()
  }, [inView, value, mv, reduce])
  return <motion.span ref={ref}>{text}</motion.span>
}

export function InfoTip({ text, className }: { text: string; className?: string }) {
  const id = useId()
  const [open, setOpen] = useState(false)
  return (
    <span className={clsx('relative inline-flex', className)}>
      <button
        type="button"
        aria-describedby={open ? id : undefined}
        aria-label="More information"
        className="text-muted transition hover:text-brand"
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
      >
        <Info className="h-3.5 w-3.5" />
      </button>
      {open && (
        <span id={id} role="tooltip"
          className="absolute bottom-full left-1/2 z-30 mb-2 w-64 -translate-x-1/2 rounded-lg bg-forest px-3 py-2 text-xs leading-relaxed text-white shadow-lg">
          {text}
        </span>
      )}
    </span>
  )
}

export function Segmented<T extends string>({ value, options, onChange, label }: {
  value: T
  options: { value: T; label: string }[]
  onChange: (v: T) => void
  label: string
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap rounded-xl border border-line bg-white p-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={clsx('rounded-lg px-3 py-1.5 text-xs font-semibold transition',
            value === o.value ? 'bg-brand text-white shadow-sm' : 'text-muted hover:bg-mint/70 hover:text-ink')}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export function Modal({ open, onClose, title, children, wide }: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  wide?: boolean
}) {
  const titleId = useId()
  const panelRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!open) return
    const prev = document.activeElement as HTMLElement | null
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    panelRef.current?.focus()
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
      prev?.focus()
    }
  }, [open, onClose])
  if (!open) return null
  return createPortal(
    <div className="fixed inset-0 z-50 flex items-end justify-center p-0 sm:items-center sm:p-4">
      <motion.div className="absolute inset-0 bg-forest/40 backdrop-blur-sm" onClick={onClose}
        initial={{ opacity: 0 }} animate={{ opacity: 1 }} />
      <motion.div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        className={clsx('relative max-h-[92vh] w-full overflow-y-auto rounded-t-2xl bg-white p-6 shadow-2xl sm:rounded-2xl',
          wide ? 'sm:max-w-3xl' : 'sm:max-w-lg')}
      >
        <div className="mb-4 flex items-start justify-between gap-4">
          <h2 id={titleId} className="text-lg font-bold text-forest">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close dialog" className="rounded-lg p-1 text-muted hover:bg-mint hover:text-ink">
            <X className="h-5 w-5" />
          </button>
        </div>
        {children}
      </motion.div>
    </div>,
    document.body,
  )
}

export function Logo({ light = false, compact = false }: { light?: boolean; compact?: boolean }) {
  // Unique per instance: a duplicated gradient id inside a hidden (display:none) copy stops it painting.
  const gradientId = `logo-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
  return (
    <span className="inline-flex items-center gap-2.5">
      <svg viewBox="0 0 64 64" className="h-9 w-9 shrink-0" aria-hidden>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#3FAE72" />
            <stop offset="1" stopColor="#047857" />
          </linearGradient>
        </defs>
        <rect width="64" height="64" rx="16" fill={`url(#${gradientId})`} />
        <path d="M18 42c0-14 10-24 28-24-1 17-10 27-24 27-2 0-3-1-4-3z" fill="#fff" opacity=".95" />
        <path d="M22 44c5-8 11-13 18-17" stroke="#047857" strokeWidth="3" strokeLinecap="round" fill="none" />
      </svg>
      {!compact && (
        <span className={clsx('font-display text-[15px] leading-tight font-extrabold', light ? 'text-white' : 'text-forest')}>
          Carbon Footprint
          <span className={clsx('block text-xs font-semibold tracking-[0.2em] uppercase', light ? 'text-algae-light' : 'text-brand')}>
            Navigator
          </span>
        </span>
      )}
    </span>
  )
}
