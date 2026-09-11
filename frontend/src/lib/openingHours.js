import OpeningHours from 'opening_hours'

// The ETL only covers Comunidad de Madrid (see REGION in etl/main.py), so this is
// hardcoded rather than derived per point. It gives opening_hours.js real Spanish/
// Madrid public-holiday resolution for PH rules.
const NOMINATIM_OBJECT = { address: { country_code: 'es', state: 'Madrid' } }

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
// to the lookup table).
export function getOpenStatus(openingHoursString, date = new Date()) {
  if (!openingHoursString) return null
  if (isPermanentlyClosed(openingHoursString)) {
    return { isOpen: false, nextChange: null, permanentlyClosed: true, temporarilyClosed: false }
  }
  if (isTemporarilyClosed(openingHoursString)) {
    return { isOpen: false, nextChange: null, permanentlyClosed: false, temporarilyClosed: true }
  }

  try {
    const oh = new OpeningHours(openingHoursString, NOMINATIM_OBJECT)
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
