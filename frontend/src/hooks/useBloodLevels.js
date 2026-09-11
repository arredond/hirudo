import { useState, useEffect } from 'react'
import { fetchBloodLevels } from '../lib/supabase'

// Matches the badge order in the design: O+, A+, AB+, B+, O-, A-, AB-, B-.
// donarsangre.org (and this DB's blood_type column) spells "O" as digit "0" — see
// sql/create_blood_levels_table.sql — so the lookup keys use "0" too.
const BLOOD_TYPE_ORDER = ['0+', 'A+', 'AB+', 'B+', '0-', 'A-', 'AB-', 'B-']

export function useBloodLevels() {
  const [bloodLevels, setBloodLevels] = useState([])

  useEffect(() => {
    fetchBloodLevels().then(rows => {
      // Rows come back most-recent-first; keep only the latest row per blood_type.
      const latestByType = new Map()
      rows.forEach(row => {
        if (!latestByType.has(row.blood_type)) latestByType.set(row.blood_type, row)
      })
      setBloodLevels(
        BLOOD_TYPE_ORDER.map(bloodType => latestByType.get(bloodType)).filter(Boolean)
      )
    })
  }, [])

  return bloodLevels
}
