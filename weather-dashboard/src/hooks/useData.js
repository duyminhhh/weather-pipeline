import { useState, useEffect, useCallback } from 'react'
import { Queries } from '../api'

export function useQuery(queryFn, deps = []) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const run = useCallback(async () => {
    setLoading(true); setError(null)
    try {
      const result = await queryFn()
      setData(result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, deps)

  useEffect(() => { run() }, [run])

  return { data, loading, error, refetch: run }
}

export function useDashboard() {
  const latest   = useQuery(Queries.goldLatest)
  const stats    = useQuery(Queries.goldStats)
  const dailyAll = useQuery(Queries.goldDailyAll)
  return { latest, stats, dailyAll }
}

export function useMl() {
  const metrics  = useQuery(Queries.mlMetrics)
  const preds    = useQuery(Queries.mlPredictions)
  const featImp  = useQuery(Queries.mlFeatureImp)
  const forecast = useQuery(Queries.mlForecast)
  return { metrics, preds, featImp, forecast }
}
