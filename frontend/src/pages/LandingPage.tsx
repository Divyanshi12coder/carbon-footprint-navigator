import { lazy, Suspense } from 'react'

import { Hero } from '../components/landing/Hero'
import {
  CTASection,
  DashboardPreview,
  Features,
  HowItWorks,
  ImpactSection,
  MLSection,
  RecommendationsPreview,
  TechStrip,
} from '../components/landing/Sections'
import { CardSkeleton } from '../components/ui/feedback'

// Recharts is only needed for this section — keep it out of the landing bundle.
const ImpactExplorer = lazy(() => import('../components/landing/ImpactExplorer').then((m) => ({ default: m.ImpactExplorer })))

export default function LandingPage() {
  return (
    <>
      <Hero />
      <TechStrip />
      <HowItWorks />
      <Features />
      <section className="py-20 sm:py-24" aria-labelledby="explorer-title">
        <div className="mx-auto grid max-w-7xl gap-10 px-4 sm:px-6 lg:grid-cols-[1fr_1.4fr] lg:items-center">
          <div>
            <p className="eyebrow">Interactive</p>
            <h2 id="explorer-title" className="mt-2 text-3xl font-extrabold text-forest sm:text-4xl">See the carbon behind everyday choices</h2>
            <p className="mt-4 text-lg text-muted">
              These bars aren’t illustrations — they’re computed from the same emission-factor table the calculation engine uses.
              Hover a bar to see the factor and its source.
            </p>
          </div>
          <Suspense fallback={<CardSkeleton rows={7} />}>
            <ImpactExplorer />
          </Suspense>
        </div>
      </section>
      <RecommendationsPreview />
      <DashboardPreview />
      <MLSection />
      <ImpactSection />
      <CTASection />
    </>
  )
}
