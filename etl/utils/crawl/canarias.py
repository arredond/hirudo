"""Crawl the Servicio Canario de la Salud's donation-point finder
(www3.gobiernodecanarias.org/sanidad/scs/PuntosHemodonacion) and retrieve
fixed and mobile ("itinerantes") donation points.

It's a PrimeFaces (JSF) app. The search form posts to index.xhtml, which
redirects to results.xhtml: a DataTable of ten rows a page, paginated on the
server. A search with no island or municipality filter lists everything
(fixed: 17 spots, mobile: ~76 stops at the time of writing), so one search per
campaign type is paged through with PrimeFaces' own paginator request (the one
its page sends when you click "next"), and no island or municipality filter is
needed.

Each row's Google Maps link carries the point's coordinates, so nothing is
geocoded unless a row has no usable link (see geocode in main.py). Blood
levels are not published by the Canarian blood bank (ICHH) in a scrapable form,
so this module does not scrape any.
"""

import datetime
import re
import urllib.parse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from utils.crawl import crawl

URL_BASE = "https://www3.gobiernodecanarias.org/sanidad/scs/PuntosHemodonacion/"
URL_SEARCH = urllib.parse.urljoin(URL_BASE, "index.xhtml")
URL_RESULTS = urllib.parse.urljoin(URL_BASE, "results.xhtml")

CAMPAIGN_FIXED = "RegularCollections"
CAMPAIGN_MOBILE = "ItinerantCollections"

ROWS_PER_PAGE = 10

# JSF state, the results summary's total and the paginator's partial response.
VIEW_STATE_RE = re.compile(r'name="javax.faces.ViewState"[^>]*value="([^"]+)"')
XML_DECLARATION_RE = re.compile(r"^\s*<\?xml[^>]*\?>")
TOTAL_RE = re.compile(r"Colectas encontradas</span>\s*</div>\s*<div[^>]*>\s*(\d+)")
PARTIAL_HEADERS = {
    "Faces-Request": "partial/ajax",
    "X-Requested-With": "XMLHttpRequest",
}
TABLE_UPDATE_RE = re.compile(
    r'<update id="results:dataView"><!\[CDATA\[(.*?)\]\]></update>', re.DOTALL
)
VIEW_STATE_UPDATE_RE = re.compile(
    r'<update id="[^"]*ViewState[^"]*"><!\[CDATA\[([^\]]+)\]\]>'
)

# Google Maps links in the MAPA column: "...maps?f=q&hl=es&q=28.081056%2C+-15.417814".
# An empty pair ("q=%2C") is a point with no location, handled as missing.
MAP_LINK_RE = re.compile(r"q=(-?\d+(?:\.\d+)?)(?:%2C|,)\+*(-?\d+(?:\.\d+)?)")

# The Canary Islands' bounding box, to reject a link pinned somewhere else
# (e.g. a 0,0 placeholder).
CANARIAS_LAT_RANGE = (27.0, 29.6)
CANARIAS_LON_RANGE = (-18.3, -13.3)

# Mobile dates are "28-oct-2026" (Spanish three-letter month abbreviations).
FECHA_RE = re.compile(r"^(\d{1,2})-([a-záéíóú]{3})-(\d{4})$")
MONTH_NUMBERS = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"


def canarias_today() -> datetime.date:
    """Today's date in the Canaries (Atlantic/Canary, an hour behind Madrid).

    The ETL runs on Cloud Run in UTC; a Madrid date would count a stop of the
    day before as still upcoming for the first hour of each Canarian day.
    """
    return pd.Timestamp.now(tz="Atlantic/Canary").date()


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace (the source doubles some spaces)."""
    return " ".join(text.split())


def parse_fecha(fecha: str) -> datetime.date | None:
    """Parse a "28-oct-2026" date from the mobile table."""
    match = FECHA_RE.match(fecha.strip().lower())
    if not match:
        return None
    day, month, year = match.groups()
    return datetime.date(int(year), MONTH_NUMBERS[month], int(day))


def coordinates_from_link(href: str | None) -> tuple[float | None, float | None]:
    """Read a row's coordinates from its Google Maps link.

    A missing or empty pair ("q=%2C"), or one outside the Canary Islands,
    counts as having none.
    """
    match = MAP_LINK_RE.search(href or "")
    if not match:
        return (None, None)
    latitude, longitude = float(match.group(1)), float(match.group(2))
    lat_min, lat_max = CANARIAS_LAT_RANGE
    lon_min, lon_max = CANARIAS_LON_RANGE
    if not (lat_min <= latitude <= lat_max and lon_min <= longitude <= lon_max):
        return (None, None)
    return (latitude, longitude)


def parse_rows(table_html: str, campaign: str) -> list[dict]:
    """Flatten the DataTable's rows into dicts, one per donation point.

    Fixed points' columns are ISLA, MUNICIPIO, UBICACIÓN, HORARIO, MAPA; mobile
    stops add FECHA in front. Each row's island is dropped (the municipality
    is enough to locate a point).
    """
    # The results page is XHTML, so its XML declaration is dropped first (it
    # only makes BeautifulSoup warn that the document looks like XML).
    table_html = XML_DECLARATION_RE.sub("", table_html, count=1)
    soup = BeautifulSoup(table_html, features="lxml")
    body = soup.find("tbody", id=re.compile(r"dataView_data$"))
    if body is None:
        return []
    rows = []
    for tr in body.find_all("tr"):
        cells = tr.find_all("td")
        link = cells[-1].find("a")
        texts = [cell.get_text("\n", strip=True) for cell in cells[:-1]]
        if campaign == CAMPAIGN_MOBILE:
            fecha, _, municipio, ubicacion, horario = texts
        else:
            fecha = None
            _, municipio, ubicacion, horario = texts
        rows.append(
            {
                "fecha": fecha,
                "localidad": municipio,
                "ubicacion": ubicacion,
                "horario": horario,
                "map_href": link["href"] if link else None,
            }
        )
    return rows


def search_results_page(campaign: str) -> tuple[str, str]:
    """Run an unfiltered search and return (results HTML, ViewState)."""
    home = SESSION.get(URL_SEARCH).text
    view_state = VIEW_STATE_RE.search(home).group(1)
    SESSION.post(
        URL_SEARCH,
        data={
            "form": "form",
            "form:type_input": campaign,
            "form:island_input": "",
            "form:municipality_input": "",
            "javax.faces.ViewState": view_state,
            "form:j_idt35": "form:j_idt35",
        },
        allow_redirects=False,
    )
    results = SESSION.get(URL_RESULTS).text
    return results, VIEW_STATE_RE.search(results).group(1)


def fetch_page(first: int, view_state: str) -> tuple[str, str]:
    """Request one page of the open results, as the paginator does.

    Returns the refreshed table HTML and ViewState from the partial response.
    """
    response = SESSION.post(
        URL_RESULTS,
        data={
            "javax.faces.partial.ajax": "true",
            "javax.faces.source": "results:dataView",
            "javax.faces.partial.execute": "results:dataView",
            "javax.faces.partial.render": "results:dataView",
            "javax.faces.behavior.event": "page",
            "results:dataView_pagination": "true",
            "results:dataView_first": str(first),
            "results:dataView_rows": str(ROWS_PER_PAGE),
            "results:dataView_skipChildren": "true",
            "results:dataView_encodeFeature": "true",
            "results:dataView_fullUpdate": "true",
            "results": "results",
            "javax.faces.ViewState": view_state,
        },
        headers=PARTIAL_HEADERS,
    )
    table = TABLE_UPDATE_RE.search(response.text).group(1)
    new_view_state = VIEW_STATE_UPDATE_RE.search(response.text)
    return table, new_view_state.group(1) if new_view_state else view_state


def fetch_all_rows(campaign: str) -> list[dict]:
    """Every row of an unfiltered search, across all pages."""
    results, view_state = search_results_page(campaign)
    total_match = TOTAL_RE.search(results)
    total = int(total_match.group(1)) if total_match else 0
    rows = parse_rows(results, campaign)
    while len(rows) < total:
        table, view_state = fetch_page(len(rows), view_state)
        page_rows = parse_rows(table, campaign)
        if not page_rows:
            break
        rows.extend(page_rows)
    if len(rows) != total:
        raise ValueError(f"Expected {total} {campaign} rows, got {len(rows)}")
    return rows


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape the region's fixed donation points (the "Colectas Fijas" campaign)."""
    rows = fetch_all_rows(CAMPAIGN_FIXED)
    records = []
    for row in rows:
        lines = [line for line in row["ubicacion"].split("\n") if line.strip()]
        latitude, longitude = coordinates_from_link(row["map_href"])
        records.append(
            {
                "name": crawl.title_name(normalize_whitespace(lines[0])),
                "localidad": crawl.title_name(normalize_whitespace(row["localidad"])),
                "direccion": crawl.title_name(normalize_whitespace(" ".join(lines[1:])))
                or None,
                "horario": normalize_whitespace(row["horario"]),
                "latitude": latitude,
                "longitude": longitude,
                "url": URL_BASE,
            }
        )
    return pd.DataFrame(records)


def scrape_mobile_points(today: datetime.date | None = None) -> pd.DataFrame:
    """Scrape the region's mobile ("itinerantes") stops, from today on."""
    today = today or canarias_today()
    rows = fetch_all_rows(CAMPAIGN_MOBILE)
    records = []
    for row in rows:
        date = parse_fecha(row["fecha"])
        if date is None or date < today:
            continue
        lines = [line for line in row["ubicacion"].split("\n") if line.strip()]
        latitude, longitude = coordinates_from_link(row["map_href"])
        records.append(
            {
                "lugar": crawl.title_name(normalize_whitespace(lines[0])),
                "localidad": crawl.title_name(normalize_whitespace(row["localidad"])),
                "direccion": crawl.title_name(normalize_whitespace(" ".join(lines[1:])))
                or None,
                "fecha": date.strftime("%d/%m/%Y"),
                "horario": normalize_whitespace(row["horario"]),
                "url": URL_BASE,
                "latitude": latitude,
                "longitude": longitude,
            }
        )
    return pd.DataFrame(records)
