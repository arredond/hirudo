// Great-circle distance in km. Shared by ListPanel (distance-to-point sorting)
// and regions.js (nearest-region lookup) — small enough that a proper geo
// library would be overkill.
export function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371
  const toRad = x => (x * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLng = toRad(lng2 - lng1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2
  return R * 2 * Math.asin(Math.sqrt(a))
}
