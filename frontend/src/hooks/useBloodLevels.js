import { useState, useEffect } from 'react'
import { fetchBloodLevels } from '../lib/supabase'

// Matches the badge order in the design: O+, A+, AB+, B+, O-, A-, AB-, B-.
// donarsangre.org (Comunidad de Madrid's source) spells "O" as digit "0" — see
// sql/create_blood_levels_table.sql — but centrodehemoterapiacyl.es (Castilla y
// León's source) spells it as the letter, so incoming rows are normalized to
// the letter before this lookup runs (see the "0" -> "O" replace below).
const BLOOD_TYPE_ORDER = ['O+', 'A+', 'AB+', 'B+', 'O-', 'A-', 'AB-', 'B-']

export function useBloodLevels(region) {
  const [bloodLevels, setBloodLevels] = useState([])

  useEffect(() => {
    if (!region) return
    let cancelled = false
    fetchBloodLevels(region).then(rows => {
      if (cancelled) return
      // Rows come back most-recent-first; keep only the latest row per blood_type.
      const latestByType = new Map()
      rows.forEach(row => {
        const bloodType = row.blood_type.replace('0', 'O')
        if (!latestByType.has(bloodType)) latestByType.set(bloodType, { ...row, blood_type: bloodType })
      })
      setBloodLevels(
        BLOOD_TYPE_ORDER.map(bloodType => latestByType.get(bloodType)).filter(Boolean)
      )
    })
    // Guards against an earlier region's slower response landing after a
    // later one's, e.g. when the user pans between regions in quick succession.
    return () => {
      cancelled = true
    }
  }, [region])

  return bloodLevels
}
