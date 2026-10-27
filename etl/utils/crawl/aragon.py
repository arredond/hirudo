"""Crawl Banco de Sangre y Tejidos de Aragón and retrieve fixed and mobile blood donation spots.

Fixed points are a short hand-edited list on the homepage. Mobile points
("extracciones") are published through the WordPress "The Events Calendar"
plugin, whose REST API returns them as clean JSON — so they're read from
there rather than scraped from the rendered calendar page. No blood-levels
("niveles de sangre") widget exists on this site, so, like Castilla-La
Mancha, there's no scrape_blood_levels() here.
"""

import re
import urllib.parse

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL_BASE = "https://bancosangrearagon.org/"
URL_MOBILE_POINTS = urllib.parse.urljoin(URL_BASE, "extracciones/")
URL_EVENTS_API = urllib.parse.urljoin(URL_BASE, "wp-json/tribe/events/v1/events")

# Plasma (apheresis) is only taken at the Banco itself, by phone appointment
# (see https://bancosangrearagon.org/donacion-de-plasma-sanguineo/).
PLASMA_CENTER_NAME = "Banco de Sangre y Tejidos de Aragón"

# Fixed points' free text runs "<address>. Teléfono: <phone>. Horario: <hours>"
# together in one <li>, sometimes followed by extra notes (floor, building).
FIXED_POINT_RE = re.compile(
    r"^(?P<direccion>.*?)\s*Teléfono:\s*(?P<telefono>[\d ]+?)\.?\s*"
    r"Horario:\s*(?P<horario>.*)$"
)

# Event titles read "<town or organization>, en <venue>", e.g. "Sariñena, en
# el Centro de Salud" or "Ibercaja, en el Hall del Salón Aragón". Some have no
# venue part at all (e.g. "Amazon Data Huesca").
EVENT_TITLE_RE = re.compile(
    r"^(?P<who>.+?),\s+en\s+(?:(?:el|la|los|las)\s+)?(?P<venue>.+)$",
    re.IGNORECASE,
)

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"


def parse_fixed_points(soup: BeautifulSoup) -> list[dict]:
    """Parse the homepage's "Puntos fijos de donación" block.

    It's an <h4> per province followed by a <ul> with one <li> per center,
    each holding the center's name in a <strong> and the rest as free text.
    """
    block = soup.find("div", class_="puntos-fijos")
    points = []
    for heading in block.find_all("h4"):
        province = heading.get_text(strip=True).title()
        for item in heading.find_next_sibling("ul").find_all("li"):
            name = item.find("strong").get_text(" ", strip=True)
            item.find("strong").extract()
            text = " ".join(item.get_text(" ", strip=True).split())
            match = FIXED_POINT_RE.match(text)
            point = {"name": name, "localidad": province}
            if match:
                point.update(
                    {
                        "direccion": match["direccion"].rstrip(". "),
                        "telefono": match["telefono"].strip(),
                        "horario": match["horario"].strip(),
                    }
                )
            else:
                point["direccion"] = text
            point["plasma"] = name == PLASMA_CENTER_NAME
            points.append(point)
    return points


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape every fixed donation point from the homepage."""
    html = SESSION.get(URL_BASE).text
    soup = BeautifulSoup(html, features="lxml")
    df = pd.DataFrame(parse_fixed_points(soup))
    df["url"] = URL_BASE
    return df


def split_event_title(title: str) -> tuple[str, str | None]:
    """Split an event title into its (town or organization, venue) parts.

    The venue is None for titles with no ", en ..." part.
    """
    match = EVENT_TITLE_RE.match(title.strip())
    if not match:
        return title.strip(), None
    return match["who"].strip(), match["venue"].strip()


def parse_event(event: dict) -> dict:
    """Flatten one Events Calendar API event into a mobile point row.

    Dates/times are rebuilt into the same "DD/MM/YYYY" + "HH:MM a HH:MM"
    shape every other region scrapes, so parse_mobile_hours handles them
    unchanged.
    """
    start = pd.Timestamp(event["start_date"])
    end = pd.Timestamp(event["end_date"])
    title = BeautifulSoup(event["title"], features="lxml").get_text(strip=True)
    who, venue = split_event_title(title)
    return {
        "title": title,
        "who": who,
        "venue": venue,
        "fecha": start.strftime("%d/%m/%Y"),
        "horario": f"{start:%H:%M} a {end:%H:%M}",
        "url": event["url"],
    }


def scrape_mobile_points() -> pd.DataFrame:
    """Fetch every upcoming mobile donation point from the events API.

    Starts from today's midnight (rather than the API's default of "now") so
    stops earlier the same day still show up, then follows next_rest_url
    until the last page.
    """
    params = {
        "per_page": 50,
        "start_date": pd.Timestamp.now(tz="Europe/Madrid").strftime("%Y-%m-%d"),
    }
    url = URL_EVENTS_API
    events = []
    while url:
        data = SESSION.get(url, params=params).json()
        events.extend(data.get("events", []))
        url = data.get("next_rest_url")
        params = None  # next_rest_url already carries every query param
    return pd.DataFrame([parse_event(event) for event in events])
