import { useMemo, useState } from 'react'

import { images } from '../assets/images'
import { ErrorState, Skeleton } from '../components/ui/feedback'
import { Badge } from '../components/ui/misc'
import { useFactors } from '../hooks/useFactors'
import { CATEGORY_META, CATEGORY_ORDER } from '../utils/categories'

const SECTIONS = [
  {
    id: 'co2e',
    title: 'CO₂ vs CO₂e',
    body: [
      'Carbon dioxide (CO₂) is one greenhouse gas. CO₂-equivalent (CO₂e) expresses the warming effect of several gases — such as methane from landfill or livestock and nitrous oxide from fertiliser — as the amount of CO₂ that would cause the same warming over 100 years (GWP100).',
      'All figures in Carbon Footprint Navigator are kilograms of CO₂e. Flight factors include an uplift for non-CO₂ effects at altitude (radiative forcing), following UK DESNZ guidance.',
    ],
  },
  {
    id: 'calculation',
    title: 'How a calculation works',
    body: [
      'Every activity is converted to the unit of its emission factor and multiplied: co2e_kg = normalised quantity × factor. The normalised quantity includes conversions (miles → km, therms or m³ → kWh), allocation (a car’s emissions are split between occupants) and multipliers (flight passengers and return legs).',
      'Flight distance is the great-circle distance between airport coordinates plus an 8% routing uplift, banded into domestic (<500 km), short-haul (<3,700 km) and long-haul.',
      'The result is stored with the factor’s ID, value, unit, source, the calculation string and any assumptions, so every number in the app can be traced. A language model is never used for these calculations.',
    ],
  },
  {
    id: 'factors-explained',
    title: 'Emission factors and versioning',
    body: [
      'Factors live in a database table, not in code. Administrators can update a factor, which creates a new version and retires the old one; existing records keep pointing at the version they were calculated with.',
      'Electricity uses country-specific grid intensity where available (location-based); other countries fall back to a global average and the record’s confidence is lowered.',
    ],
  },
  {
    id: 'uncertainty',
    title: 'Estimates, uncertainty and confidence',
    body: [
      'Emission factors are averages. A specific car, flight load factor, farm or supply chain can differ substantially. Each record therefore carries a confidence level (high / medium / low) inherited from its factor and adjusted for fallbacks.',
      'Spend-based purchase factors and product footprints are the least certain; food factors use global means from a meta-analysis and real products vary widely. Treat results as directional estimates for decision-making, not audited measurements.',
    ],
  },
  {
    id: 'geography',
    title: 'Geographic differences',
    body: [
      'Many factors come from UK datasets (DESNZ) and are applied globally where no better open data is bundled. Grid electricity is the main regional factor. The dataset is configurable, so regional factors can be added without code changes.',
    ],
  },
  {
    id: 'ml',
    title: 'Machine learning, recommendations and the assistant',
    body: [
      'Forecasts are chosen by back-testing three simple models on your history and come with an 80% interval from hold-out errors. They assume your recent routine continues and cannot anticipate one-off trips.',
      'Anomalies use robust weekly statistics and an Isolation Forest; both need several weeks of data. Recommendations and scenarios recompute your monthly behaviour with real factors; behavioural assumptions (e.g. 8% heating saving per °C) are stated next to each estimate.',
      'The assistant receives facts computed by the platform and is instructed not to produce new numbers; its answers are scanned and any figure that cannot be matched to those facts is flagged.',
    ],
  },
  {
    id: 'limitations',
    title: 'Limitations',
    body: [
      'Only what you log (or estimate in onboarding) is counted — untracked activities, public services and infrastructure are outside the footprint. Rebound effects and lifecycle emissions of renewables are simplified. Recommendation savings are individually estimated and not strictly additive.',
    ],
  },
]

export default function MethodologyPage() {
  const { data, isLoading, error, refetch } = useFactors()
  const [category, setCategory] = useState('')
  const rows = useMemo(() => (data ?? []).filter((f) => !category || f.category === category), [data, category])
  const sources = useMemo(() => [...new Map((data ?? []).map((f) => [f.source, f.source_url])).entries()], [data])

  return (
    <div className="bg-offwhite pt-24 pb-20">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <p className="eyebrow">Transparency</p>
        <h1 className="mt-2 text-4xl font-extrabold text-forest">Assumptions &amp; methodology</h1>
        <p className="mt-4 max-w-3xl text-lg text-muted">
          How Carbon Footprint Navigator turns activities into CO₂e estimates — and where those estimates are uncertain.
        </p>
        <nav aria-label="On this page" className="mt-8 flex flex-wrap gap-2">
          {[...SECTIONS.map((s) => ({ id: s.id, title: s.title })), { id: 'factors', title: 'Factor dataset' }, { id: 'credits', title: 'Image credits' }].map((s) => (
            <a key={s.id} href={`#${s.id}`} className="rounded-full border border-line bg-white px-3 py-1.5 text-xs font-semibold text-ink hover:bg-mint">{s.title}</a>
          ))}
        </nav>
        <div className="mt-10 space-y-6">
          {SECTIONS.map((s) => (
            <section key={s.id} id={s.id} className="card scroll-mt-24 p-6 sm:p-8">
              <h2 className="text-xl font-bold text-forest">{s.title}</h2>
              {s.body.map((p) => <p key={p.slice(0, 30)} className="mt-3 leading-relaxed text-ink/85">{p}</p>)}
            </section>
          ))}
        </div>

        <section id="factors" className="mt-12 scroll-mt-24">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h2 className="text-2xl font-bold text-forest">Emission-factor dataset</h2>
              <p className="text-sm text-muted">Live from the API — the exact values the calculation engine uses ({data?.length ?? '…'} active factors).</p>
            </div>
            <select aria-label="Filter by category" className="input w-auto" value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">All categories</option>
              {CATEGORY_ORDER.map((c) => <option key={c} value={c}>{CATEGORY_META[c].label}</option>)}
            </select>
          </div>
          {error ? <div className="card"><ErrorState error={error} onRetry={() => refetch()} /></div> : isLoading ? <Skeleton className="h-96" /> : (
            <div className="card overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <caption className="sr-only">Emission factors</caption>
                <thead className="bg-offwhite text-xs text-muted">
                  <tr><th className="px-4 py-3 font-medium">Factor</th><th className="font-medium">Region</th><th className="text-right font-medium">kg CO₂e</th><th className="pl-3 font-medium">per</th><th className="font-medium">Confidence</th><th className="pr-4 font-medium">Source</th></tr>
                </thead>
                <tbody>
                  {rows.map((f) => (
                    <tr key={f.id} className="border-t border-line align-top">
                      <td className="px-4 py-2.5"><p className="font-medium">{f.name}</p><p className="font-mono text-[11px] text-muted">{f.key}</p>{f.notes && <p className="mt-0.5 text-[11px] text-muted">{f.notes}</p>}</td>
                      <td className="py-2.5">{f.region}</td>
                      <td className="py-2.5 text-right font-semibold tabular-nums">{f.co2e_per_unit}</td>
                      <td className="py-2.5 pl-3">{f.unit.replace('_', '-')}</td>
                      <td className="py-2.5"><Badge tone={f.quality === 'high' ? 'green' : f.quality === 'medium' ? 'blue' : 'amber'}>{f.quality}</Badge></td>
                      <td className="py-2.5 pr-4 text-xs text-muted">{f.source_url ? <a href={f.source_url} target="_blank" rel="noreferrer" className="underline">{f.source}</a> : f.source}{f.year ? ` (${f.year})` : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {sources.length > 0 && (
            <div className="mt-6 text-sm">
              <h3 className="font-semibold text-forest">Sources</h3>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
                {sources.map(([src, url]) => <li key={src}>{url ? <a href={url} target="_blank" rel="noreferrer" className="underline">{src}</a> : src}</li>)}
              </ul>
            </div>
          )}
        </section>

        <section id="credits" className="mt-12 scroll-mt-24">
          <h2 className="text-2xl font-bold text-forest">Image credits</h2>
          <p className="text-sm text-muted">All photographs are openly licensed via Wikimedia Commons and used unmodified apart from resizing and compression.</p>
          <ul className="mt-4 grid gap-3 sm:grid-cols-2">
            {Object.values(images).map((img) => (
              <li key={img.src} className="flex gap-3 rounded-xl border border-line bg-white p-3">
                <img src={img.src} alt="" aria-hidden className="h-14 w-20 shrink-0 rounded-lg object-cover" loading="lazy" />
                <p className="text-xs text-muted">
                  <span className="text-ink">{img.alt}</span><br />
                  {img.credit.author} · <a href={img.credit.licenseUrl} target="_blank" rel="noreferrer" className="underline">{img.credit.license}</a> · <a href={img.credit.source} target="_blank" rel="noreferrer" className="underline">source</a>
                </p>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
