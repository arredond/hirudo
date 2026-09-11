import OpeningHours from 'opening_hours'

// The ETL only covers Comunidad de Madrid (see REGION in etl/main.py), so this is
// hardcoded rather than derived per point. It gives opening_hours.js real Spanish/
// Madrid public-holiday resolution for PH rules.
const NOMINATIM_OBJECT = { address: { country_code: 'es', state: 'Madrid' } }

// The OSM opening_hours spec's literal sentinel for "permanently closed" — see
// etl/utils/opening_hours_fijos.json, where this is set by hand for shut-down centers.
const CLOSED_SENTINEL = 'closed'

export function isPermanentlyClosed(openingHoursString) {
  return (openingHoursString ?? '').trim() === CLOSED_SENTINEL
}

// Returns { isOpen, nextChange, permanentlyClosed }, or null if openingHoursString is
// missing or fails to parse (e.g. a fixed point not yet added to the lookup table).
export function getOpenStatus(openingHoursString, date = new Date()) {
  if (!openingHoursString) return null
  if (isPermanentlyClosed(openingHoursString)) {
    return { isOpen: false, nextChange: null, permanentlyClosed: true }
  }

  try {
    const oh = new OpeningHours(openingHoursString, NOMINATIM_OBJECT)
    return {
      isOpen: oh.getState(date),
      nextChange: oh.getNextChange(date) ?? null,
      permanentlyClosed: false,
    }
  } catch (error) {
    console.warn('Could not parse opening_hours:', openingHoursString, error)
    return null
  }
}
