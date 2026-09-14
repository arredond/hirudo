export function getPointInfo(point) {
  const p = point.properties
  const isMobile = Boolean(p.fecha)
  return {
    isMobile,
    name: isMobile
      ? (p.name ?? '').replace(/^Equipo m[oó]vil en /i, '')
      : (p.name ?? ''),
    // "direccion"/"localidad"/"horario" are consolidated names every region's
    // ETL output uses regardless of how its own source spells them (see
    // MADRID_FIXED_POINT_COLUMN_ALIASES / CYL_LOCATION_COLUMN_ALIASES in
    // etl/main.py), so this stays region-agnostic rather than branching here.
    address: p.direccion,
    locality: p.localidad,
    hours: p.horario,
    openingHours: p.opening_hours,
    mapsUrl: isMobile ? p.url : p.gmaps_url,
    infoUrl: isMobile ? null : p.url,
    // Fixed-point extras shown in popup — Comunidad de Madrid only, no
    // equivalent scraped for other regions, so these are just absent there.
    roomLocation: p.ubicacion_de_las_salas_de_donacion,
    donorInfo: p.informacion_al_donante,
    notes: p.observaciones,
    zipCode: p.codigo_postal,
    // Every point accepts whole-blood ("sangre") donation; plasma/médula are only
    // available at the fixed points listed in puntos_fijos_otras_donaciones.json.
    donationTypes: {
      plasma: Boolean(p.plasma),
      sangre: true,
      medula: Boolean(p.medula),
    },
  }
}
