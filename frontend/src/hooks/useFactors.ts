import { useQuery } from '@tanstack/react-query'
import { useMemo } from 'react'

import { factorApi } from '../api/endpoints'
import type { EmissionFactor } from '../types/api'

/** Public emission-factor dataset with a lookup helper (region-specific first, then GLOBAL). */
export function useFactors() {
  const query = useQuery({ queryKey: ['factors', 'public'], queryFn: () => factorApi.list(), staleTime: 10 * 60_000 })
  const lookup = useMemo(() => {
    const map = new Map<string, EmissionFactor>()
    for (const f of query.data ?? []) map.set(`${f.key}|${f.region}`, f)
    return (key: string, region = 'GLOBAL') => map.get(`${key}|${region}`) ?? map.get(`${key}|GLOBAL`)
  }, [query.data])
  return { ...query, factor: lookup }
}
