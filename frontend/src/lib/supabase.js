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
