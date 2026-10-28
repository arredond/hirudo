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

### Cantabria
- Fixed points: one spot, the Banco de Sangre y Tejidos del Hospital
  Universitario Marqués de Valdecilla (Santander), listed in the
  "dónde donar" slider on the homepage <https://www.hdsc.org/> — address,
  phone and "Estamos de lunes a viernes de 8:30 a 21:00h" are plain text
  there. Its Google Maps short link (`maps.app.goo.gl`) carries the
  coordinates, resolved with `crawl.resolve_gmaps_coords`, so nothing is
  geocoded. Hours come from the `opening_hours_fijos.json` lookup (the source
  says nothing about public holidays, so none are stated there either).
  The same slider's e-mail and activities slides are ignored.
- Mobile points: **not scraped.** The weekly "Agenda semanal unidad móvil"
  (<https://www.hdsc.org/agenda-semanal-unidad-movil/>) is published only as
  images: the post's `<img>` tags have no alt text, the media-library
  attachments are named generically ("Agenda-Semanal-Unidad-Movil-ilustrado-
  azul-y-rojo-6.png") with no schedule in their descriptions, and there is no
  PDF, iCal, feed or events-API (`tribe/events`, 404) alternative. Reading the
  images would need OCR, which isn't a dependency here. Revisit if the Banco
  starts publishing the agenda as text.
- Blood levels: none. The homepage and the donation page have no
  "niveles de sangre" or semáforo widget.
### Comunidad Foral de Navarra
- Fixed points: ADONA's two spots, one contact page each:
  <https://adona.es/es/contacto-adona/contacto-pamplona> (Banco de Sangre
  de Pamplona) and <https://adona.es/es/contacto-adona/contacto-tudela>
  (Tudela). Address, phone and hours sit in `div.box-services-2` boxes
  keyed by their icon class; the map's `initMap()` carries the centre
  coordinates with decimal commas (`lat: 42,804981957138`), so nothing is
  geocoded. Hours are hand-translated into `opening_hours_fijos.json`,
  keyed by the names we give them (the site only says "Pamplona"/"Tudela").
- Plasma: both spots offer "Dona aféresis" on the booking page
  (<https://adona.es/es/dona-sangre/reservar-cita>, `?aferesis=1` links), so
  both are flagged `plasma` and `sangre`.
- Mobile points ("Unidad móvil", Autohemoteca): <https://adona.es/es/calendario-unidad-movil>
  is a FullCalendar page fed by `https://adona.es/adona/calendars/get.json`
  (needs a unix `start`/`end` window; returns nothing without one). One
  event per stop, titled "TOWN HH:MM - HH:MM" with the venue on the next
  line; some times use dots ("17.00"), and a placeholder entry (".  - ")
  is skipped. Geocoded from venue + town (Geocoding API + Places, best
  score kept), since the feed has no coordinates. The booking page offers
  "Dona aféresis" for the Unidad móvil too, so its stops get `plasma` and
  `sangre` like the fixed spots.
- Blood levels: **none found** on the site (frontend shows the placeholder).

### La Rioja
- Fixed point: the Banco de Sangre at the Hospital San Pedro (Logroño), one
  spot, on <https://www.bancosangrerioja.org/donacion/donde-donar-sangre>.
  Its coordinates are the map marker's JS variable (`var myLatLngBS = {lat,
  lng}`), and its hours are the map legend's "Horario:" line — hand-translated
  into `opening_hours_fijos.json` like the other fixed points.
- Mobile points: the monthly calendar at
  <https://www.bancosangrerioja.org/el-banco-de-sangre/calendario-extracciones>
  (server-rendered; `?f=MM-YYYY`). It publishes only the current and the next
  month, so the ETL asks for those two. Each stop links to its detail page
  `.../colecta?c=<id>`, whose embedded Google Map (`maps?q=<lat>%2C<lng>`)
  gives the exact coordinates. Some stops' maps carry none (`q=%2C`), so
  those are geocoded from their address through the geocoding cache.
- Blood levels: <https://www.bancosangrerioja.org/> "Estado de las reservas",
  one blood-bag image per type whose filename ends in the level
  (`estado-0-neg-2.png`). The page's legend pairs `estado-1` "Dona hoy",
  `-2` "Dona en 2 ó 3 días", `-3` "Dona en tu próxima colecta", mapped to
  red, orange and green (levels 1, 2, 3).
- Plasma (aféresis) is booked by appointment at the Banco
  (<https://www.bancosangrerioja.org/donacion/donacion-aferesis>); the flag is
  left unset, as for the other regions' fixed points.

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

### Principado de Asturias
- Fixed points: <https://donasturias.org/puntos-fijos/> — four centres on one
  page (HUCA in Oviedo, Centro de Salud Puerta de la Villa, Cruz Roja and the
  Asociación de Donantes in Avilés), each with a weekly free-text schedule
  (hand-translated into `opening_hours_fijos.json`, keyed by name) and a
  Google Maps embed. The embed carries the coordinates (`!2d…!3d…` or
  `ll=`), so they're used as-is; nothing is geocoded.
- Mobile points: The Events Calendar REST API,
  <https://donasturias.org/wp-json/tribe/events/v1/events> (from today,
  paginated via `next_rest_url`). One event per town and day; each paragraph
  of its description is one spot ("09.00-14.00 y 16.00-21.00 | **La Arena.**
  C/ …"), so each spot becomes its own row. The calendar also carries the
  fixed centres' own days, titled "PUNTOS FIJOS"; those are skipped since the
  fixed points come from the page. Events have no coordinates, so spots are
  geocoded: a Places search for "venue, town" plus the Geocoding API for the
  address, best score kept (see `scrape_mobile_points_asturias`).
- Blood levels ("Estado de las reservas de hematíes"): eight gauge images on
  the homepage, no legend and no text. The blood type comes from the filename
  (`omas…` = O+, `o-…` = O-, `Amas…` = A+, …); the level is read off the
  image: the needle's angle picks the rim band it points at, and that band's
  colour is the status (red, yellow, green — three levels, like Madrid and
  Castilla y León). The numbers in the filenames are not the level.
- Everything is in Spanish.

### Illes Balears
- Source: Fundació Banc de Sang i Teixits de les Illes Balears,
  <https://www.donasang.org/es_index.php> (server-rendered; the Spanish
  pages are crawled, the Catalan ones are the same data).
- Fixed points: the three centres listed on
  <https://www.donasang.org/on-puc-donar/es_calendari/index.php> (Palma, Mahón,
  Eivissa). Each has a detail page whose map script (`new
  google.maps.LatLng(lat, lng)`) carries its coordinates; no Google Maps link
  is published. Palma's hours are prose on the listing, hand-translated into
  `opening_hours_fijos.json`; Mahón and Eivissa publish only "Consultar
  calendario campañas", so they have no lookup entry and log a warning.
- Mobile points: the day calendar at
  <https://www.donasang.org/on-puc-donar/es_calendari/punts.php>, paged
  `?PAGE=N` (three event days per page, 18 pages at the time of writing). The
  ETL reads pages in order until one passes the end of next month, so the
  window is the same as La Rioja's. Each entry has its own detail page with
  the spot's coordinates, fetched once per spot (name, town and address), since
  the same venue recurs on each day with a new id. Entries named "AFERESI /
  AFERESIS" are apheresis sessions and are flagged plasma (not sangre).
- Blood levels: the homepage's "Niveles de la reserva" grid, one bag image per
  type (`/media/comu/reserves/<digit>_<type>.jpg`). The digit is the bag's
  fill, read against the legend's own icons: 1 is full ("Dona en la próxima
  campaña", green), 2 half ("Dona en 2 ó 3 días", orange), 3 nearly empty
  ("Dona urgentemente", red). This runs the opposite way to La Rioja's digits,
  so the mapping is per region.

## Blocked

### Región de Murcia
- Source: <https://www.murciasalud.es/web/centro-regional-de-hemodonacion>
  (blood levels and "Fijos" tab) and `.../calendario-de-colectas` (mobile).
  Every spot links a Google Map, so no geocoding would be needed.
- **Blocked (2026-10-28):** murciasalud.es serves a Radware bot-check captcha
  to every non-browser request, so the Cloud Run job can't fetch it. Not
  worked around. Revisit if the CRH offers a feed/open-data export or lifts
  the check for these pages.

### Extremadura
- Source: <https://saludextremadura.ses.es/bancodesangre/> — reachable
  (200), but a client-rendered SPA: the server HTML is an empty shell and
  `build/bundle.js` names no data endpoints (`/bancodesangre/rest/` is 403,
  guessed paths return the shell). Next step: load the page in a browser and
  capture its XHR requests to find the JSON API it uses.

## Not yet researched

- Canarias
