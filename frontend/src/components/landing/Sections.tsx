import { motion } from 'framer-motion'
import {
  Activity,
  ArrowRight,
  BrainCircuit,
  Building2,
  Calculator,
  ChevronLeft,
  ChevronRight,
  FlaskConical,
  Gauge,
  LineChart,
  ListChecks,
  MessageSquareText,
  Radar,
  Sparkles,
  Target,
  TrendingDown,
} from 'lucide-react'
import { useRef } from 'react'

import { fadeUp, stagger } from '../../animations/variants'
import { images, type SiteImage } from '../../assets/images'
import { useFactors } from '../../hooks/useFactors'
import { ButtonLink } from '../ui/Button'

function Section({ id, eyebrow, title, intro, children, className = '' }: {
  id?: string
  eyebrow: string
  title: string
  intro?: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <section id={id} className={`scroll-mt-20 py-20 sm:py-24 ${className}`}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6">
        <motion.div className="mb-12 max-w-2xl" variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true, margin: '-80px' }}>
          <p className="eyebrow">{eyebrow}</p>
          <h2 className="mt-2 text-3xl font-extrabold text-forest sm:text-4xl">{title}</h2>
          {intro && <p className="mt-4 text-lg text-muted">{intro}</p>}
        </motion.div>
        {children}
      </div>
    </section>
  )
}

export function TechStrip() {
  const items = ['Activity-based carbon accounting', 'Sourced emission factors', 'Predictive analytics', 'Anomaly detection',
    'Personalised recommendations', 'What-if scenarios', 'Data-grounded AI assistant', 'Organisation mode']
  return (
    <div className="border-y border-line bg-white py-5" aria-label="Capabilities">
      <div className="relative overflow-hidden [mask-image:linear-gradient(90deg,transparent,black_10%,black_90%,transparent)]">
        <motion.ul className="flex w-max gap-10 pr-10" animate={{ x: ['0%', '-50%'] }} transition={{ duration: 36, repeat: Infinity, ease: 'linear' }}>
          {[...items, ...items].map((t, i) => (
            <li key={i} className="flex items-center gap-2 text-sm font-semibold whitespace-nowrap text-muted" aria-hidden={i >= items.length}>
              <Sparkles className="h-4 w-4 text-algae" aria-hidden /> {t}
            </li>
          ))}
        </motion.ul>
      </div>
    </div>
  )
}

const STEPS: { title: string; body: string; icon: typeof Activity; image: SiteImage }[] = [
  { title: 'Track activities', body: 'Log trips, flights, meter readings, meals, waste and purchases in seconds — with a live CO₂e preview before you save.', icon: ListChecks, image: images.tram },
  { title: 'Calculate emissions', body: 'A deterministic engine multiplies each quantity by a sourced, versioned emission factor. Every number shows its formula.', icon: Calculator, image: images.solar },
  { title: 'Analyse patterns', body: 'Trends, category shares, rolling averages, anomaly detection and forecasts reveal what drives your footprint.', icon: LineChart, image: images.wind },
  { title: 'Reduce impact', body: 'Explainable recommendations and a scenario simulator quantify each change before you make it, then goals track progress.', icon: TrendingDown, image: images.forest },
]

export function HowItWorks() {
  return (
    <Section id="how-it-works" eyebrow="How it works" title="Measure → Understand → Reduce → Improve"
      intro="Four steps, each backed by real calculations rather than guesses.">
      <motion.ol className="grid gap-6 md:grid-cols-2 lg:grid-cols-4" variants={stagger} initial="hidden" whileInView="show" viewport={{ once: true }}>
        {STEPS.map((s, i) => (
          <motion.li key={s.title} variants={fadeUp} className="card card-hover group overflow-hidden">
            <div className="relative h-40 overflow-hidden">
              <img src={s.image.src} alt={s.image.alt} loading="lazy" className="h-full w-full object-cover transition duration-700 group-hover:scale-105" />
              <div className="absolute inset-0 bg-gradient-to-t from-forest/60 to-transparent" aria-hidden />
              <span className="absolute top-3 left-3 rounded-full bg-white/90 px-2.5 py-0.5 text-xs font-bold text-forest">Step {i + 1}</span>
            </div>
            <div className="p-5">
              <s.icon className="mb-3 h-6 w-6 text-brand" aria-hidden />
              <h3 className="text-lg font-bold text-forest">{s.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted">{s.body}</p>
            </div>
          </motion.li>
        ))}
      </motion.ol>
    </Section>
  )
}

const FEATURES = [
  { icon: Calculator, title: 'Transparent carbon engine', body: 'Activity × factor = CO₂e. 75 factors from DESNZ, EPA, Ember, IPCC and peer-reviewed food studies, each versioned and traceable.' },
  { icon: Gauge, title: 'Real-time dashboard', body: 'KPIs, category breakdowns and timelines for 7 days to a year, compared with the previous period.' },
  { icon: Radar, title: 'Anomaly detection', body: 'Robust weekly z-scores plus an Isolation Forest flag spikes such as “transport 42% above your normal week”.' },
  { icon: LineChart, title: 'Forecasting', body: 'Three models compete on a back-test; the winner forecasts 7–90 days with an 80% interval.' },
  { icon: FlaskConical, title: 'Scenario simulator', body: 'Drag sliders for driving, flights, renewables, meat and recycling and watch the modelled footprint update.' },
  { icon: MessageSquareText, title: 'AI sustainability assistant', body: 'Answers questions from your computed data. The model never invents numbers — every figure is validated.' },
  { icon: Target, title: 'Goals & achievements', body: 'Set reduction targets against your own baseline and track progress with clear measurement rules.' },
  { icon: Building2, title: 'Organisation mode', body: 'Teams log business travel and office energy into a shared company footprint with member breakdowns.' },
]

export function Features() {
  return (
    <Section id="features" eyebrow="Features" title="Everything you need to act on your footprint" className="bg-white">
      <motion.div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4" variants={stagger} initial="hidden" whileInView="show" viewport={{ once: true }}>
        {FEATURES.map((f) => (
          <motion.div key={f.title} variants={fadeUp} className="card card-hover p-6">
            <div className="mb-4 grid h-11 w-11 place-items-center rounded-xl bg-mint text-brand-deep"><f.icon className="h-5 w-5" aria-hidden /></div>
            <h3 className="font-bold text-forest">{f.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-muted">{f.body}</p>
          </motion.div>
        ))}
      </motion.div>
    </Section>
  )
}

const REC_TYPES: { title: string; how: string; image: SiteImage }[] = [
  { title: 'Swap car trips for public transport', how: 'Uses your logged trip count and average distance × (car − bus/rail factor).', image: images.tram },
  { title: 'Consider an electric car', how: 'Your monthly km × (current fuel factor − EV factor for the grid).', image: images.evCharging },
  { title: 'Switch to renewable electricity', how: 'Your grid kWh × (national grid intensity − renewable lifecycle factor).', image: images.solar },
  { title: 'Replace some beef & lamb meals', how: 'Servings you logged × (beef/lamb − vegetarian per-serving factor).', image: images.food },
  { title: 'Recycle and compost more', how: 'Your general-waste kg × (landfill − recycling/composting factor).', image: images.recycling },
  { title: 'Cycle the short hops', how: 'Short car trips you logged × car factor (cycling has zero direct emissions).', image: images.cycling },
]

export function RecommendationsPreview() {
  const scroller = useRef<HTMLDivElement>(null)
  const scroll = (dir: 1 | -1) => scroller.current?.scrollBy({ left: dir * 340, behavior: 'smooth' })
  return (
    <Section id="sustainability" eyebrow="Recommendations" title="Personal, quantified and explainable"
      intro="Recommendations only appear when your data shows the behaviour — and each one shows the calculation behind its estimate.">
      <div className="mb-4 flex justify-end gap-2">
        <button type="button" aria-label="Scroll left" onClick={() => scroll(-1)} className="rounded-full border border-line bg-white p-2 text-forest hover:bg-mint"><ChevronLeft className="h-5 w-5" /></button>
        <button type="button" aria-label="Scroll right" onClick={() => scroll(1)} className="rounded-full border border-line bg-white p-2 text-forest hover:bg-mint"><ChevronRight className="h-5 w-5" /></button>
      </div>
      <div ref={scroller} className="-mx-4 flex snap-x snap-mandatory gap-5 overflow-x-auto px-4 pb-4 [scrollbar-width:thin]" tabIndex={0} aria-label="Recommendation types">
        {REC_TYPES.map((r) => (
          <article key={r.title} className="card card-hover w-[300px] shrink-0 snap-start overflow-hidden">
            <img src={r.image.src} alt={r.image.alt} loading="lazy" className="h-40 w-full object-cover" />
            <div className="p-5">
              <h3 className="font-bold text-forest">{r.title}</h3>
              <p className="mt-2 text-sm text-muted"><span className="font-semibold text-ink">How it’s estimated: </span>{r.how}</p>
            </div>
          </article>
        ))}
      </div>
    </Section>
  )
}

export function DashboardPreview() {
  return (
    <Section id="analytics" eyebrow="Analytics" title="A dashboard that explains itself" className="bg-white"
      intro="Every chart is drawn from stored emission records — totals, category shares, trends, anomalies and forecasts.">
      <motion.figure variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
        className="overflow-hidden rounded-[1.5rem] border border-line bg-offwhite shadow-[var(--shadow-lift)]">
        <img src="/images/dashboard-preview.webp" alt="Screenshot of the Carbon Footprint Navigator dashboard showing KPIs, an emissions trend chart and a category breakdown"
          loading="lazy" className="w-full" />
        <figcaption className="border-t border-line bg-white px-5 py-3 text-xs text-muted">
          Real screenshot of the app running with the seeded demo account (≈6 months of generated activities).
        </figcaption>
      </motion.figure>
    </Section>
  )
}

const ML = [
  { icon: Calculator, title: 'Deterministic accounting', body: 'Emissions are never “guessed” by AI. Quantity × versioned factor, with unit conversion, occupancy and flight distance from airport coordinates.' },
  { icon: LineChart, title: 'Model-selected forecasting', body: 'Moving average, weekday-seasonal and a Ridge trend model are back-tested on your last 28 days; the lowest-MAE model wins.' },
  { icon: Radar, title: 'Two anomaly detectors', body: 'Median/MAD robust z-scores per category and week, plus a scikit-learn Isolation Forest over daily feature vectors.' },
  { icon: BrainCircuit, title: 'Grounded assistant', body: 'A context builder assembles your facts; the LLM explains them; a validator checks every number it writes against those facts.' },
]

export function MLSection() {
  return (
    <section className="relative overflow-hidden bg-forest py-20 text-white sm:py-24">
      <img src={images.earth.src} alt="" aria-hidden className="pointer-events-none absolute -right-40 -bottom-40 w-[560px] opacity-25" loading="lazy" />
      <div className="relative mx-auto max-w-7xl px-4 sm:px-6">
        <p className="eyebrow !text-algae-light">AI / ML</p>
        <h2 className="mt-2 max-w-2xl text-3xl font-extrabold sm:text-4xl">Machine learning where it helps. Arithmetic where it matters.</h2>
        <div className="mt-12 grid gap-5 md:grid-cols-2">
          {ML.map((m) => (
            <motion.div key={m.title} variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }}
              className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur transition hover:bg-white/10">
              <m.icon className="h-6 w-6 text-algae-light" aria-hidden />
              <h3 className="mt-3 text-lg font-bold">{m.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/75">{m.body}</p>
            </motion.div>
          ))}
        </div>
        <ol className="mt-12 flex flex-wrap items-center gap-2 text-xs font-semibold text-white/80" aria-label="Assistant pipeline">
          {['Your question', 'FastAPI', 'Context builder', 'Your emissions & ML outputs', 'LLM', 'Number validation', 'Answer'].map((s, i, arr) => (
            <li key={s} className="flex items-center gap-2">
              <span className="rounded-full border border-white/20 bg-white/10 px-3 py-1.5">{s}</span>
              {i < arr.length - 1 && <ArrowRight className="h-3.5 w-3.5 text-algae-light" aria-hidden />}
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}

export function ImpactSection() {
  const { factor } = useFactors()
  const no = factor('energy.electricity.grid', 'NO')
  const india = factor('energy.electricity.grid', 'IN')
  const beef = factor('food.meal.beef')
  const veg = factor('food.meal.vegan')
  const facts = [
    { image: images.wind, label: 'Grid electricity varies by country',
      value: no && india ? `${Math.round(india.co2e_per_unit / no.co2e_per_unit)}×` : '—',
      body: no && india ? `India’s grid emits ${india.co2e_per_unit} kg CO₂e/kWh vs Norway’s ${no.co2e_per_unit} — so the same kWh counts very differently.` : 'Loading factor data…' },
    { image: images.food, label: 'Food choices matter',
      value: beef && veg ? `${Math.round(beef.co2e_per_unit / veg.co2e_per_unit)}×` : '—',
      body: beef && veg ? `A beef meal (${beef.co2e_per_unit} kg) vs a vegan meal (${veg.co2e_per_unit} kg) using mean factors from Poore & Nemecek (2018).` : 'Loading factor data…' },
    { image: images.cycling, label: 'Active travel', value: '0 kg', body: 'Walking and cycling have no direct emissions — the platform tracks them so your progress shows.' },
  ]
  return (
    <Section eyebrow="Environmental impact" title="Small numbers add up — the data shows where">
      <div className="grid gap-6 md:grid-cols-3">
        {facts.map((f) => (
          <motion.article key={f.label} variants={fadeUp} initial="hidden" whileInView="show" viewport={{ once: true }} className="card card-hover overflow-hidden">
            <img src={f.image.src} alt={f.image.alt} loading="lazy" className="h-44 w-full object-cover" />
            <div className="p-6">
              <p className="text-sm font-semibold text-muted">{f.label}</p>
              <p className="mt-1 font-display text-4xl font-extrabold text-brand">{f.value}</p>
              <p className="mt-2 text-sm text-muted">{f.body}</p>
            </div>
          </motion.article>
        ))}
      </div>
    </Section>
  )
}

export function CTASection() {
  return (
    <section className="px-4 pb-20 sm:px-6">
      <div className="relative mx-auto max-w-7xl overflow-hidden rounded-[2rem]">
        <img src={images.forest.src} alt={images.forest.alt} loading="lazy" className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-r from-forest/95 via-forest/80 to-forest/30" aria-hidden />
        <div className="relative max-w-xl px-8 py-16 sm:px-14 sm:py-20">
          <h2 className="text-3xl font-extrabold text-white sm:text-4xl">Start with one week of data.</h2>
          <p className="mt-4 text-white/80">Answer a few onboarding questions for an instant estimate, then log activities to replace estimates with your real numbers.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink to="/register" size="lg" variant="light">Create a free account</ButtonLink>
            <ButtonLink to="/methodology" size="lg" variant="ghost" className="!text-white hover:!bg-white/10">Read the methodology</ButtonLink>
          </div>
        </div>
      </div>
    </section>
  )
}
