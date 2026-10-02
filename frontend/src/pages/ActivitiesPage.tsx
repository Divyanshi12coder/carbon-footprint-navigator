import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronDown, ChevronLeft, ChevronRight, Pencil, Search, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { activityApi, type ActivityQuery } from '../api/endpoints'
import { images } from '../assets/images'
import { ActivityForm } from '../components/activities/ActivityForm'
import { Panel } from '../components/dashboard/cards'
import { Button } from '../components/ui/Button'
import { EmptyState, ErrorState, Skeleton } from '../components/ui/feedback'
import { Badge, Modal, PageHeader, QualityBadge } from '../components/ui/misc'
import { useDebounce } from '../hooks/useDebounce'
import { useInvalidateEmissions } from '../hooks/useInvalidateEmissions'
import type { Activity } from '../types/api'
import { CATEGORY_META, CATEGORY_ORDER, activityLabel } from '../utils/categories'
import { errorMessage, formatDate, formatKg, formatNumber } from '../utils/format'

function detailSummary(a: Activity): string {
  const d = a.details
  if (a.activity_type === 'flight') {
    const route = d.origin && d.destination ? `${d.origin} → ${d.destination}` : `${formatNumber(Number(d.distance_km), 0)} km`
    return `${route} · ${String(d.cabin_class).replace('_', ' ')}${d.round_trip ? ' · return' : ''}${Number(d.passengers) > 1 ? ` · ${d.passengers} pax` : ''}`
  }
  const parts = Object.entries(d)
    .filter(([k]) => !['factor_kg_per_unit', 'factor_source'].includes(k))
    .map(([k, v]) => (k === 'occupants' ? `${v} ${Number(v) === 1 ? 'person' : 'people'}` : String(v).replace(/_/g, ' ')))
  return [`${formatNumber(a.quantity, 2)} ${a.unit.replace('_', ' ')}`, ...parts].join(' · ')
}

function ActivityRow({ a, onEdit, onDelete }: { a: Activity; onEdit: () => void; onDelete: () => void }) {
  const [open, setOpen] = useState(false)
  const meta = CATEGORY_META[a.category]
  return (
    <li className="py-3">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-white" style={{ background: meta.color }} aria-hidden>
          <meta.icon className="h-5 w-5" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-ink">
            {activityLabel(a.activity_type)}
            {a.organization_id && <Badge tone="blue" className="ml-2">Organisation</Badge>}
          </p>
          <p className="truncate text-xs text-muted">{formatDate(a.occurred_on, { day: 'numeric', month: 'short', year: 'numeric' })} · {detailSummary(a)}{a.description ? ` · ${a.description}` : ''}</p>
        </div>
        <p className="text-right font-display text-sm font-bold text-forest tabular-nums">{formatKg(a.emission.co2e_kg, { precise: true })}</p>
        <div className="flex shrink-0 items-center">
          <button type="button" onClick={() => setOpen(!open)} aria-expanded={open} aria-label="Show calculation" className="rounded-lg p-1.5 text-muted hover:bg-mint hover:text-ink">
            <ChevronDown className={`h-4 w-4 transition ${open ? 'rotate-180' : ''}`} />
          </button>
          <button type="button" onClick={onEdit} aria-label="Edit activity" className="rounded-lg p-1.5 text-muted hover:bg-mint hover:text-ink"><Pencil className="h-4 w-4" /></button>
          <button type="button" onClick={onDelete} aria-label="Delete activity" className="rounded-lg p-1.5 text-muted hover:bg-red-50 hover:text-red-600"><Trash2 className="h-4 w-4" /></button>
        </div>
      </div>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }} className="overflow-hidden">
            <div className="mt-3 ml-13 space-y-1.5 rounded-xl bg-offwhite p-3 text-xs">
              <p className="font-mono break-words text-ink">{a.emission.calculation_method}</p>
              <p className="text-muted">Factor <span className="font-semibold text-ink">{a.emission.factor_key}</span> = {a.emission.factor_value} kg CO₂e/{a.emission.factor_unit}</p>
              <p className="text-muted">Source: {a.emission.factor_source}</p>
              <div className="flex flex-wrap gap-2"><QualityBadge quality={a.emission.data_quality} /><Badge tone="gray">source: {a.source}</Badge></div>
              {a.emission.assumptions.map((x) => <p key={x} className="text-muted">• {x}</p>)}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </li>
  )
}

export default function ActivitiesPage() {
  const invalidate = useInvalidateEmissions()
  const [query, setQuery] = useState<ActivityQuery>({ page: 1, page_size: 15, sort: 'occurred_on', order: 'desc' })
  const [search, setSearch] = useState('')
  const debouncedSearch = useDebounce(search, 350)
  const [editing, setEditing] = useState<Activity | null>(null)
  const [deleting, setDeleting] = useState<Activity | null>(null)

  const q = { ...query, search: debouncedSearch || undefined }
  const list = useQuery({ queryKey: ['activities', q], queryFn: () => activityApi.list(q), placeholderData: keepPreviousData })

  const del = useMutation({
    mutationFn: (id: string) => activityApi.remove(id),
    onSuccess: () => {
      toast.success('Activity deleted')
      setDeleting(null)
      invalidate()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })

  const update = (patch: Partial<ActivityQuery>) => setQuery({ ...query, ...patch, page: patch.page ?? 1 })

  return (
    <div>
      <PageHeader eyebrow="Activity tracker" title="Activities"
        description="Each activity is validated, matched to an emission factor and stored with its full calculation trace." />
      <div className="grid gap-6 xl:grid-cols-[minmax(0,440px)_1fr]">
        <div className="space-y-4 xl:sticky xl:top-6 xl:self-start">
          <div className="relative h-28 overflow-hidden rounded-2xl">
            <img src={images.evCharging.src} alt={images.evCharging.alt} className="h-full w-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-r from-forest/85 to-forest/20" aria-hidden />
            <p className="absolute bottom-3 left-4 max-w-xs text-sm font-semibold text-white">Log trips, energy, meals, waste and purchases — the estimate updates as you type.</p>
          </div>
          <Panel title="Add activity">
            <ActivityForm onSaved={(a) => {
              toast.success(`Saved · ${formatKg(a.emission.co2e_kg, { precise: true })} CO₂e`)
              invalidate()
            }} />
          </Panel>
        </div>

        <Panel title="History" subtitle={list.data ? `${list.data.total} activities` : undefined}>
          <div className="mb-4 grid gap-2 sm:grid-cols-[1fr_auto_auto]">
            <div className="relative">
              <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden />
              <label htmlFor="search" className="sr-only">Search activities</label>
              <input id="search" className="input pl-9" placeholder="Search notes or types" value={search} onChange={(e) => setSearch(e.target.value)} />
            </div>
            <label className="sr-only" htmlFor="cat-filter">Category</label>
            <select id="cat-filter" className="input" value={query.category ?? ''} onChange={(e) => update({ category: e.target.value || undefined })}>
              <option value="">All categories</option>
              {CATEGORY_ORDER.map((c) => <option key={c} value={c}>{CATEGORY_META[c].label}</option>)}
            </select>
            <label className="sr-only" htmlFor="sort">Sort</label>
            <select id="sort" className="input" value={`${query.sort}:${query.order}`}
              onChange={(e) => { const [sort, order] = e.target.value.split(':') as [ActivityQuery['sort'], ActivityQuery['order']]; update({ sort, order }) }}>
              <option value="occurred_on:desc">Newest first</option>
              <option value="occurred_on:asc">Oldest first</option>
              <option value="co2e_kg:desc">Highest CO₂e</option>
              <option value="co2e_kg:asc">Lowest CO₂e</option>
            </select>
            <div className="flex gap-2 sm:col-span-3">
              <label className="sr-only" htmlFor="from">From</label>
              <input id="from" type="date" className="input" value={query.date_from ?? ''} onChange={(e) => update({ date_from: e.target.value || undefined })} />
              <label className="sr-only" htmlFor="to">To</label>
              <input id="to" type="date" className="input" value={query.date_to ?? ''} onChange={(e) => update({ date_to: e.target.value || undefined })} />
              <select aria-label="Scope" className="input" value={query.scope ?? 'personal'} onChange={(e) => update({ scope: e.target.value as ActivityQuery['scope'] })}>
                <option value="personal">Personal</option>
                <option value="organization">Organisation</option>
                <option value="all">All</option>
              </select>
            </div>
          </div>

          {list.error ? <ErrorState error={list.error} onRetry={() => list.refetch()} /> : list.isLoading ? (
            <div className="space-y-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-12" />)}</div>
          ) : list.data && list.data.items.length === 0 ? (
            <EmptyState title="No activities found" body={query.category || debouncedSearch || query.date_from ? 'Try clearing the filters.' : 'Use the form to log your first activity.'} />
          ) : (
            <>
              <ul className={`divide-y divide-line transition ${list.isPlaceholderData ? 'opacity-60' : ''}`}>
                {list.data?.items.map((a) => <ActivityRow key={a.id} a={a} onEdit={() => setEditing(a)} onDelete={() => setDeleting(a)} />)}
              </ul>
              {list.data && list.data.pages > 1 && (
                <nav className="mt-4 flex items-center justify-between" aria-label="Pagination">
                  <Button variant="secondary" size="sm" disabled={query.page === 1} onClick={() => setQuery({ ...query, page: (query.page ?? 1) - 1 })} icon={<ChevronLeft className="h-4 w-4" />}>Prev</Button>
                  <span className="text-sm text-muted">Page {list.data.page} of {list.data.pages}</span>
                  <Button variant="secondary" size="sm" disabled={query.page === list.data.pages} onClick={() => setQuery({ ...query, page: (query.page ?? 1) + 1 })}>
                    Next <ChevronRight className="h-4 w-4" />
                  </Button>
                </nav>
              )}
            </>
          )}
        </Panel>
      </div>

      <Modal open={editing !== null} onClose={() => setEditing(null)} title="Edit activity" wide>
        {editing && (
          <ActivityForm initial={editing} submitLabel="Update activity" onSaved={(a) => {
            toast.success(`Updated · ${formatKg(a.emission.co2e_kg, { precise: true })} CO₂e`)
            setEditing(null)
            invalidate()
          }} />
        )}
      </Modal>
      <Modal open={deleting !== null} onClose={() => setDeleting(null)} title="Delete this activity?">
        <p className="text-sm text-muted">
          {deleting && `${activityLabel(deleting.activity_type)} on ${formatDate(deleting.occurred_on)} (${formatKg(deleting.emission.co2e_kg, { precise: true })} CO₂e)`} will be removed
          and your analytics recalculated. This can’t be undone.
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="secondary" onClick={() => setDeleting(null)}>Cancel</Button>
          <Button variant="danger" loading={del.isPending} onClick={() => deleting && del.mutate(deleting.id)} icon={<Trash2 className="h-4 w-4" />}>Delete</Button>
        </div>
      </Modal>
    </div>
  )
}
