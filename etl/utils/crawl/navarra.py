"""Crawl ADONA (Navarra) and retrieve fixed and mobile blood donation spots.

ADONA (https://adona.es/es/) runs two fixed spots, the Banco de Sangre in
Pamplona and a centre in Tudela, each with a contact page: an address, phone
and hours in icon-led boxes, plus a Google Map whose initMap() script embeds
the spot's coordinates (with decimal commas, so they're read off by hand here).

Mobile stops ("Unidad móvil", the Autohemoteca) come from the JSON feed behind
the calendar page: one event per stop, titled "TOWN HH:MM - HH:MM" with the
venue on the next line. There's no address or coordinates, so those are
geocoded in regions/navarra.py.

No blood-levels ("niveles de sangre") widget exists on this site, so, like
Castilla-La Mancha, there's no scrape_blood_levels() here.
"""

import datetime
import re
import urllib.parse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from utils.crawl import comunidad_valenciana, crawl

URL_BASE = "https://adona.es/es/"
URL_MOBILE_POINTS = urllib.parse.urljoin(URL_BASE, "calendario-unidad-movil")
URL_CALENDAR_EVENTS = "https://adona.es/adona/calendars/get.json"

# Fixed spot name -> its contact page. The names are ours: the site only
# calls them "Pamplona" and "Tudela".
FIXED_POINT_PAGES = {
    "Banco de Sangre de Pamplona": urllib.parse.urljoin(
        URL_BASE, "contacto-adona/contacto-pamplona"
    ),
    "Banco de Sangre de Tudela": urllib.parse.urljoin(
        URL_BASE, "contacto-adona/contacto-tudela"
    ),
}

# How far ahead the calendar is asked for. It publishes about two months out.
MOBILE_EVENTS_DAYS_AHEAD = 180

# Each info box is a <div class="box-services-2"> whose icon class names what
# it holds: the address, the phone or the hours.
INFO_BOX_ICONS = {
    "icon_pin_alt": "direccion",
    "icon_mobile": "telefono",
    "icon_clock_alt": "horario",
}

# "C/ Irunlarrea, 3 (Hospital de Navarra) 31008 PAMPLONA"
ADDRESS_RE = re.compile(r"^(?P<direccion>.+?)\s+\d{5}\s+(?P<localidad>[^\d]+)$")

# initMap()'s centre, with decimal commas: "{lat: 42,804981957138, lng: -1,6653321776321}"
MAP_CENTER_RE = re.compile(r"lat:\s*(-?\d+),(\d+),\s*lng:\s*(-?\d+),(\d+)")

# Calendar titles read "SANTACARA 16:45 - 20:45\nCentro de Salud". Some write
# the times with dots ("LOS ARCOS 17.00 - 21.00"); the empty placeholder
# entry (".  - \n") matches nothing and is skipped.
EVENT_TITLE_RE = re.compile(
    r"^(?P<localidad>.+?)\s+"
    r"(?P<open>\d{1,2}[:.]\d{2})\s*-\s*(?P<close>\d{1,2}[:.]\d{2})\s*"
    r"\n\s*(?P<lugar>.+?)\s*$",
    re.DOTALL,
)

# Particles title-casing shouldn't capitalize ("SAN MARTÍN DE UNX").
TOWN_PARTICLE_RE = re.compile(r"(?<=\s)(?:De|Del|La|Las|Los|El)(?=\s)")

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"


def normalize_time(text: str) -> str:
    """Turn "16.45" into "16:45"."""
    return text.replace(".", ":")


def title_town(text: str) -> str:
    """Title-case an all-caps town name, keeping its particles lowercase."""
    return TOWN_PARTICLE_RE.sub(lambda match: match.group().lower(), text.title())


def parse_contact_page(html: str) -> dict:
    """Parse one fixed spot's contact page into its address, phone and hours.

    The map centre comes from the page's initMap() script; latitude and
    longitude are None if the page has none.
    """
    soup = BeautifulSoup(html, features="lxml")
    point = {}
    for box in soup.select("div.box-services-2"):
        icon = crawl.required(box.select_one("i"), "info box icon")
        field = next(
            (
                INFO_BOX_ICONS[name]
                for name in icon.get_attribute_list("class")
                if name in INFO_BOX_ICONS
            ),
            None,
        )
        content = crawl.required(box.select_one("div.box-right"), "info box text")
        text = " ".join(content.get_text(" ").split())
        if field == "direccion":
            match = crawl.required(ADDRESS_RE.match(text), "address")
            point["direccion"] = match["direccion"].strip()
            point["localidad"] = title_town(match["localidad"].strip())
        elif field == "telefono":
            point["telefono"] = text.removeprefix("T.").strip()
        elif field == "horario":
            point["horario"] = text

    center = MAP_CENTER_RE.search(html)
    point["latitude"] = float(f"{center[1]}.{center[2]}") if center else None
    point["longitude"] = float(f"{center[3]}.{center[4]}") if center else None
    return point


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape both fixed spots from their contact pages."""
    points = []
    for name, url in FIXED_POINT_PAGES.items():
        html = SESSION.get(url).text
        points.append({"name": name, **parse_contact_page(html), "url": url})
    return pd.DataFrame(points)


def parse_event(event: dict) -> dict | None:
    """Flatten one calendar event into a mobile stop row, or None if unparseable."""
    match = EVENT_TITLE_RE.match(event["title"].strip())
    if not match:
        return None
    fecha = datetime.date.fromisoformat(event["start"]).strftime("%d/%m/%Y")
    return {
        "localidad": title_town(match["localidad"].strip()),
        "lugar": " ".join(match["lugar"].split()),
        "fecha": fecha,
        "horario": (
            f"{normalize_time(match['open'])} a {normalize_time(match['close'])}"
        ),
        "url": URL_MOBILE_POINTS,
    }


def scrape_mobile_points(today: datetime.date | None = None) -> pd.DataFrame:
    """Fetch every upcoming mobile stop from the calendar feed.

    The feed only answers a request that carries a unix start/end window, and
    its window reaches back a few days, so events before today are dropped.
    """
    today = today or comunidad_valenciana.madrid_today()
    start = pd.Timestamp(today).tz_localize("Europe/Madrid")
    params = {
        "start": int(start.timestamp()),
        "end": int((start + pd.Timedelta(days=MOBILE_EVENTS_DAYS_AHEAD)).timestamp()),
    }
    events = SESSION.get(URL_CALENDAR_EVENTS, params=params).json()["events"]
    points = [
        parse_event(event) for event in events if event["start"] >= today.isoformat()
    ]
    columns = ["localidad", "lugar", "fecha", "horario", "url"]
    return pd.DataFrame([point for point in points if point], columns=columns)
