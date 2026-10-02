export function formatKg(kg: number | null | undefined, opts: { precise?: boolean } = {}): string {
  if (kg === null || kg === undefined || Number.isNaN(kg)) return '—'
  const abs = Math.abs(kg)
  if (abs >= 1000) return `${(kg / 1000).toLocaleString(undefined, { maximumFractionDigits: 2 })} t`
  const digits = opts.precise || abs < 10 ? 2 : abs < 100 ? 1 : 0
  return `${kg.toLocaleString(undefined, { maximumFractionDigits: digits })} kg`
}

export function formatNumber(n: number | null | undefined, digits = 1): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return n.toLocaleString(undefined, { maximumFractionDigits: digits })
}

export function formatPct(pct: number | null | undefined, signed = false): string {
  if (pct === null || pct === undefined || Number.isNaN(pct)) return '—'
  const s = `${Math.abs(pct).toLocaleString(undefined, { maximumFractionDigits: 1 })}%`
  if (!signed) return s
  return pct > 0 ? `+${s}` : pct < 0 ? `−${s}` : s
}

export function formatDate(iso: string, opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short' }): string {
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00` : iso)
  return d.toLocaleDateString(undefined, opts)
}

export function todayIso(): string {
  const d = new Date()
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

export function addDaysIso(days: number): string {
  const d = new Date()
  d.setDate(d.getDate() + days)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10)
}

export function titleCase(s: string): string {
  return s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function errorMessage(err: unknown): string {
  if (err instanceof Error) return err.message
  return 'Something went wrong.'
}
