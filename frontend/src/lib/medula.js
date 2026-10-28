import regionData from '../data/regions.json'

// How to register as a bone marrow (médula) donor in each region — every
// region runs it differently, so the app can't just show one centre. Each
// region's "medula" entry in data/regions.json was compiled by hand from its
// official page (researched 2026-10-28) and cross-checked against the
// Fundación Josep Carreras' per-region list of registration centres
// (https://fcarreras.org/donacion-de-medula/donde-hacer-donante-de-medula-osea/,
// last updated 2024-08 — where they disagree, the region's own page wins).
// Shown as MedulaInfoCard plus, where it applies, the map pins.
//
// `where` says which donation points take the sample, i.e. which ones the map
// shows while "médula" is selected (see takesMedula below):
//   - 'all':     every blood donation point, mobile units included
//   - 'fixed':   the region's fixed points only
//   - 'centres': only the fixed points named in `centres`
//   - 'none':    no walk-in — you phone or fill in a form first (or, in
//                Castilla y León, get a saliva kit by post), so no pins
// `summary` is the card's explanation; `phone` and `formUrl` (both optional)
// its calls to action. The official info page is the region's links.medula,
// like sangre/plasma (see regionLink in lib/regions.js).

// For regions with no entry: the Fundación Josep Carreras' national line,
// which runs the Spanish bone marrow donor registry (REDMO).
const MEDULA_FALLBACK = {
  where: 'none',
  summary: 'Llama a la Fundación Josep Carreras y te dirán dónde registrarte en tu comunidad.',
  phone: '900 102 688',
  url: 'https://fcarreras.org/es/donacion-de-medula/donde-hacer-donante-de-medula-osea/',
}

export function medulaInfo(region) {
  return regionData[region]?.medula ?? MEDULA_FALLBACK
}

// Whether a point takes bone marrow donor sign-ups, by its region's rule (or the ETL's own medula flag). Shared by App's donation-type filter
// and getPointInfo (the popup's donation-type tags), so both always agree.
export function takesMedula(feature) {
  const p = feature.properties ?? {}
  if (p.medula) return true
  const rule = regionData[p.region]?.medula
  if (!rule) return false
  const isFixed = !p.fecha
  switch (rule.where) {
    case 'all':
      return p.sangre !== false
    case 'fixed':
      return isFixed
    case 'centres':
      return isFixed && rule.centres.includes(p.name)
    default:
      return false
  }
}
