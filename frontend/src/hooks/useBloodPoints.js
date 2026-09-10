import { useState, useEffect } from 'react'
import dayjs from 'dayjs'
import { fetchFixedPoints, fetchMobilePoints } from '../lib/supabase'

export function useBloodPoints(selectedDate) {
  const [fixedPoints, setFixedPoints] = useState([])
  const [mobilePoints, setMobilePoints] = useState([])
  const [loadingMobile, setLoadingMobile] = useState(true)

  useEffect(() => {
    fetchFixedPoints().then(geojson => {
      const features = geojson?.features ?? []
      // Deduplicate by name — the DB can have duplicate rows from past ETL runs
      const seen = new Set()
      setFixedPoints(features.filter(f => {
        const key = f.properties?.name
        if (seen.has(key)) return false
        seen.add(key)
        return true
      }))
    })
  }, [])

  useEffect(() => {
    setLoadingMobile(true)
    const dateStr = (selectedDate ?? dayjs()).format('DD/MM/YYYY')
    fetchMobilePoints(dateStr).then(geojson => {
      setMobilePoints(geojson?.features ?? [])
      setLoadingMobile(false)
    })
  }, [selectedDate?.format('YYYY-MM-DD')])

  return { fixedPoints, mobilePoints, loadingMobile }
}
