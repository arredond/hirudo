"""Crawl the Fundació Banc de Sang i Teixits de les Illes Balears (donasang.org).

It's a server-rendered site; this crawls its Spanish pages. Three sources
feed the ETL:

- Fixed points: the three donation centres (Palma, Mahón, Eivissa) listed on
  the "¿Dónde puedo donar?" page. Each has its own detail page whose map
  script carries the centre's exact coordinates, so nothing is geocoded.
- Mobile points: the day-by-day calendar (punts.php), three event days per
  page. Each entry links to its own detail page, which carries the spot's
  coordinates the same way.
- Blood levels: one bag image per blood type on the homepage. The image's
  filename ends in the level digit, mapped to a status in BLOOD_LEVEL_STATUS.
"""

import datetime
import re
import urllib.parse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from utils.crawl import comunidad_valenciana

URL_BASE = "https://www.donasang.org/"
URL_HOME = urllib.parse.urljoin(URL_BASE, "es_index.php")
URL_FIXED_POINTS = urllib.parse.urljoin(URL_BASE, "on-puc-donar/es_calendari/index.php")
URL_CALENDAR = urllib.parse.urljoin(URL_BASE, "on-puc-donar/es_calendari/punts.php")

# A detail page's map script: `var myLatlng = new google.maps.LatLng(39.58, 2.65);`
# The first such line is the spot's own marker.
DETAIL_LATLNG_RE = re.compile(
    r"var\s+myLatlng\s*=\s*new\s+google\.maps\.LatLng\(\s*"
    r"(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)"
)

# A calendar day heading, "Miercoles, 28 de Octubre de 2026" (the weekday is
# skipped by the search).
HEADING_DATE_RE = re.compile(r"(\d{1,2}) de (\w+) de (\d{4})")
SPANISH_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

# "de 08:00h. a 20:30h." (the calendar's punctuation varies).
HOURS_RE = re.compile(r"(\d{1,2}):(\d{2})\s*h?\.?\s*(?:a|-)\s*(\d{1,2}):(\d{2})")

# Aféresis sessions (apheresis, i.e. plasma) are named "AFERESI / AFERESIS ...".
APHERESIS_RE = re.compile(r"AFERESI", re.IGNORECASE)

# Blood-bag image filename ("3_O-.jpg") -> level digit and blood type. The
# digit is the bag's fill, read against the legend's own icons: 1 is a full
# bag ("Dona en la próxima campaña", green), 2 half full ("Dona en 2 ó 3
# días", orange), 3 nearly empty ("Dona urgentemente", red). This is the
# reverse of the other regions' numbering, so the mapping below converts it
# to the shared vocabulary, where level 1 is the most urgent.
BLOOD_LEVEL_IMAGE_RE = re.compile(r"/(\d)_(AB|A|B|O)([+-])\.jpg$")
BLOOD_LEVEL_STATUS = {
    "1": ("green", 3, "Dona en la próxima campaña"),
    "2": ("orange", 2, "Dona en 2 ó 3 días"),
    "3": ("red", 1, "Dona urgentemente"),
}

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace, including the non-breaking spaces the source uses."""
    return " ".join(text.split())


def parse_spanish_date(text: str) -> datetime.date | None:
    """Parse a calendar heading such as "Miercoles, 28 de Octubre de 2026"."""
    match = HEADING_DATE_RE.search(normalize_whitespace(text))
    if not match:
        return None
    day, month_name, year = match.groups()
    month = SPANISH_MONTHS.get(month_name.lower())
    if month is None:
        return None
    return datetime.date(int(year), month, int(day))


def normalize_hours(text: str) -> str | None:
    """Turn "de 08:00h. a 20:30h." into "08:00-20:30" (None if there's no range)."""
    match = HOURS_RE.search(normalize_whitespace(text))
    if not match:
        return None
    open_h, open_m, close_h, close_m = match.groups()
    return f"{int(open_h):02d}:{open_m}-{int(close_h):02d}:{close_m}"


def fetch_coordinates(url: str) -> tuple[float | None, float | None]:
    """Read a spot's exact coordinates from its detail page's map script.

    A map pinned at 0,0 counts as having none.
    """
    match = DETAIL_LATLNG_RE.search(SESSION.get(url).text)
    if not match:
        return (None, None)
    latitude, longitude = float(match.group(1)), float(match.group(2))
    if latitude == 0 and longitude == 0:
        return (None, None)
    return (latitude, longitude)


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape the three fixed donation centres listed on the fixed-points page.

    The listing gives each centre's name, address and, for Palma, its hours
    as prose ("Horario de donaciones ..."). Mahón and Eivissa say "Consultar
    calendario campañas" instead, so their horario is None; their hours are
    hand-built in opening_hours_fijos.json.
    """
    soup = BeautifulSoup(SESSION.get(URL_FIXED_POINTS).text, features="lxml")
    rows = []
    for item in soup.select("#centresFixos ul li"):
        link = item.find("h4").find("a")
        name = normalize_whitespace(link.get_text())
        url = urllib.parse.urljoin(URL_BASE, link["href"])
        lines = [
            normalize_whitespace(line)
            for line in item.find("p").get_text("\n").split("\n")
            if line.strip()
        ]
        horario = None
        for line in lines:
            if line.startswith("Horario de donaciones"):
                horario = (
                    line.removeprefix("Horario de donaciones")
                    .split("Cómo llegar", 1)[0]
                    .strip()
                )
        latitude, longitude = fetch_coordinates(url)
        rows.append(
            {
                "name": name,
                # "Palma (Mallorca). Banco de sangre" -> "Palma"
                "localidad": re.split(r"[.(]", name, maxsplit=1)[0].strip(),
                "direccion": lines[0],
                "horario": horario or None,
                "latitude": latitude,
                "longitude": longitude,
                "url": url,
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "name",
            "localidad",
            "direccion",
            "horario",
            "latitude",
            "longitude",
            "url",
        ],
    )


def parse_stop(item, date: datetime.date) -> dict:
    """Flatten one calendar entry into a mobile point row.

    An entry gives the town as its link text (<h3>), the spot's name in bold,
    its address lines and its hours ("de 08:00h. a 20:30h.").
    """
    link = item.find("h3").find("a")
    lugar = normalize_whitespace(item.find("p").get_text())
    address = item.find("p", class_="subtitle")
    return {
        "lugar": lugar,
        "localidad": normalize_whitespace(link.get_text()),
        "direccion": (
            normalize_whitespace(" ".join(address.stripped_strings))
            if address
            else None
        ),
        "fecha": date.strftime("%d/%m/%Y"),
        "horario": normalize_hours(item.find("span", class_="hores").get_text()),
        "url": urllib.parse.urljoin(URL_BASE, link["href"]),
        "aferesis": bool(APHERESIS_RE.search(lugar)),
    }


def parse_calendar(html: str) -> list[tuple[datetime.date, list[dict]]]:
    """Parse one page of the day calendar into (date, stops) pairs, in page order."""
    soup = BeautifulSoup(html, features="lxml")
    days = []
    for day in soup.select("#colPunts #dies > li"):
        date = parse_spanish_date(day.find("h2").get_text())
        if date is None:
            continue
        stops = [parse_stop(item, date) for item in day.select("ul.llistatPobles > li")]
        days.append((date, stops))
    return days


def page_count(html: str) -> int:
    """Total number of calendar pages the page's pager reports."""
    total = BeautifulSoup(html, features="lxml").select_one("#pagTotal")
    return int(total.get_text()) if total else 1


def scrape_mobile_points(today: datetime.date | None = None) -> pd.DataFrame:
    """Scrape the mobile stops from today to the end of next month.

    The calendar is paged in date order (punts.php?PAGE=N), so pages are
    fetched until one reaches past the window. Each stop's coordinates come
    from its detail page. Entries for the same spot (same name, town and
    address) recur on different days with different detail pages, so the
    page is fetched once per spot.
    """
    today = today or comunidad_valenciana.madrid_today()
    first_of_month = today.replace(day=1)
    next_month = (first_of_month + datetime.timedelta(days=32)).replace(day=1)
    window_end = (next_month + datetime.timedelta(days=32)).replace(day=1) - (
        datetime.timedelta(days=1)
    )

    stops = []
    page = 1
    while True:
        html = SESSION.get(URL_CALENDAR, params={"PAGE": page}).text
        days = parse_calendar(html)
        for date, day_stops in days:
            if today <= date <= window_end:
                stops.extend(day_stops)
        if page >= page_count(html) or not days or days[-1][0] > window_end:
            break
        page += 1

    columns = ["lugar", "localidad", "direccion", "fecha", "horario", "url", "aferesis"]
    df = pd.DataFrame(stops, columns=columns).drop_duplicates(
        subset="url", ignore_index=True
    )
    if df.empty:
        return df.assign(latitude=None, longitude=None)

    coordinates_by_spot = {}
    coordinates = []
    for row in df.itertuples():
        spot = (row.lugar, row.localidad, row.direccion)
        if spot not in coordinates_by_spot:
            coordinates_by_spot[spot] = fetch_coordinates(row.url)
        coordinates.append(coordinates_by_spot[spot])
    df[["latitude", "longitude"]] = pd.DataFrame(
        coordinates, index=df.index, columns=["latitude", "longitude"]
    )
    return df


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape the homepage's "Niveles de la reserva" blood-bag images."""
    soup = BeautifulSoup(SESSION.get(URL_HOME).text, features="lxml")
    blood_levels = []
    for img in soup.select("#nivells li img"):
        match = BLOOD_LEVEL_IMAGE_RE.search(img["src"])
        if not match:
            continue
        level_digit, blood_group, rhesus = match.groups()
        status, level, label = BLOOD_LEVEL_STATUS[level_digit]
        blood_levels.append(
            {
                "blood_type": blood_group + rhesus,
                "status": status,
                "level": level,
                "label": label,
            }
        )
    return pd.DataFrame(
        blood_levels, columns=["blood_type", "status", "level", "label"]
    )
