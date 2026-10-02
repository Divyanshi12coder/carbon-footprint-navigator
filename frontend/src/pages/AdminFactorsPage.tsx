import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { History, Pencil } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { toast } from 'sonner'

import { factorApi } from '../api/endpoints'
import { Button } from '../components/ui/Button'
import { CardSkeleton, ErrorState } from '../components/ui/feedback'
import { Badge, Modal, PageHeader } from '../components/ui/misc'
import type { EmissionFactor, Quality } from '../types/api'
import { CATEGORY_META, CATEGORY_ORDER } from '../utils/categories'
import { errorMessage, formatDate } from '../utils/format'

function EditFactor({ factor, onDone }: { factor: EmissionFactor; onDone: () => void }) {
  const qc = useQueryClient()
  const [value, setValue] = useState(String(factor.co2e_per_unit))
  const [source, setSource] = useState(factor.source)
  const [quality, setQuality] = useState<Quality>(factor.quality)
  const [reason, setReason] = useState('')
  const history = useQuery({ queryKey: ['factor-history', factor.id], queryFn: () => factorApi.history(factor.id) })
  const save = useMutation({
    mutationFn: () => factorApi.update(factor.id, { co2e_per_unit: Number(value), source, quality, change_reason: reason }),
    onSuccess: (f) => {
      qc.invalidateQueries({ queryKey: ['factors'] })
      toast.success(`Saved as version ${f.version}. Existing records keep version ${factor.version}.`)
      onDone()
    },
    onError: (e) => toast.error(errorMessage(e)),
  })
  const invalid = value === '' || Number(value) < 0 || Number.isNaN(Number(value)) || reason.trim().length < 3 || source.trim().length < 3
  return (
    <form className="space-y-4" onSubmit={(e: FormEvent) => { e.preventDefault(); if (!invalid) save.mutate() }}>
      <p className="text-sm text-muted"><span className="font-mono text-ink">{factor.key}</span> · {factor.region} · per {factor.unit}</p>
      <div className="grid gap-4 sm:grid-cols-2">
        <div><label htmlFor="fv" className="label">kg CO₂e per {factor.unit}</label><input id="fv" type="number" step="any" min={0} className="input" value={value} onChange={(e) => setValue(e.target.value)} /></div>
        <div><label htmlFor="fq" className="label">Quality</label>
          <select id="fq" className="input" value={quality} onChange={(e) => setQuality(e.target.value as Quality)}><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option></select></div>
      </div>
      <div><label htmlFor="fs" className="label">Source</label><input id="fs" className="input" maxLength={300} value={source} onChange={(e) => setSource(e.target.value)} /></div>
      <div><label htmlFor="fr" className="label">Reason for change (audit log)</label><input id="fr" className="input" maxLength={300} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="e.g. Updated to 2025 dataset" /></div>
      <Button type="submit" loading={save.isPending} disabled={invalid}>Save new version</Button>
      <div>
        <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-forest"><History className="h-4 w-4" /> Version history</h3>
        <ul className="space-y-1 text-xs">
          {(history.data ?? []).map((h) => (
            <li key={h.id} className="flex justify-between gap-2 rounded-lg bg-offwhite px-3 py-2">
              <span>v{h.version} · {h.co2e_per_unit} · {h.change_reason ?? '—'}</span>
              <span className="text-muted">{h.is_active ? 'active' : 'retired'} · {formatDate(h.updated_at)}</span>
            </li>
          ))}
        </ul>
      </div>
    </form>
  )
}

export default function AdminFactorsPage() {
  const [category, setCategory] = useState('')
  const [editing, setEditing] = useState<EmissionFactor | null>(null)
  const factors = useQuery({ queryKey: ['factors', 'admin', category], queryFn: () => factorApi.list({ category: category || undefined, include_inactive: true }) })
  return (
    <div>
      <PageHeader eyebrow="Administration" title="Emission factors"
        description="Updates never overwrite: each edit creates a new version and retires the old one, so every stored record stays traceable to the exact factor used."
        actions={<select aria-label="Category" className="input w-auto" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>{CATEGORY_ORDER.map((c) => <option key={c} value={c}>{CATEGORY_META[c].label}</option>)}</select>} />
      {factors.error ? <div className="card"><ErrorState error={factors.error} onRetry={() => factors.refetch()} /></div> : factors.isLoading ? <CardSkeleton rows={10} /> : (
        <div className="card overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-offwhite text-xs text-muted"><tr><th className="px-4 py-3 font-medium">Key</th><th className="font-medium">Region</th><th className="font-medium">Value</th><th className="font-medium">Version</th><th className="font-medium">Status</th><th /></tr></thead>
            <tbody>
              {factors.data!.map((f) => (
                <tr key={f.id} className="border-t border-line">
                  <td className="px-4 py-2.5"><p className="font-medium">{f.name}</p><p className="font-mono text-xs text-muted">{f.key}</p></td>
                  <td>{f.region}</td>
                  <td className="tabular-nums">{f.co2e_per_unit} / {f.unit}</td>
                  <td>v{f.version}</td>
                  <td><Badge tone={f.is_active ? 'green' : 'gray'}>{f.is_active ? 'active' : 'retired'}</Badge></td>
                  <td className="pr-4 text-right">{f.is_active && <Button size="sm" variant="ghost" onClick={() => setEditing(f)} icon={<Pencil className="h-4 w-4" />}>Edit</Button>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Modal open={editing !== null} onClose={() => setEditing(null)} title={editing ? `Edit: ${editing.name}` : ''} wide>
        {editing && <EditFactor factor={editing} onDone={() => setEditing(null)} />}
      </Modal>
    </div>
  )
}
