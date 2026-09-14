"""Crawl Castilla-La Mancha pages and retrieve fixed and mobile blood donation spots.

No blood-levels ("niveles de sangre") page has been found for this region —
scrape_blood_levels() here simply doesn't exist; main.py handles a region
with no blood-levels source by just not calling one (see REGION_CLM there).
"""

import re
import urllib.parse
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL_BASE = "https://sanidad.castillalamancha.es/"
URL_FIXED_POINTS = urllib.parse.urljoin(
    URL_BASE, "ciudadanos/hazte-donante-sangre/puntos-fijos-de-donacion"
)
URL_MOBILE_POINTS_BASE = urllib.parse.urljoin(
    URL_BASE, "ciudadanos/hazte-donante-sangre/colectas-donantes-de-sangre/"
)

# The mobile-points index page lists one link per province; hardcoded here
# since, like Castilla y León's province list, it's small and effectively
# static.
PROVINCES = ["albacete", "ciudad-real", "cuenca", "guadalajara", "toledo"]

MONTH_NAME_TO_NUM = {
    "enero": "01",
    "febrero": "02",
    "marzo": "03",
    "abril": "04",
    "mayo": "05",
    "junio": "06",
    "julio": "07",
    "agosto": "08",
    "septiembre": "09",
    "octubre": "10",
    "noviembre": "11",
    "diciembre": "12",
}
# "Viernes, 25 Septiembre, 2026" — weekday name, day, Spanish month name, year.
CLM_DATE_RE = re.compile(r"(\d{1,2})\s+([A-Za-zÁÉÍÓÚáéíóú]+),\s*(\d{4})")

# Mobile points' "Localidad" moves a leading article to the end for
# alphabetical sorting, e.g. "PUEBLA DE ALMORADIEL,LA" instead of "LA PUEBLA
# DE ALMORADIEL".
LOCALITY_ARTICLE_SUFFIX_RE = re.compile(r"^(.+),\s*(LA|EL|LOS|LAS)$", re.IGNORECASE)

SESSION = requests.Session()


def province_url(province: str) -> str:
    """Build the mobile-points page URL for a province slug."""
    return urllib.parse.urljoin(URL_MOBILE_POINTS_BASE, province)


def clean_locality(locality: str) -> str:
    """Un-invert a locality's trailing sorting article and title-case it.

    e.g. "PUEBLA DE ALMORADIEL,LA" -> "La Puebla De Almoradiel".
    """
    match = LOCALITY_ARTICLE_SUFFIX_RE.match(locality)
    if match:
        name, article = match.groups()
        locality = f"{article} {name}"
    return locality.title()


def parse_clm_date(dia_text: str) -> str | None:
    """Convert "Viernes, 25 Septiembre, 2026" to "25/09/2026".

    Returns None (rather than raising) on an unrecognized month name, so a
    single bad row logs a warning downstream instead of failing the scrape.
    """
    match = CLM_DATE_RE.search(dia_text)
    if not match:
        return None
    day, month_name, year = match.groups()
    month = MONTH_NAME_TO_NUM.get(month_name.lower())
    if not month:
        return None
    return f"{int(day):02d}/{month}/{year}"


def parse_fixed_points(soup: BeautifulSoup) -> list[dict]:
    """Parse the fixed-points page's Drupal Views accordion rows.

    Each row's address text mixes the center's name into the same sentence
    as its street address (e.g. "Hospital Mancha Centro. Avenida de la
    Constitución.") with no reliable separator — Spanish addresses are full
    of their own mid-sentence abbreviation periods ("C/.", "s/n.", "Ntra.",
    "Avda.") that make splitting that apart unreliable. So the accordion's
    own locality heading is used as the point's name instead (suffixed to
    disambiguate the few localities — e.g. Toledo — with more than one
    point), and the full address text is kept as-is in "direccion".
    """
    rows = [
        row
        for row in soup.find_all("div", class_="views-row")
        if row.find("div", class_="views-accordion-header")
    ]

    points = []
    locality_counts: dict[str, int] = {}
    for row in rows:
        locality = row.find("div", class_="views-accordion-header").get_text(strip=True)
        locality_counts[locality] = locality_counts.get(locality, 0) + 1

        direccion_field = row.find("div", class_="views-field-field-direccion")
        direccion = None
        if direccion_field and direccion_field.find("p"):
            direccion = (
                direccion_field.find("p")
                .get_text(" ", strip=True)
                .removeprefix("Dirección:")
                .strip()
            )

        horario_lines = []
        body_field = row.find("div", class_="views-field-body")
        if body_field:
            # The first <p> is just the "Horario" label; later ones are
            # occasionally contact info (WhatsApp/Email/Web) rather than a
            # schedule line, which is filtered out here.
            for p in body_field.find_all("p")[1:]:
                text = p.get_text(" ", strip=True)
                if text and not text.startswith(("WhatsApp", "Email", "Web")):
                    horario_lines.append(text)

        telefono = None
        telefono_field = row.find("div", class_="views-field-field-telefonos-contacto")
        if telefono_field and telefono_field.find("p"):
            telefono = (
                telefono_field.find("p")
                .get_text(" ", strip=True)
                .removeprefix("Teléfono:")
                .strip()
            )

        points.append(
            {
                "locality": locality,
                "direccion": direccion,
                "horario": "; ".join(horario_lines),
                "telefono": telefono,
            }
        )

    seen: dict[str, int] = {}
    for point in points:
        locality = point.pop("locality")
        point["localidad"] = locality
        if locality_counts[locality] > 1:
            seen[locality] = seen.get(locality, 0) + 1
            point["name"] = f"{locality} ({seen[locality]})"
        else:
            point["name"] = locality

    return points


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape every fixed donation point (a single page, no pagination)."""
    html = SESSION.get(URL_FIXED_POINTS).text
    soup = BeautifulSoup(html, features="lxml")
    points = parse_fixed_points(soup)
    for point in points:
        point["url"] = URL_FIXED_POINTS
    return pd.DataFrame(points)


def scrape_mobile_points_province(province: str) -> pd.DataFrame:
    """Scrape one province's mobile points, following pagination to the end."""
    page_frames = []
    url = province_url(province)
    while url:
        html = SESSION.get(url).text
        soup = BeautifulSoup(html, features="lxml")
        table = soup.find("table", class_="views-table")
        if table:
            df = pd.read_html(StringIO(str(table)))[0]
            page_frames.append(df)

        next_link = soup.find("li", class_="pager-next")
        url = (
            urllib.parse.urljoin(url, next_link.find("a")["href"])
            if next_link and next_link.find("a")
            else None
        )

    if not page_frames:
        return pd.DataFrame()
    df = pd.concat(page_frames, ignore_index=True)
    df["province"] = province
    return df


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and return all mobile donation points as a DataFrame."""
    province_frames = [
        scrape_mobile_points_province(province) for province in PROVINCES
    ]
    province_frames = [df for df in province_frames if not df.empty]
    return pd.concat(province_frames, ignore_index=True)
