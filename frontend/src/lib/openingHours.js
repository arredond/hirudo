import OpeningHours from 'opening_hours'

// opening_hours.js bundles real Spanish public-holiday data at CCAA
// granularity, keyed by the exact same region names this app already uses
// (e.g. "only_states":["Castilla y León"]) — so a point's own `region`
// (from its DB row) is passed straight through as `state`, no lookup or
// Nominatim call needed. Without a known region, `state` is simply omitted:
// opening_hours.js still applies nationwide (non-state-restricted)
// holidays, which is safer than guessing a region.
function nominatimObjectFor(region) {
  return { address: { country_code: 'es', ...(region ? { state: region } : {}) } }
}

// Hand-maintained sentinels in etl/utils/opening_hours_fijos.json, checked before
// generic OSM parsing — not valid opening_hours syntax on their own.
const CLOSED_SENTINEL = 'closed'
const TEMPORARILY_CLOSED_SENTINEL = 'temporarily closed'

export function isPermanentlyClosed(openingHoursString) {
  return (openingHoursString ?? '').trim() === CLOSED_SENTINEL
}

export function isTemporarilyClosed(openingHoursString) {
  return (openingHoursString ?? '').trim() === TEMPORARILY_CLOSED_SENTINEL
}

// Returns { isOpen, nextChange, permanentlyClosed, temporarilyClosed }, or null if
// openingHoursString is missing or fails to parse (e.g. a fixed point not yet added
// to the lookup table). `region` is a point's own region (e.g. "Comunidad de
// Madrid") — see nominatimObjectFor above.
export function getOpenStatus(openingHoursString, date = new Date(), region = null) {
  if (!openingHoursString) return null
  if (isPermanentlyClosed(openingHoursString)) {
    return { isOpen: false, nextChange: null, permanentlyClosed: true, temporarilyClosed: false }
  }
  if (isTemporarilyClosed(openingHoursString)) {
    return { isOpen: false, nextChange: null, permanentlyClosed: false, temporarilyClosed: true }
  }

  try {
    const oh = new OpeningHours(openingHoursString, nominatimObjectFor(region))
    return {
      isOpen: oh.getState(date),
      nextChange: oh.getNextChange(date) ?? null,
      permanentlyClosed: false,
      temporarilyClosed: false,
    }
  } catch (error) {
    console.warn('Could not parse opening_hours:', openingHoursString, error)
    return null
  }
}
