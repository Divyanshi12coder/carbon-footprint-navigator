import { clsx } from 'clsx'
import { motion } from 'framer-motion'
import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import type { ReactNode } from 'react'

import { fadeUp } from '../../animations/variants'
import type { Category, CategoryRow } from '../../types/api'
import { CATEGORY_META } from '../../utils/categories'
import { formatKg, formatPct } from '../../utils/format'
import { AnimatedNumber, InfoTip } from '../ui/misc'

/** Change badge: for emissions, down is good (green) and up is bad (amber). Icon + sign, never colour alone. */
export function ChangeBadge({ pct, suffix = 'vs previous period' }: { pct: number | null; suffix?: string }) {
  if (pct === null) return <span className="text-xs text-muted">No previous data</span>
  const up = pct > 0.05
  const down = pct < -0.05
  const Icon = up ? ArrowUpRight : down ? ArrowDownRight : Minus
  return (
    <span className="inline-flex items-center gap-1 text-xs">
      <span className={clsx('inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 font-semibold',
        up ? 'bg-amber-50 text-amber-800' : down ? 'bg-brand/10 text-brand-deep' : 'bg-gray-100 text-gray-600')}>
        <Icon className="h-3.5 w-3.5" aria-hidden />
        {formatPct(pct, true)}
      </span>
      <span className="text-muted">{suffix}</span>
    </span>
  )
}

export function KpiCard({ label, kg, hint, footer, icon, highlight }: {
  label: string
  kg: number
  hint?: string
  footer?: ReactNode
  icon?: ReactNode
  highlight?: boolean
}) {
  const tonnes = Math.abs(kg) >= 1000
  return (
    <motion.div variants={fadeUp} className={clsx('card card-hover p-5', highlight && 'bg-gradient-to-br from-brand to-brand-deep text-white')}>
      <div className="flex items-center justify-between gap-2">
        <p className={clsx('flex items-center gap-1.5 text-sm font-medium', highlight ? 'text-white/85' : 'text-muted')}>
          {label} {hint && <InfoTip text={hint} />}
        </p>
        {icon}
      </div>
      <p className={clsx('mt-2 font-display text-3xl font-extrabold tabular-nums', highlight ? 'text-white' : 'text-forest')}>
        <AnimatedNumber value={tonnes ? kg / 1000 : kg} digits={tonnes ? 2 : kg < 100 ? 1 : 0} />
        <span className={clsx('ml-1 text-base font-semibold', highlight ? 'text-white/80' : 'text-muted')}>{tonnes ? 't' : 'kg'} CO₂e</span>
      </p>
      {footer && <div className="mt-2">{footer}</div>}
    </motion.div>
  )
}

export function CategoryTile({ category, row }: { category: Category; row?: CategoryRow }) {
  const meta = CATEGORY_META[category]
  return (
    <motion.div variants={fadeUp} className="card card-hover flex items-center gap-3 p-4">
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-white" style={{ background: meta.color }}>
        <meta.icon className="h-5 w-5" aria-hidden />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-muted">{meta.label}</p>
        <p className="font-display text-lg font-bold text-forest tabular-nums">{formatKg(row?.kg ?? 0)}</p>
      </div>
      <div className="text-right text-xs">
        <p className="font-semibold text-ink">{formatPct(row?.share_pct ?? 0)}</p>
        {row?.change_pct !== null && row?.change_pct !== undefined && (
          <p className={row.change_pct > 0 ? 'text-amber-700' : 'text-brand-deep'}>{formatPct(row.change_pct, true)}</p>
        )}
      </div>
    </motion.div>
  )
}

export function Panel({ title, subtitle, actions, children, className }: {
  title: string
  subtitle?: ReactNode
  actions?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section className={clsx('card p-5 sm:p-6', className)} aria-label={title}>
      <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-forest">{title}</h2>
          {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
        </div>
        {actions}
      </div>
      {children}
    </section>
  )
}
