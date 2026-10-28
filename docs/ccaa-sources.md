# Blood donation sources per Comunidad Autónoma

Spain's public healthcare is run per Comunidad Autónoma (CCAA), so each one
publishes (or doesn't) its own donation-point and blood-level pages — there's
no national source. This tracks what's been found for each, so extending the
ETL to a new region doesn't mean re-researching from scratch.

Each region's scraper lives at `etl/utils/crawl/<region>.py`; see `main.py`'s
`REGION_*` constants and `scrape_*_<region>` functions for how a region is
wired in once its sources are known.

## Implemented

### Comunidad de Madrid
- Fixed points: <https://donarsangre.sanidadmadrid.org/fijos.aspx>
- Mobile points: <https://donarsangre.sanidadmadrid.org/moviles.aspx>
- Blood levels ("semáforo de necesidades"): <https://www.donarsangre.org/>
- ASP.NET site — needs a GET (for VIEWSTATE tokens) then a POST to list
  points. Fixed-point detail pages carry real coordinates directly (via a
  Google Maps link) — see `extract_fixed_point_details` in `madrid.py`.

### Castilla y León
- Fixed **and** mobile points, one page per province:
  <https://www.centrodehemoterapiacyl.es/puntos-de-donacion/><province>/
  (provinces: avila, burgos, leon, palencia, salamanca, segovia, soria,
  valladolid, zamora)
- Blood levels ("niveles de sangre actuales"): homepage widget at
  <https://www.centrodehemoterapiacyl.es/>
  (as of Oct 2026 the widget renders as a raw `[reservaSangre]` shortcode —
  the same breakage as the mobile tables — so it scrapes no rows until fixed)
- WordPress site, plain HTML tables. Needs a real `User-Agent` header or the
  homepage 403s. Fixed points' Google Maps short link resolves to real
  coordinates from its first redirect — no Geocoding API call needed for
  those (see `resolve_gmaps_coords`).

### Castilla-La Mancha
- Fixed points (single page): <https://sanidad.castillalamancha.es/ciudadanos/hazte-donante-sangre/puntos-fijos-de-donacion>
- Mobile points, one page per province (paginated via `?page=N`):
  <https://sanidad.castillalamancha.es/ciudadanos/hazte-donante-sangre/colectas-donantes-de-sangre/><province>
  (provinces: albacete, ciudad-real, cuenca, guadalajara, toledo)
- Blood levels: **none found**. The frontend shows a "no data for this
  region" placeholder instead (see `BloodLevelBadges.jsx`).
- Drupal Views site. Fixed-point addresses mix the center name into the
  street address with no reliable separator — see the note in
  `castilla_la_mancha.py`'s `parse_fixed_points`. Mobile points mark
  plasma-only stops ("Tipo de donación") — the only region with that
  distinction so far, wired into a `sangre`/`plasma` flag.

### Aragón
- Fixed points: homepage "Puntos fijos de donación" block at
  <https://bancosangrearagon.org/> (5 centers: Zaragoza ×3, Huesca, Teruel)
- Mobile points: <https://bancosangrearagon.org/extracciones/> is a WordPress
  "The Events Calendar" view — read via its REST API instead:
  <https://bancosangrearagon.org/wp-json/tribe/events/v1/events> (paginated,
  `next_rest_url`). Events carry **no venue/address/locality** — only a title
  like "Sariñena, en el Centro de Salud" (town *or* organization, then venue),
  so geocoding is title-only (see `scrape_mobile_points_aragon`): Geocoding
  API + a Places "Find Place" free-text candidate, plus hand-pinned
  locations in `etl/utils/aragon_mobile_locations.json` for the stops
  neither gets right (add to it when a new one shows up mislocated).
- Plasma: only at the Banco itself (C/ Ramón Salanova 1, Zaragoza), by phone
  appointment — <https://bancosangrearagon.org/donacion-de-plasma-sanguineo/>.
  (The "Edificio Pignatelli, Pº María Agustín 36" address in the site footer
  is the Gobierno de Aragón's HQ, not a donation point.)
- Blood levels: **none found** (frontend shows the placeholder).

### Comunidad Valenciana
- Fixed **and** mobile points, one page per province:
  <https://centro-transfusion.san.gva.es/es/puntos-de-donacion?provincia=><province>
  (provinces: castellon, valencia, alicante)
- Each page lists its fixed points (name + address only) and then a
  per-date schedule table with **every** point's hours — fixed points'
  rows are split off as their own day-by-day schedule (dated
  `opening_hours`, no weekly pattern / no `opening_hours_fijos.json` entry).
  A stop open morning and afternoon appears as two rows (merged). Dates
  have no year ("Martes, 27 de octubre") — inferred from the weekday.
- Restricted stops ("(SOLO EMPLEADOS)", "-SOLO ALUMNOS-", "EXCLUSIVA
  PERSONAL"…) are kept, with the note appended to the point's name.
  Plasma-only stops ("SOLO DONACIÓN DE PLASMA CON CITA PREVIA") get
  `sangre: false`. Plasma at fixed points: the three Centros de Transfusión,
  by phone appointment (<https://centro-transfusion.san.gva.es/es/plasmaferesi>).
- Blood levels: **none found** (frontend shows the placeholder).

### Cataluña
- Fixed points: hospitals listed on
  <https://www.bancsang.net/es/donaciones/sangre/donde/>, each with an info
  page at `/es/hospitales/<id>/` (address + free-text weekly "Horario",
  hand-translated into `opening_hours_fijos.json`, keyed by name). All take
  plasma too.
- Mobile points: <https://www.bancsang.net/es/donaciones/sangre/calendario-de-recogida/>
  lists ~a month of stops as cards (town / venue / street + "Dona
  sangre"/"Dona plasma" buttons — the donation-type flags come straight from
  those). **Hours are only on each stop's own booking page**
  (`<p class="horari">`), so the ETL fetches one page per stop (~260
  requests, ~1 min). Plasma-only stops' pages list booking slots only, so
  they have no hours.
- Donation-bus stops ("Unidad móvil …") skip the Places candidate: their
  street address is the spot.
- Hand-pinned locations in `etl/utils/cataluna_mobile_locations.json`,
  matched by "venue, town" or "street, town" — mostly villages inside a
  multi-village municipality (Google's address names the village, so the
  Places town check rejects a correct match), plus street geocodes that
  landed in the wrong town.
- Blood levels: **none found** (frontend shows the placeholder).

### Galicia
- Fixed points ("Locais de doazón", 7 cities): <https://ados.sergas.gal/cartafol/ADOS-locais>
  — one SharePoint accordion page. Most carry "Coordenadas GPS" in
  degrees/minutes/seconds (used as-is, no geocoding); Ourense has none and
  is geocoded. Hours are free text (Ourense and Pontevedra have a winter
  Oct–May and summer Jun–Sep schedule), hand-translated into
  `opening_hours_fijos.json`, keyed by name. All take plasma
  (<https://ados.sergas.gal/cartafol/Sangue-Plasmaferesis>).
- Mobile points ("Desprazamentos das unidades móbiles"): <https://ados.sergas.gal/cartafol/proximos-desprazamentos>
  — ~3 weeks of donation-bus stops grouped by health area and date: concello,
  "Lugar de colecta" (town, parish, neighbourhood or campus) and a spot
  description ("UNIDADE MÓBIL DIANTE DA CASA DA XUVENTUDE"). A row can list
  several spots ("QUINS: …", "MELON: …"); unfilled "Localización 2" slots are
  dropped. "Provisional" stops are kept, flagged in the name. Geocoded from
  the spot description via Geocoding API + Places, plus hand pins in
  `etl/utils/galicia_mobile_locations.json` (matched by "description,
  concello").
- Blood levels ("Semáforo"): <https://ados.sergas.gal/cartafol/sangue-semaforo>
  — **an image only** (`Semaforo_<date>.png`), a 4×2 grid of four-light
  traffic lights in a fixed blood-type order; the lit light's hue is read
  off the pixels (see `parse_blood_levels_image`). Four levels — red, orange,
  yellow, green — kept as-is (Madrid and CyL have three).
- Everything is in Galician.

### País Vasco
- Fixed **and** mobile points: <https://donantesdesangre.eus/donde-donar/>
  loads each province (Araba, Bizkaia, Gipuzkoa) one day at a time from
  `wp-content/themes/hello-elementor/extracciones/index.php?idioma=ES&provincia=<P>&fechaInicio=YYYY/MM/DD`
  (the page's calendar selector just changes the date). The ETL asks for 60
  days ahead × 3 provinces (~180 requests, ~25 s). Every spot links to
  `google.com/maps/place/<lat>,<lng>` — **no geocoding**.
- No separate fixed-point list: the permanent centres (CVTTH Galdakao,
  Manuel Lekuona Donostia, Ambulatorio Olaguibel Vitoria) plus every spot
  named ambulatorio/anbulategi/hospital/ospitale are fixed points with a
  dated day-by-day schedule (like Valencia's). Generic names
  ("Anbulategia/Ambulatorio") get the town appended.
- Plasma-only spots ("Solo Plasma/Cita", "COLECTA PLASMAS") get `sangre:
  false`; "(colecta privada)" company/school stops keep the note in the name.
  Which centres take plasma isn't published (booked by phone), so the
  other fixed points leave the flag unset.
- Blood levels: <https://donantesdesangre.eus/> loads
  `.../niveles-sangre/index.php?idioma=ES` — one blood-bag image per type
  whose filename is the level (`Reserva-Sangre-01` green "Dona en la próxima
  colecta", `-02` yellow "Dona en 2 o 3 días", `-03` red "Dona urgente").
- Boundary polygon keeps the Treviño (Burgos) and Villaverde (Cantabria)
  enclave holes.

### Andalucía
- Entry page: <https://www.juntadeandalucia.es/temas/salud/servicios/donacion-sangre.html>
  links each province's Centro de transfusión, tejidos y células (CTTC),
  all on sspa.juntadeandalucia.es with one template per province
  (`informacion-por-centros/<id>`): Almería 20585, Cádiz 16502, Córdoba 16503,
  Granada 16504, Huelva 16505, Jaén 16506, Málaga 16507, Sevilla 16508.
- Fixed points: each CTTC page's own address (`field--name-field-direccion`,
  `-codigo-postal`, `-municipio`) and one repeating weekly timetable
  (`table.center-schedule__table`, one row per weekday). Each province has
  one fixed point, geocoded from its street address (no coordinates on the
  page); `opening_hours` is built straight from the weekly table
  (`opening_hours.parse_weekly_hours`), so there's no hand-built lookup.
- Mobile points: the same page's "Se puede donar en..." table
  (`div.center-blood table.views-table`): date (DD-MM-YYYY), town, venue
  ("Lugar") and hours, a few weeks ahead, server-rendered and unpaginated.
  Hours come in several styles ("09:00 - 14:30", "DE 17,30 a 21,00", "17 a 21
  HORAS", "10 a 14 Y 17 a 21 HORAS"), normalized to "HH:MM - HH:MM" before
  `parse_mobile_hours`. Venues are geocoded from venue + town (like
  Castilla-La Mancha's), with no Places lookup. Mobile stops don't say
  whether they take whole blood or plasma, so `sangre`/`plasma` stay unset.
- Known quirks: "DESDE LAS 17,00 HORAS" (open-ended, no closing time) gets no
  `opening_hours`; one Almería stop lists "Plasma Centro de Transfusion" as
  its town.
- Blood levels: none. The CTTC pages and the entry page show no reserve or
  semáforo level, so there's no `scrape_blood_levels_andalucia`.
- Boundary polygon: mainland Andalucía only (the Ceuta/Melilla and island
  slivers in the source are dropped).

## Not yet researched

- Principado de Asturias
- Illes Balears
- Canarias
- Cantabria
- Extremadura
- Región de Murcia
- Comunidad Foral de Navarra
- La Rioja
