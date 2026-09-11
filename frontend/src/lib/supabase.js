import { createClient } from '@supabase/supabase-js'

const SUPABASE_URL = 'https://tasrhjtpqshgxfofwery.supabase.co'
const SUPABASE_KEY = 'sb_publishable_GYgKDp3djbq9SvNm71FZZQ_cBl2AaN5'

export const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

export async function fetchFixedPoints() {
  const { data, error } = await supabase.rpc('get_puntos_fijos_geojson').select('geojson')
  if (error) throw error
  return data[0]?.geojson ?? null
}

export async function fetchMobilePoints(date) {
  const { data, error } = await supabase.rpc('get_puntos_moviles_geojson', { filter_date: date })
  if (error) throw error
  return data[0]?.geojson ?? null
}

// The ETL only covers Comunidad de Madrid (see REGION in etl/main.py).
const REGION = 'Comunidad de Madrid'

// blood_levels is append-only (one snapshot of 8 rows per ETL run), so this fetches
// enough recent rows to cover the latest snapshot and lets the caller dedupe by
// blood_type, keeping the most recent row for each.
export async function fetchBloodLevels() {
  const { data, error } = await supabase
    .from('blood_levels')
    .select('blood_type, status, level, label, updated_at')
    .eq('region', REGION)
    .order('updated_at', { ascending: false })
    .limit(32)
  if (error) throw error
  return data ?? []
}
