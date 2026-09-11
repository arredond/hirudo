export function getPointInfo(point) {
  const p = point.properties
  const isMobile = Boolean(p.fecha)
  return {
    isMobile,
    name: isMobile
      ? (p.name ?? '').replace(/^Equipo m[oó]vil en /i, '')
      : (p.name ?? ''),
    address: isMobile ? p.direccion : p.direccion_postal,
    locality: isMobile ? p.localidad : p.municipio,
    hours: isMobile ? p.horario : p.horario_de_donaciones,
    openingHours: p.opening_hours,
    mapsUrl: isMobile ? p.url : p.gmaps_url,
    infoUrl: isMobile ? null : p.url,
    // Fixed-point extras shown in popup
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
