import { takesMedula } from './medula'

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
    // FIXED_POINT_COLUMN_ALIASES / LOCATION_COLUMN_ALIASES in
    // etl/regions/madrid.py and castilla_y_leon.py), so this stays region-agnostic rather than branching here.
    address: p.direccion,
    locality: p.localidad,
    hours: p.horario,
    openingHours: p.opening_hours,
    // The point's own region (e.g. "Comunidad de Madrid") — passed to
    // OpenStatusBadge so opening_hours.js resolves "PH" against the right
    // CCAA's public holidays instead of a fixed one (see lib/openingHours.js).
    region: p.region,
    mapsUrl: isMobile ? p.url : p.gmaps_url,
    infoUrl: isMobile ? null : p.url,
    // Fixed-point extras shown in popup — Comunidad de Madrid only, no
    // equivalent scraped for other regions, so these are just absent there.
    roomLocation: p.ubicacion_de_las_salas_de_donacion,
    donorInfo: p.informacion_al_donante,
    notes: p.observaciones,
    zipCode: p.codigo_postal,
    // Every point accepts whole-blood ("sangre") donation by default; plasma
    // only where its flag is set, médula by its region's rule (lib/medula.js). Only
    // Castilla-La Mancha's mobile points ever mark a point sangre: false (a
    // plasma-only stop) — everywhere else the field is simply absent, so the
    // default stays permissive (matches App.jsx's donation-type filter).
    // Set by the ETL (flag_appointments) where the source says the point only
    // takes donors by appointment; absent or false means walk-ins are fine.
    appointmentRequired: p.cita_previa === true,
    donationTypes: {
      plasma: Boolean(p.plasma),
      sangre: p.sangre !== false,
      medula: takesMedula(point),
    },
  }
}
