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

## Not yet researched

- Andalucía
- Aragón
- Principado de Asturias
- Illes Balears
- Canarias
- Cantabria
- Cataluña
- Comunidad Valenciana
- Extremadura
- Galicia
- Región de Murcia
- Comunidad Foral de Navarra
- País Vasco
- La Rioja
