import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, Info, RefreshCw, Sparkles } from 'lucide-react'
import { toast } from 'sonner'

import { fadeUp, stagger } from '../animations/variants'
import { mlApi } from '../api/endpoints'
import { Button } from '../components/ui/Button'
import { CardSkeleton, EmptyState, ErrorState } from '../components/ui/feedback'
import { Badge, PageHeader } from '../components/ui/misc'
import type { Insight } from '../types/api'
import { categoryLabel } from '../utils/categories'
import { errorMessage, formatDate } from '../utils/format'

const SEVERITY = {
  positive: { icon: CheckCircle2, ring: 'border-brand/30 bg-brand/5', iconCls: 'text-brand', tone: 'green' as const, label: 'Positive' },
  info: { icon: Info, ring: 'border-sky-200 bg-sky-50/50', iconCls: 'text-sky-700', tone: 'blue' as const, label: 'Info' },
  warning: { icon: AlertTriangle, ring: 'border-amber-200 bg-amber-50/60', iconCls: 'text-amber-700', tone: 'amber' as const, label: 'Attention' },
}

const TYPE_LABELS: Record<string, string> = {
  largest_source: 'Largest source',
  period_change: 'Month over month',
  biggest_increase: 'Biggest increase',
  biggest_improvement: 'Biggest improvement',
  anomaly: 'Anomaly',
  opportunity: 'Opportunity',
  forecast: 'Forecast',
  goal_progress: 'Goal progress',
  data_quality: 'Data quality',
  benchmark: 'Benchmark',
}

export default function InsightsPage() {
  const qc = useQueryClient()
  const insights = useQuery({ queryKey: ['insights'], queryFn: mlApi.insights })
  const refresh = useMutation({
    mutationFn: mlApi.refreshInsights,
    onSuccess: (data) => {
      qc.setQueryData<Insight[]>(['insights'], data)
      toast.success('Insights regenerated from your latest data')
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  return (
    <div>
      <PageHeader eyebrow="Insight engine" title="Insights"
        description="Short statements computed from your records, the anomaly detector, the forecast model, recommendations and goals. Regenerated automatically after every change."
        actions={<Button variant="secondary" loading={refresh.isPending} onClick={() => refresh.mutate()} icon={<RefreshCw className="h-4 w-4" />}>Regenerate</Button>} />
      {insights.error ? <div className="card"><ErrorState error={insights.error} onRetry={() => insights.refetch()} /></div> : insights.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">{Array.from({ length: 4 }).map((_, i) => <CardSkeleton key={i} />)}</div>
      ) : (insights.data ?? []).length === 0 ? (
        <div className="card"><EmptyState icon={<Sparkles className="h-6 w-6" />} title="No insights yet" body="Log a few activities — insights appear as soon as there is data to analyse." /></div>
      ) : (
        <motion.div className="grid gap-4 md:grid-cols-2" variants={stagger} initial="hidden" animate="show">
          {insights.data!.map((i) => {
            const s = SEVERITY[i.severity]
            return (
              <motion.article key={i.id} variants={fadeUp} className={`card card-hover border p-5 ${s.ring}`}>
                <div className="flex items-start gap-3">
                  <s.icon className={`mt-0.5 h-5 w-5 shrink-0 ${s.iconCls}`} aria-hidden />
                  <div className="min-w-0">
                    <div className="mb-1.5 flex flex-wrap gap-1.5">
                      <Badge tone={s.tone}>{s.label}</Badge>
                      <Badge tone="gray">{TYPE_LABELS[i.insight_type] ?? i.insight_type}</Badge>
                      {i.category && <Badge tone="mint">{categoryLabel(i.category)}</Badge>}
                    </div>
                    <h2 className="font-semibold text-forest">{i.title}</h2>
                    <p className="mt-1 text-sm text-muted">{i.body}</p>
                    <p className="mt-2 text-[11px] text-muted/80">Generated {formatDate(i.generated_at, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</p>
                  </div>
                </div>
              </motion.article>
            )
          })}
        </motion.div>
      )}
    </div>
  )
}
