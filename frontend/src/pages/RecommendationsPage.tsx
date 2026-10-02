import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Check, ChevronDown, Lightbulb, RefreshCw, ThumbsUp, X } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { fadeUp, stagger } from '../animations/variants'
import { mlApi } from '../api/endpoints'
import { images } from '../assets/images'
import { Button } from '../components/ui/Button'
import { CardSkeleton, EmptyState, ErrorState } from '../components/ui/feedback'
import { Badge, PageHeader, Segmented } from '../components/ui/misc'
import type { Recommendation, RecommendationStatus } from '../types/api'
import { CATEGORY_META } from '../utils/categories'
import { errorMessage, formatKg, formatPct } from '../utils/format'

const DIFFICULTY_TONE = { easy: 'green', medium: 'amber', hard: 'red' } as const

function RecommendationCard({ rec, onStatus, busy }: { rec: Recommendation; onStatus: (s: RecommendationStatus) => void; busy: boolean }) {
  const [open, setOpen] = useState(false)
  const meta = CATEGORY_META[rec.category]
  return (
    <motion.article variants={fadeUp} className={`card card-hover flex flex-col p-5 ${rec.status === 'dismissed' ? 'opacity-60' : ''}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl text-white" style={{ background: meta.color }} aria-hidden><meta.icon className="h-5 w-5" /></div>
          <div>
            <h2 className="font-semibold text-forest">{rec.title}</h2>
            <div className="mt-1 flex flex-wrap gap-1.5">
              <Badge tone={DIFFICULTY_TONE[rec.difficulty]}>{rec.difficulty}</Badge>
              <Badge tone="gray">{meta.label}</Badge>
              {rec.status !== 'open' && <Badge tone="blue">{rec.status}</Badge>}
            </div>
          </div>
        </div>
        <div className="text-right">
          <p className="font-display text-xl font-extrabold text-brand">−{formatKg(rec.estimated_monthly_reduction_kg)}</p>
          <p className="text-[11px] text-muted">per month · {formatPct(rec.share_of_footprint_pct)} of footprint</p>
        </div>
      </div>
      <p className="mt-3 text-sm text-muted">{rec.reason}</p>
      <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
        <div className="rounded-xl bg-offwhite p-3"><dt className="text-xs font-medium text-muted">Current behaviour</dt><dd className="mt-0.5 text-ink">{rec.current_behavior}</dd></div>
        <div className="rounded-xl bg-mint/60 p-3"><dt className="text-xs font-medium text-muted">Suggested action</dt><dd className="mt-0.5 text-ink">{rec.suggested_action}</dd></div>
      </dl>
      <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} className="mt-3 inline-flex items-center gap-1 self-start text-xs font-semibold text-brand">
        Calculation basis <ChevronDown className={`h-3.5 w-3.5 transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && (
        <div className="mt-2 rounded-xl bg-offwhite p-3 text-xs">
          <p className="font-mono break-words text-ink">{rec.calculation_basis}</p>
          <p className="mt-1.5 text-muted">Based on {rec.data_basis === 'tracked_activities' ? 'your tracked activities' : 'your onboarding answers (log activities for a sharper estimate)'}. Annual: ≈ {formatKg(rec.estimated_monthly_reduction_kg * 12)}.</p>
        </div>
      )}
      <div className="mt-4 flex flex-wrap gap-2 border-t border-line pt-4">
        {rec.status !== 'accepted' && <Button size="sm" variant="secondary" disabled={busy} onClick={() => onStatus('accepted')} icon={<ThumbsUp className="h-4 w-4" />}>I’ll try this</Button>}
        {rec.status !== 'completed' && <Button size="sm" variant="secondary" disabled={busy} onClick={() => onStatus('completed')} icon={<Check className="h-4 w-4" />}>Done</Button>}
        {rec.status !== 'dismissed' ? (
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus('dismissed')} icon={<X className="h-4 w-4" />}>Dismiss</Button>
        ) : (
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus('open')}>Restore</Button>
        )}
      </div>
    </motion.article>
  )
}

export default function RecommendationsPage() {
  const qc = useQueryClient()
  const [view, setView] = useState<'active' | 'all'>('active')
  const recs = useQuery({ queryKey: ['recommendations', view], queryFn: () => mlApi.recommendations(view === 'all') })
  const refresh = useMutation({
    mutationFn: mlApi.refreshRecommendations,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['recommendations'] })
      toast.success('Recommendations recalculated')
    },
    onError: (e) => toast.error(errorMessage(e)),
  })
  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: string; status: RecommendationStatus }) => mlApi.setRecommendationStatus(id, status),
    onSuccess: (r) => {
      qc.invalidateQueries({ queryKey: ['recommendations'] })
      qc.invalidateQueries({ queryKey: ['insights'] })
      toast.success(`Marked as ${r.status}`)
    },
    onError: (e) => toast.error(errorMessage(e)),
  })
  const totalSaving = (recs.data ?? []).filter((r) => r.status !== 'dismissed').slice(0, 3).reduce((s, r) => s + r.estimated_monthly_reduction_kg, 0)

  return (
    <div>
      <PageHeader eyebrow="Recommendation engine" title="Recommendations"
        description="Each suggestion is generated from your own behaviour and priced with the same emission factors as your activities. Savings shown separately are not strictly additive."
        actions={<>
          <Segmented label="Show" value={view} onChange={setView} options={[{ value: 'active', label: 'Active' }, { value: 'all', label: 'Include dismissed' }]} />
          <Button variant="secondary" loading={refresh.isPending} onClick={() => refresh.mutate()} icon={<RefreshCw className="h-4 w-4" />}>Recalculate</Button>
        </>} />
      <div className="relative mb-6 overflow-hidden rounded-2xl">
        <img src={images.food.src} alt={images.food.alt} className="h-36 w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-r from-forest/90 to-forest/20" aria-hidden />
        <div className="absolute inset-y-0 left-6 flex flex-col justify-center text-white">
          <p className="text-sm text-white/80">Top 3 opportunities combined (approx.)</p>
          <p className="font-display text-3xl font-extrabold">{recs.isLoading ? '…' : `−${formatKg(totalSaving)} / month`}</p>
        </div>
      </div>
      {recs.error ? <div className="card"><ErrorState error={recs.error} onRetry={() => recs.refetch()} /></div> : recs.isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">{Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} rows={5} />)}</div>
      ) : (recs.data ?? []).length === 0 ? (
        <div className="card"><EmptyState icon={<Lightbulb className="h-6 w-6" />} title="No recommendations yet"
          body="Recommendations need either onboarding answers or a couple of weeks of logged activities so savings can be calculated from your behaviour." /></div>
      ) : (
        <motion.div className="grid gap-4 lg:grid-cols-2" variants={stagger} initial="hidden" animate="show">
          {recs.data!.map((r) => (
            <RecommendationCard key={r.id} rec={r} busy={setStatus.isPending} onStatus={(status) => setStatus.mutate({ id: r.id, status })} />
          ))}
        </motion.div>
      )}
    </div>
  )
}
