"""Crawl the Centro Regional de Hemodonación de Murcia (murciasalud.es) and
retrieve fixed and mobile blood donation spots and blood-reserve levels.

It's a server-rendered Liferay site behind Radware Bot Manager, which answers
plain HTTP clients (requests, curl) with a captcha page on
validate.perfdrive.com, whatever their User-Agent. curl_cffi, which makes the
TLS handshake look like Chrome's, gets the real pages, so this module fetches
with it instead of the shared requests session. The site's robots.txt allows
crawling with a 10-second crawl delay, which fetch_page honours; the homepage
is fetched once per run and shared by the fixed points and the blood levels.

- Homepage: the blood levels ("Niveles de reserva") and the "Fijos" tab, four
  spots (two of which also appear in the calendar; see
  FIXED_POINTS_IN_CALENDAR), each with its phone, its hours as free text and a
  "Localización" popup whose Google Maps embed carries its coordinates
  ("!2d<lon>!3d<lat>").
- Calendar ("calendario-de-colectas"): about a month of mobile stops, grouped
  by day. Each stop's "Ver plano" popup is an iframe whose lazy-loaded
  data-src ("maps?q=<lat>,<lon>") carries its coordinates.

Every point comes with coordinates, so nothing is geocoded.
"""

import datetime
import logging
import re
import time
import unicodedata
import urllib.parse

import pandas as pd
from bs4 import BeautifulSoup, Tag
from curl_cffi import requests as curl_requests
from utils.crawl import comunidad_valenciana, crawl

log = logging.getLogger(__name__)

URL_BASE = "https://www.murciasalud.es/web/centro-regional-de-hemodonacion"
URL_CALENDAR = URL_BASE + "/calendario-de-colectas"

# robots.txt: "Crawl-delay: 10".
CRAWL_DELAY_SECONDS = 10

# What Radware serves instead of the page when it flags a request.
CAPTCHA_MARKER = "Radware Captcha Page"

# Popups are opened by "javascript:smsCRHToggleMapa('<id>')", <id> being the
# element that holds the map iframe.
MAP_TOGGLE_RE = re.compile(r"smsCRHToggleMapa\('([^']+)'\)")

# A fixed spot's map is a Google Maps embed: "...!2d-1.121929!3d37.983067!...".
EMBED_COORDS_RE = re.compile(r"!2d(-?\d+(?:\.\d+)?)!3d(-?\d+(?:\.\d+)?)")

# A mobile stop's map: "https://maps.google.com/maps?q=38.0971,-1.2273&hl=es...".
QUERY_COORDS_RE = re.compile(r"[?&]q=(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")

# A calendar day heading: "Jueves, 29 de Octubre de 2026".
DAY_HEADING_RE = re.compile(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})")

# "09:30 - 14:00".
TIME_RANGE_RE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")

# "Fijos" spots that only open on given days ("Último jueves de cada mes",
# "Primer y tercer jueves de cada mes") and are also listed, with each day's
# exact hours, in the calendar. Kept only as mobile stops, so they aren't
# shown twice and their vague fixed-point hours aren't needed.
FIXED_POINTS_IN_CALENDAR = {
    "Hospital Virgen del Castillo",  # Yecla
    "Centro Especialidades Santa Rosa de Lima",  # Lorca
}

# The level image's filename -> (status colour, level), the colour being the
# image's own fill. Its alt can't tell them apart: the orange one is also
# "urgente" (seen on a 2022 Wayback Machine snapshot). Its src reads
# "/documents/58881/58939/Donaci%C3%B3n+urgente.svg/<uuid>?t=...".
LEVEL_IMAGE_RE = re.compile(r"/([^/]+\.svg)/")
BLOOD_LEVEL_STATUS = {
    "Donación en próxima colecta.svg": ("green", 3),  # #39b54a
    "Donación en días.svg": ("orange", 2),  # #fbb03b
    "Donación urgente.svg": ("red", 1),  # #ed1c24
}

SESSION = curl_requests.Session(impersonate="chrome")
SESSION.headers["Accept-Language"] = "es-ES,es;q=0.9"

# Monotonic time of the last request, so fetch_page can keep the crawl delay.
LAST_REQUEST = {"at": None}

# Pages already fetched this run, by URL.
PAGES: dict[str, str | None] = {}


def fetch_page(url: str) -> str | None:
    """Fetch a murciasalud.es page, or None if Radware served its captcha.

    A captcha is logged and the region's points are left out of this run
    instead of failing the whole ETL, since Radware may start flagging the
    job at any time. Pages are fetched once per run and spaced by the
    robots.txt crawl delay.
    """
    if url in PAGES:
        return PAGES[url]
    last = LAST_REQUEST["at"]
    if last is not None:
        time.sleep(max(0.0, CRAWL_DELAY_SECONDS - (time.monotonic() - last)))
    response = SESSION.get(url)
    LAST_REQUEST["at"] = time.monotonic()
    response.raise_for_status()
    if CAPTCHA_MARKER in response.text:
        log.warning("Murcia: Radware served a captcha for %s; skipping it", url)
        PAGES[url] = None
    else:
        PAGES[url] = response.text
    return PAGES[url]


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace, &nbsp; included."""
    return " ".join(text.split())


def map_target(container: Tag, soup: BeautifulSoup) -> Tag | None:
    """The map popup element a container's "Localización"/"Ver plano" link opens."""
    link = container.find("a", href=MAP_TOGGLE_RE)
    if link is None:
        return None
    toggle = crawl.required(
        MAP_TOGGLE_RE.search(crawl.attribute(link, "href")), "map toggle id"
    )
    return soup.find(id=toggle.group(1))


def fixed_point_coordinates(
    point: Tag, soup: BeautifulSoup
) -> tuple[float | None, float | None]:
    """Read a fixed spot's coordinates from its popup's Google Maps embed."""
    popup = map_target(point, soup)
    iframe = popup.find("iframe") if popup else None
    match = EMBED_COORDS_RE.search(crawl.attribute(iframe, "src")) if iframe else None
    if not match:
        return (None, None)
    return (float(match.group(2)), float(match.group(1)))


def mobile_stop_coordinates(
    stop: Tag, soup: BeautifulSoup
) -> tuple[float | None, float | None]:
    """Read a mobile stop's coordinates from its popup iframe's data-src."""
    popup = map_target(stop, soup)
    iframe = popup.find("iframe") if popup else None
    if iframe is None or not iframe.get("data-src"):
        return (None, None)
    match = QUERY_COORDS_RE.search(crawl.attribute(iframe, "data-src"))
    if not match:
        return (None, None)
    return (float(match.group(1)), float(match.group(2)))


def parse_fixed_points(html: str) -> list[dict]:
    """Parse the homepage's "Fijos" tab into fixed point rows.

    Each spot's title reads "<Town> - <Name>"; its hours are free text (with
    any plasma-appointment note), and a few have an extra note after the
    "Localización" link. Spots in FIXED_POINTS_IN_CALENDAR are skipped.
    """
    soup = BeautifulSoup(html, features="lxml")
    points = []
    for point in soup.select(".punto-donacion-fijo"):
        title = normalize_whitespace(
            crawl.required(
                point.select_one(".titulo-punto-donacion"), "fixed point title"
            ).get_text(" ")
        )
        localidad, name = (part.strip() for part in title.split(" - ", 1))
        if name in FIXED_POINTS_IN_CALENDAR:
            continue
        phone = point.select_one(".info-contacto")
        horario = normalize_whitespace(
            crawl.required(
                point.select_one(".info-disponibilidad"), "fixed point hours"
            ).get_text(" ")
        )
        note = point.select_one("span.font-weight-semibold:has(a[href*=ToggleMapa])")
        observaciones = (
            normalize_whitespace(note.get_text(" ").replace("Localización", ""))
            if note
            else ""
        )
        latitude, longitude = fixed_point_coordinates(point, soup)
        points.append(
            {
                "name": name,
                "localidad": localidad,
                "direccion": None,
                "telefono": normalize_whitespace(phone.get_text()) if phone else None,
                "horario": horario,
                "observaciones": observaciones or None,
                "plasma": "plasma" in horario.lower(),
                "latitude": latitude,
                "longitude": longitude,
                "url": URL_BASE,
            }
        )
    return points


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape the homepage's fixed spots (none if Radware blocked it)."""
    columns = [
        "name",
        "localidad",
        "direccion",
        "telefono",
        "horario",
        "observaciones",
        "plasma",
        "latitude",
        "longitude",
        "url",
    ]
    html = fetch_page(URL_BASE)
    return pd.DataFrame(parse_fixed_points(html) if html else [], columns=columns)


def parse_day_heading(heading: Tag) -> datetime.date | None:
    """Parse a calendar day heading ("Jueves, 29 de Octubre de 2026")."""
    match = DAY_HEADING_RE.search(normalize_whitespace(heading.get_text(" ")))
    if not match:
        return None
    day, month_name, year = match.groups()
    month = comunidad_valenciana.MONTH_NAME_TO_NUM.get(month_name.lower())
    if month is None:
        return None
    return datetime.date(int(year), month, int(day))


def parse_stop(stop: Tag, soup: BeautifulSoup, fecha: str) -> dict | None:
    """Flatten one calendar entry into a mobile point row.

    The entry's bold block names the place and then its venue (e.g. "Mula",
    "Centro de Salud"); its hidden "Más información" block lists the street,
    postcode and town, in that order.
    """
    title_lines = [
        normalize_whitespace(p.get_text(" "))
        for p in stop.select("div.font-weight-semibold p")
    ]
    hours = TIME_RANGE_RE.search(stop.get_text(" "))
    if not title_lines or not hours:
        return None
    place, *venue = title_lines
    info = stop.select_one("div[id$='___info']")
    address = (
        [normalize_whitespace(span.get_text(" ")) for span in info.find_all("span")]
        if info
        else []
    )
    street = address[0] if address else None
    town = address[-1] if len(address) == 3 else None
    open_h, open_m, close_h, close_m = hours.groups()
    latitude, longitude = mobile_stop_coordinates(stop, soup)
    return {
        "lugar": f"{place} ({venue[0]})" if venue and venue[0] else place,
        "localidad": crawl.title_name(town) if town and town.isupper() else town,
        "direccion": street or None,
        "fecha": fecha,
        "horario": f"{int(open_h):02d}:{open_m}-{int(close_h):02d}:{close_m}",
        "latitude": latitude,
        "longitude": longitude,
        "url": URL_CALENDAR,
    }


def parse_calendar(html: str, today: datetime.date) -> list[dict]:
    """Parse the calendar into mobile stop rows, from today on.

    Each day is a centred heading paragraph followed by a block of stop
    cards; each card's map popup sits next to it, found by id.
    """
    soup = BeautifulSoup(html, features="lxml")
    stops = []
    for heading in soup.select("p.text-center"):
        date = parse_day_heading(heading)
        if date is None or date < today:
            continue
        cards = heading.find_next_sibling("div")
        if cards is None:
            continue
        fecha = date.strftime("%d/%m/%Y")
        for card in cards.find_all("div", class_="col-md-3", recursive=False):
            stop = parse_stop(card, soup, fecha)
            if stop:
                stops.append(stop)
    return stops


def scrape_mobile_points(today: datetime.date | None = None) -> pd.DataFrame:
    """Scrape the calendar's mobile stops (none if Radware blocked it)."""
    columns = [
        "lugar",
        "localidad",
        "direccion",
        "fecha",
        "horario",
        "latitude",
        "longitude",
        "url",
    ]
    today = today or comunidad_valenciana.madrid_today()
    html = fetch_page(URL_CALENDAR)
    return pd.DataFrame(parse_calendar(html, today) if html else [], columns=columns)


def parse_blood_levels(html: str) -> list[dict]:
    """Parse the homepage's "Niveles de reserva": one card per blood type.

    Each card shows its type, an image whose filename gives the level (see
    BLOOD_LEVEL_STATUS) and the label beneath it ("Dona de manera habitual").
    An image not in BLOOD_LEVEL_STATUS is logged and its type skipped.
    """
    soup = BeautifulSoup(html, features="lxml")
    blood_levels = []
    for card in soup.select("#crh-niveles-reservas .journal-content-article"):
        blood_type = normalize_whitespace(
            crawl.required(card.select_one(".crh-grupos"), "blood type").get_text()
        )
        image = crawl.required(card.select_one(".nivel-reserva img"), "level image")
        src = urllib.parse.unquote_plus(crawl.attribute(image, "src"))
        filename = unicodedata.normalize(
            "NFC", crawl.required(LEVEL_IMAGE_RE.search(src), "level image").group(1)
        )
        label = card.select_one(".nivel")
        if filename not in BLOOD_LEVEL_STATUS:
            log.warning("Murcia: unknown blood level %r for %s", filename, blood_type)
            continue
        status, level = BLOOD_LEVEL_STATUS[filename]
        blood_levels.append(
            {
                "blood_type": blood_type,
                "status": status,
                "level": level,
                "label": normalize_whitespace(label.get_text()) if label else None,
            }
        )
    return blood_levels


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape the homepage's blood levels (none if Radware blocked it)."""
    html = fetch_page(URL_BASE)
    return pd.DataFrame(
        parse_blood_levels(html) if html else [],
        columns=["blood_type", "status", "level", "label"],
    )
