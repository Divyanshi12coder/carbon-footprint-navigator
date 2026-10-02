import { motion } from 'framer-motion'
import { ArrowRight, BarChart3, ShieldCheck, TrainFront } from 'lucide-react'

import { images } from '../../assets/images'
import { useFactors } from '../../hooks/useFactors'
import { ButtonLink } from '../ui/Button'
import { Skeleton } from '../ui/feedback'

export function Hero() {
  const { factor, isLoading } = useFactors()
  const car = factor('transport.car.petrol')
  const rail = factor('transport.rail')
  const railSaving = car && rail ? Math.round(100 * (1 - rail.co2e_per_unit / car.co2e_per_unit)) : null

  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-mint/70 via-offwhite to-offwhite pt-28 pb-16 sm:pt-32 lg:pb-24">
      <div className="pointer-events-none absolute -top-40 -right-40 h-[520px] w-[520px] rounded-full bg-algae-light/30 blur-3xl" aria-hidden />
      <div className="relative mx-auto grid max-w-7xl items-center gap-12 px-4 sm:px-6 lg:grid-cols-[1.05fr_1fr]">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
          <span className="inline-flex items-center gap-2 rounded-full border border-algae-light/60 bg-white/80 px-3 py-1 text-xs font-semibold text-brand-deep">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden /> Sourced emission factors · explainable ML
          </span>
          <h1 className="mt-5 text-4xl leading-[1.08] font-extrabold text-forest sm:text-5xl lg:text-6xl">
            Understand your carbon.
            <span className="block bg-gradient-to-r from-brand to-algae bg-clip-text text-transparent">Change your impact.</span>
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-muted">
            Log journeys, energy, food and purchases. Carbon Footprint Navigator calculates CO₂e with published emission
            factors, spots unusual spikes, forecasts where you’re heading and shows — with the maths — which changes cut the most.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink to="/register" size="lg" icon={<ArrowRight className="h-4 w-4" />}>Start tracking</ButtonLink>
            <ButtonLink to="/login" state={{ demo: true }} size="lg" variant="secondary" icon={<BarChart3 className="h-4 w-4" />}>
              Explore the dashboard
            </ButtonLink>
          </div>
          <p className="mt-4 text-xs text-muted">Explore with the demo account — credentials are pre-filled on the sign-in page.</p>
        </motion.div>

        <motion.div className="relative" initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.7, delay: 0.1 }}>
          <div className="relative overflow-hidden rounded-[2rem] shadow-[var(--shadow-lift)]">
            <img src={images.heroCity.src} alt={images.heroCity.alt} className="aspect-[4/3] w-full object-cover" fetchPriority="high" />
            <div className="absolute inset-0 bg-gradient-to-t from-forest/50 via-transparent to-transparent" aria-hidden />
            <p className="absolute top-4 right-5 rounded-full bg-forest/60 px-3 py-1 text-xs font-semibold text-white backdrop-blur">Measure → Understand → Reduce → Improve</p>
          </div>
          <motion.div className="glass absolute -bottom-6 -left-4 w-60 rounded-2xl p-4 shadow-[var(--shadow-lift)] sm:-left-8"
            initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
            <div className="flex items-center gap-2 text-xs font-semibold text-brand-deep">
              <TrainFront className="h-4 w-4" aria-hidden /> Train vs petrol car
            </div>
            {isLoading || railSaving === null ? (
              <Skeleton className="mt-2 h-8 w-24" />
            ) : (
              <p className="mt-1 font-display text-3xl font-extrabold text-forest">−{railSaving}%</p>
            )}
            <p className="text-xs text-muted">CO₂e per km, from the live factor dataset ({rail?.source.split(' ').slice(0, 2).join(' ') ?? 'DESNZ'})</p>
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}
