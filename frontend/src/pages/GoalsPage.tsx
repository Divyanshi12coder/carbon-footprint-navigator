import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { Archive, Award, Lock, Plus, Target, Trash2, Trophy } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { fadeUp, stagger } from '../animations/variants'
import { goalApi } from '../api/endpoints'
import { Panel } from '../components/dashboard/cards'
import { Button } from '../components/ui/Button'
import { CardSkeleton, EmptyState, ErrorState } from '../components/ui/feedback'
import { Badge, InfoTip, Modal, PageHeader, ProgressBar } from '../components/ui/misc'
import type { Category, Goal, GoalInput } from '../types/api'
import { CATEGORY_META, CATEGORY_ORDER, categoryLabel } from '../utils/categories'
import { addDaysIso, errorMessage, formatDate, formatKg, formatPct, todayIso } from '../utils/format'

function GoalForm({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient()
  const [form, setForm] = useState({ title: 'Reduce monthly emissions by 20%', category: '' as Category | '', pct: 20, baseline: '', deadline: addDaysIso(90) })
  const create = useMutation({
    mutationFn: (body: GoalInput) => goalApi.create(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['goals'] })
      qc.invalidateQueries({ queryKey: ['achievements'] })
      toast.success('Goal created')
      onDone()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })
  const invalid = !form.title.trim() || form.pct <= 0 || form.pct > 100 || form.deadline <= todayIso()
  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (invalid) return
    create.mutate({
      title: form.title.trim(),
      category: form.category || null,
      target_reduction_pct: form.pct,
      baseline_monthly_kg: form.baseline === '' ? null : Number(form.baseline),
      deadline: form.deadline,
    })
  }
  return (
    <form onSubmit={submit} className="space-y-4" noValidate>
      <div>
        <label htmlFor="g-title" className="label">Goal name</label>
        <input id="g-title" className="input" maxLength={160} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="g-cat" className="label">Scope</label>
          <select id="g-cat" className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value as Category | '' })}>
            <option value="">All categories</option>
            {CATEGORY_ORDER.map((c) => <option key={c} value={c}>{CATEGORY_META[c].label}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="g-pct" className="label">Reduction target: {form.pct}%</label>
          <input id="g-pct" type="range" className="slider mt-3 w-full" min={5} max={100} step={5} value={form.pct} onChange={(e) => setForm({ ...form, pct: Number(e.target.value) })} />
        </div>
        <div>
          <label htmlFor="g-base" className="label">Baseline (kg CO₂e / month)</label>
          <input id="g-base" type="number" min={0} className="input" placeholder="Auto: last 30 days" value={form.baseline} onChange={(e) => setForm({ ...form, baseline: e.target.value })} />
          <p className="mt-1 text-xs text-muted">Leave blank to use your tracked last 30 days.</p>
        </div>
        <div>
          <label htmlFor="g-deadline" className="label">Deadline</label>
          <input id="g-deadline" type="date" className="input" min={addDaysIso(1)} value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })} />
        </div>
      </div>
      <Button type="submit" className="w-full" loading={create.isPending} disabled={invalid} icon={<Target className="h-4 w-4" />}>Create goal</Button>
    </form>
  )
}

function GoalCard({ goal }: { goal: Goal }) {
  const qc = useQueryClient()
  const refresh = () => qc.invalidateQueries({ queryKey: ['goals'] })
  const archive = useMutation({ mutationFn: () => goalApi.update(goal.id, { status: 'archived' }), onSuccess: refresh, onError: (e) => toast.error(errorMessage(e)) })
  const remove = useMutation({ mutationFn: () => goalApi.remove(goal.id), onSuccess: () => { refresh(); toast.success('Goal deleted') }, onError: (e) => toast.error(errorMessage(e)) })
  const p = goal.progress
  const tone = goal.status === 'achieved' ? 'green' : goal.status === 'missed' ? 'red' : goal.status === 'archived' ? 'gray' : p.on_track ? 'green' : 'amber'
  return (
    <motion.article variants={fadeUp} className="card card-hover p-5">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="font-semibold text-forest">{goal.title}</h2>
          <p className="text-xs text-muted">{categoryLabel(goal.category)} · −{goal.target_reduction_pct}% by {formatDate(goal.deadline, { day: 'numeric', month: 'short', year: 'numeric' })}</p>
        </div>
        <Badge tone={tone}>{goal.status === 'active' ? (p.on_track ? 'On track' : 'In progress') : goal.status}</Badge>
      </div>
      <div className="mt-4"><ProgressBar value={p.progress_pct} label={`${goal.title} progress`} /></div>
      <dl className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded-lg bg-offwhite p-2"><dt className="text-muted">Baseline</dt><dd className="font-semibold">{formatKg(goal.baseline_monthly_kg)}</dd></div>
        <div className="rounded-lg bg-offwhite p-2"><dt className="text-muted">Current</dt><dd className="font-semibold">{formatKg(p.current_monthly_kg)}</dd></div>
        <div className="rounded-lg bg-mint/60 p-2"><dt className="text-muted">Target</dt><dd className="font-semibold">{formatKg(p.target_monthly_kg)}</dd></div>
      </dl>
      <p className="mt-3 flex items-center gap-1 text-xs text-muted">
        {formatPct(p.progress_pct)} of the way · reduction so far {formatPct(p.reduction_achieved_pct, true)} · {p.days_remaining >= 0 ? `${p.days_remaining} days left` : 'deadline passed'}
        <InfoTip text={`Per month. ${p.measurement}`} />
      </p>
      <div className="mt-4 flex gap-2 border-t border-line pt-3">
        {goal.status === 'active' && <Button size="sm" variant="ghost" loading={archive.isPending} onClick={() => archive.mutate()} icon={<Archive className="h-4 w-4" />}>Archive</Button>}
        <Button size="sm" variant="ghost" loading={remove.isPending} onClick={() => remove.mutate()} icon={<Trash2 className="h-4 w-4" />}>Delete</Button>
      </div>
    </motion.article>
  )
}

export default function GoalsPage() {
  const [creating, setCreating] = useState(false)
  const goals = useQuery({ queryKey: ['goals'], queryFn: goalApi.list })
  const achievements = useQuery({ queryKey: ['achievements'], queryFn: goalApi.achievements })

  return (
    <div>
      <PageHeader eyebrow="Goals" title="Reduction goals" description="Targets are measured against a monthly baseline using your tracked emissions."
        actions={<Button onClick={() => setCreating(true)} icon={<Plus className="h-4 w-4" />}>New goal</Button>} />
      {goals.error ? <div className="card"><ErrorState error={goals.error} onRetry={() => goals.refetch()} /></div> : goals.isLoading ? (
        <div className="grid gap-4 md:grid-cols-2"><CardSkeleton rows={4} /><CardSkeleton rows={4} /></div>
      ) : (goals.data ?? []).length === 0 ? (
        <div className="card"><EmptyState icon={<Target className="h-6 w-6" />} title="No goals yet" body="Set a reduction target to track progress month by month."
          action={<Button onClick={() => setCreating(true)} icon={<Plus className="h-4 w-4" />}>Create your first goal</Button>} /></div>
      ) : (
        <motion.div className="grid gap-4 md:grid-cols-2" variants={stagger} initial="hidden" animate="show">
          {goals.data!.map((g) => <GoalCard key={g.id} goal={g} />)}
        </motion.div>
      )}

      <Panel className="mt-8" title="Achievements" subtitle="Awarded automatically from your data">
        {achievements.isLoading ? <CardSkeleton rows={2} /> : achievements.error ? <ErrorState error={achievements.error} /> : (
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {achievements.data!.map((a) => (
              <li key={a.code} className={`rounded-xl border p-4 ${a.achieved ? 'border-algae-light bg-mint/50' : 'border-line bg-offwhite opacity-70'}`}>
                <div className="flex items-center gap-2">
                  {a.achieved ? <Trophy className="h-5 w-5 text-brand" aria-hidden /> : <Lock className="h-5 w-5 text-muted" aria-hidden />}
                  <p className="font-semibold text-forest">{a.title}</p>
                </div>
                <p className="mt-1 text-xs text-muted">{a.description}</p>
                {a.achieved_at && <p className="mt-1 flex items-center gap-1 text-[11px] font-medium text-brand-deep"><Award className="h-3 w-3" />{formatDate(a.achieved_at)}</p>}
                <span className="sr-only">{a.achieved ? 'Achieved' : 'Locked'}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Modal open={creating} onClose={() => setCreating(false)} title="New reduction goal">
        <GoalForm onDone={() => setCreating(false)} />
      </Modal>
    </div>
  )
}
