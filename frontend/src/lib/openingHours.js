import OpeningHours from 'opening_hours'

// opening_hours.js bundles real Spanish public-holiday data at CCAA
// granularity, keyed by the exact same region names this app already uses
// (e.g. "only_states":["Castilla y León"]) — so a point's own `region`
// (from its DB row) is passed straight through as `state`, no lookup or
// Nominatim call needed. Without a known region, `state` is simply omitted:
// opening_hours.js still applies nationwide (non-state-restricted)
// holidays, which is safer than guessing a region.
// The few regions whose name in opening_hours.js differs from ours.
const HOLIDAY_STATE_NAMES = {
  'Comunidad Foral de Navarra': 'Navarra',
  'Illes Balears': 'Islas Baleares',
  'Principado de Asturias': 'Asturias',
}

function nominatimObjectFor(region) {
  const state = HOLIDAY_STATE_NAMES[region] ?? region
  return { address: { country_code: 'es', ...(state ? { state } : {}) } }
}

// Every point's hours are published in its own local time. That's
// Europe/Madrid everywhere except Canarias, an hour behind.
const DEFAULT_TIME_ZONE = 'Europe/Madrid'
const REGION_TIME_ZONES = { Canarias: 'Atlantic/Canary' }

// opening_hours.js reads a Date's local (viewer's clock) fields. To evaluate
// a point's hours at the viewer's current instant, build a Date whose local
// fields are that instant's wall-clock time in the point's own time zone.
function wallClockIn(date, timeZone) {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-US', {
      timeZone,
      hourCycle: 'h23',
      year: 'numeric', month: 'numeric', day: 'numeric',
      hour: 'numeric', minute: 'numeric', second: 'numeric',
    })
      .formatToParts(date)
      .map(({ type, value }) => [type, Number(value)])
  )
  return new Date(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute, parts.second)
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
// Madrid") — see nominatimObjectFor above. `date` is the viewer's instant; the
// hours are checked at that instant's wall-clock time in the point's own
// time zone (see wallClockIn), so nextChange is in that local time too.
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
    const localDate = wallClockIn(date, REGION_TIME_ZONES[region] ?? DEFAULT_TIME_ZONE)
    return {
      isOpen: oh.getState(localDate),
      nextChange: oh.getNextChange(localDate) ?? null,
      permanentlyClosed: false,
      temporarilyClosed: false,
    }
  } catch (error) {
    console.warn('Could not parse opening_hours:', openingHoursString, error)
    return null
  }
}
