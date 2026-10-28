"""Crawl Banco de Sangre de La Rioja (bancosangrerioja.org) and retrieve fixed
and mobile blood donation spots and blood-reserve levels.

It's a server-rendered Joomla site. The one fixed spot (the Banco at the
Hospital San Pedro) has its hours in a map legend on the "¿Dónde puedo donar
sangre?" page, and its exact coordinates in the map's marker variable — no
geocoding needed.

Mobile stops ("extracciones") are listed on the monthly calendar, which
publishes the current month and the next one (?f=MM-YYYY). Each stop links to
its own detail page, whose embedded Google Map carries the stop's exact
coordinates, so those are read from there rather than geocoded.

Blood levels are one blood-bag image per type on the homepage; the image's
filename ends in the level (1-3), which the page's own legend explains (see
BLOOD_LEVEL_STATUS).
"""

import datetime
import re
import urllib.parse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from utils.crawl import comunidad_valenciana, crawl

URL_BASE = "https://www.bancosangrerioja.org/"
URL_FIXED_POINTS = urllib.parse.urljoin(URL_BASE, "donacion/donde-donar-sangre")
URL_CALENDAR = urllib.parse.urljoin(
    URL_BASE, "el-banco-de-sangre/calendario-extracciones"
)

# The Banco's map marker on the fixed-points page:
#   var myLatLngBS = {lat: 42.451333, lng: -2.427574};
BANCO_COORDS_RE = re.compile(
    r"var\s+myLatLngBS\s*=\s*\{\s*lat:\s*(-?\d+(?:\.\d+)?),\s*lng:\s*(-?\d+(?:\.\d+)?)\s*\}"
)
BANCO_NAME = "Banco de Sangre del Hospital San Pedro"
BANCO_LOCALIDAD = "Logroño"
BANCO_DIRECCION = "Hospital San Pedro"

# Calendar cells link each stop to its detail page: ".../colecta?c=4992".
COLECTA_HREF_RE = re.compile(r"colecta\?c=\d+")

# "10:00 -13:45" (the calendar's own spacing varies).
TIME_RANGE_RE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")

# The stop detail page's embedded map: maps?q=42.466478%2C-2.432242&...
STOP_MAP_RE = re.compile(r"maps\?q=(-?\d+(?:\.\d+)?)(?:%2C|,)(-?\d+(?:\.\d+)?)")

# Blood-bag image filename ("estado-0-neg-2.png") -> blood type and the level
# its last digit gives. The digit is the status icon the page's own legend
# pairs with each label (estado-1 "Dona hoy" ... estado-3 "Dona en tu próxima
# colecta"); 1 = most urgent, so level 3 is the fullest bag, green.
BLOOD_LEVEL_IMAGE_RE = re.compile(r"estado-(AB|A|B|0)-(pos|neg)-(\d)\.png$")
BLOOD_LEVEL_STATUS = {
    "1": ("red", 1, "Dona hoy"),
    "2": ("orange", 2, "Dona en 2 ó 3 días"),
    "3": ("green", 3, "Dona en tu próxima colecta"),
}

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"
# The server sends its leaf certificate without the Sectigo DV R36
# intermediate, so requests can't build the chain on its own (see
# crawl.ca_bundle_with).
SESSION.verify = crawl.ca_bundle_with(
    "sectigo_public_server_authentication_ca_dv_r36.pem"
)


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace (the source doubles some spaces)."""
    return " ".join(text.split())


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape the Banco de Sangre, the one permanent spot.

    Coordinates come from the map marker's JS variable; the hours from the
    map legend's "Horario:" line.
    """
    html = SESSION.get(URL_FIXED_POINTS).text
    soup = BeautifulSoup(html, features="lxml")
    coords = BANCO_COORDS_RE.search(html)
    legend = normalize_whitespace(soup.find(id="leyendaMapaBS").get_text(" "))
    horario = legend.split("Horario:", 1)[1].strip()
    return pd.DataFrame(
        [
            {
                "name": BANCO_NAME,
                "localidad": BANCO_LOCALIDAD,
                "direccion": BANCO_DIRECCION,
                "latitude": float(coords.group(1)),
                "longitude": float(coords.group(2)),
                "horario": horario,
                "url": URL_FIXED_POINTS,
            }
        ]
    )


def parse_stop(link, fecha: str) -> dict | None:
    """Flatten one calendar entry into a mobile point row.

    The entry reads, in order: the stop's name (<strong>), "HH:MM -HH:MM",
    and then its address lines (none for some stops).
    """
    texts = list(link.stripped_strings)
    if len(texts) < 2:
        return None
    name, hours_text, *address_lines = texts
    hours = TIME_RANGE_RE.search(hours_text)
    if not hours:
        return None
    open_h, open_m, close_h, close_m = hours.groups()
    lugar = normalize_whitespace(name)
    return {
        "lugar": lugar,
        "localidad": normalize_whitespace(lugar.split(" - ")[0]),
        "direccion": normalize_whitespace(" ".join(address_lines)) or None,
        "fecha": fecha,
        "horario": f"{int(open_h):02d}:{open_m}-{int(close_h):02d}:{close_m}",
        "url": urllib.parse.urljoin(URL_BASE, link["href"]),
    }


def parse_calendar(
    html: str, month_start: datetime.date, today: datetime.date
) -> list[dict]:
    """Parse one month's calendar grid into mobile stop rows, from today on.

    Each day cell holds its day number as its first text, then one link per
    stop. The month comes from the request (month_start), not the page's
    heading, so no Spanish month names need parsing.
    """
    soup = BeautifulSoup(html, features="lxml")
    stops = []
    for cell in soup.select("#calCuerpo div.col"):
        day = cell.find(string=True, recursive=False)
        if day is None or not day.strip().isdigit():
            continue
        date = month_start.replace(day=int(day.strip()))
        if date < today:
            continue
        fecha = date.strftime("%d/%m/%Y")
        for link in cell.find_all("a", href=COLECTA_HREF_RE):
            stop = parse_stop(link, fecha)
            if stop:
                stops.append(stop)
    return stops


def fetch_stop_coordinates(url: str) -> tuple[float | None, float | None]:
    """Read a stop's exact coordinates from its detail page's embedded map.

    A map pinned at 0,0 (seen on some stops) counts as having none.
    """
    match = STOP_MAP_RE.search(SESSION.get(url).text)
    if not match:
        return (None, None)
    latitude, longitude = float(match.group(1)), float(match.group(2))
    if latitude == 0 and longitude == 0:
        return (None, None)
    return (latitude, longitude)


def scrape_mobile_points(today: datetime.date | None = None) -> pd.DataFrame:
    """Scrape every mobile stop from today to the end of next month.

    The calendar publishes only the current and the next month. A stop
    listed twice (same URL) is kept once.
    """
    today = today or comunidad_valenciana.madrid_today()
    first_of_month = today.replace(day=1)
    next_month = (first_of_month + datetime.timedelta(days=32)).replace(day=1)
    stops = []
    for month_start in [first_of_month, next_month]:
        response = SESSION.get(
            URL_CALENDAR, params={"f": month_start.strftime("%m-%Y")}
        )
        stops.extend(parse_calendar(response.text, month_start, today))
    columns = ["lugar", "localidad", "direccion", "fecha", "horario", "url"]
    df = pd.DataFrame(stops, columns=columns).drop_duplicates(
        subset="url", ignore_index=True
    )
    coords = df["url"].apply(fetch_stop_coordinates)
    df[["latitude", "longitude"]] = pd.DataFrame(
        coords.tolist(), index=df.index, columns=["latitude", "longitude"]
    )
    return df


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape the "Estado de las reservas" blood-bag images on the homepage."""
    soup = BeautifulSoup(SESSION.get(URL_BASE).text, features="lxml")
    blood_levels = []
    for img in soup.select(".estadosReservas img"):
        match = BLOOD_LEVEL_IMAGE_RE.search(img["src"])
        if not match:
            continue
        blood_group, rhesus, level_digit = match.groups()
        blood_type = blood_group + ("+" if rhesus == "pos" else "-")
        status, level, label = BLOOD_LEVEL_STATUS[level_digit]
        blood_levels.append(
            {"blood_type": blood_type, "status": status, "level": level, "label": label}
        )
    return pd.DataFrame(
        blood_levels, columns=["blood_type", "status", "level", "label"]
    )
