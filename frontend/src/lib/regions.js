import { haversine } from './geo'
import regionBoundaries from '../data/regionBoundaries.json'

// Every region the ETL covers (etl/main.py: REGION_MADRID, REGION_CYL) —
// also the option list for the header's region dropdown.
export const REGIONS = ['Comunidad de Madrid', 'Castilla y León']

// regionBoundaries.json holds just these two regions' real polygons, trimmed
// from codeforgermany/click_that_hood's spain-communities.geojson (public
// domain-ish community dataset) down to ~15KB. An earlier version of this
// module guessed the region from whichever fixed point was nearest instead —
// but that's biased by point *density*, not the real border: Madrid's 32
// fixed points vs. Castilla y León's 10, spread over a much bigger area,
// bulged Madrid's detected area well past its actual (small) territory. Real
// polygons don't have that problem.
function pointInRing(lng, lat, ring) {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i]
    const [xj, yj] = ring[j]
    const crosses = yi > lat !== yj > lat && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi
    if (crosses) inside = !inside
  }
  return inside
}

function pointInGeometry(lng, lat, geometry) {
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates
  return polygons.some(([outer, ...holes]) => {
    if (!pointInRing(lng, lat, outer)) return false
    return !holes.some(hole => pointInRing(lng, lat, hole))
  })
}

// The region whose real boundary contains the given map center, or null if
// it falls outside every region we have a boundary for (e.g. panned to some
// other part of Spain) — see nearestCoveredRegion for a fallback then.
export function regionAt(center) {
  if (!center) return null
  const feature = regionBoundaries.features.find(f =>
    pointInGeometry(center.lng, center.lat, f.geometry)
  )
  return feature?.properties?.region ?? null
}

// Fallback for when the map center isn't inside any region we cover —
// picks whichever fixed point is closest and uses its region, so the
// title/blood levels still show *something* relevant instead of going blank.
export function nearestCoveredRegion(fixedPoints, center) {
  if (!center || fixedPoints.length === 0) return null
  let best = null
  let bestDist = Infinity
  for (const point of fixedPoints) {
    const [lng, lat] = point.geometry.coordinates
    const dist = haversine(center.lat, center.lng, lat, lng)
    if (dist < bestDist) {
      bestDist = dist
      best = point.properties?.region ?? null
    }
  }
  return best
}
