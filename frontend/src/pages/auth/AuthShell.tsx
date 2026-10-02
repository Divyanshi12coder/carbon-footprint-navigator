import { motion } from 'framer-motion'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { images } from '../../assets/images'
import { Logo } from '../../components/ui/misc'

export function AuthShell({ title, subtitle, children, footer }: { title: string; subtitle: string; children: ReactNode; footer: ReactNode }) {
  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      <div className="flex flex-col px-5 py-8 sm:px-10">
        <Link to="/" aria-label="Home"><Logo /></Link>
        <motion.main initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="mx-auto my-auto w-full max-w-md py-10">
          <h1 className="text-3xl font-extrabold text-forest">{title}</h1>
          <p className="mt-2 text-muted">{subtitle}</p>
          <div className="mt-8">{children}</div>
          <div className="mt-6 text-sm text-muted">{footer}</div>
        </motion.main>
      </div>
      <div className="relative hidden lg:block">
        <img src={images.wind.src} alt={images.wind.alt} className="absolute inset-0 h-full w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-t from-forest/85 via-forest/30 to-transparent" aria-hidden />
        <blockquote className="absolute right-10 bottom-12 left-10 text-white">
          <p className="font-display text-2xl leading-snug font-bold">“What gets measured gets managed — as long as the measurement is honest.”</p>
          <p className="mt-3 text-sm text-white/75">Every estimate in Carbon Footprint Navigator links to its emission factor and source.</p>
        </blockquote>
      </div>
    </div>
  )
}
