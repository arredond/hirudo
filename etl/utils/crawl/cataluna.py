"""Crawl Banc de Sang i Teixits (Cataluña) pages and retrieve fixed and mobile blood donation spots.

Fixed points are the hospitals listed on the "Dónde donar" page, each with
its own info page (address + a free-text weekly "Horario", hand-translated
into opening_hours_fijos.json like every other region's). Mobile points
come from the "Calendario de recogida" page, which lists every upcoming
stop (about a month ahead) as a card — town, venue, street, and "Dona
sangre"/"Dona plasma" booking buttons — but not its hours: those are only
on each stop's own booking page ("De 16:00 a 20:00"), so every card's page
is fetched too (a few hundred requests per run).

No blood-levels ("niveles de sangre") widget exists on this site, so, like
Castilla-La Mancha, there's no scrape_blood_levels() here.
"""

import re
import urllib.parse

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL_BASE = "https://www.bancsang.net/"
URL_FIXED_POINTS = urllib.parse.urljoin(URL_BASE, "es/donaciones/sangre/donde/")
URL_MOBILE_POINTS = urllib.parse.urljoin(
    URL_BASE, "es/donaciones/sangre/calendario-de-recogida/"
)

# Fixed-point hospitals' booking links look like /es/donaciones/sangre/
# hospital/c/<id>/, and their info pages live at /es/hospitales/<id>/.
HOSPITAL_ID_RE = re.compile(r"/hospital/c/(\d+)/")

# Every booking link carries the stop's date as DD-MM-YYYY — either in the
# path (blood: .../poblacion//9386/barcelona/27-10-2026/) or as a "day"
# query param (plasma: .../inscripcion/?hospital=534K&day=27-10-2026).
LINK_DATE_RE = re.compile(r"(\d{2})-(\d{2})-(\d{4})")

# Fixed-point towns move a leading article to the end for sorting, e.g.
# "Hospitalet de Llobregat, L'" instead of "L'Hospitalet de Llobregat".
LOCALITY_ARTICLE_SUFFIX_RE = re.compile(r"^(.+),\s*(L'|El|La|Els|Les)$")

# Mobile stops at a donation bus ("Unidad móvil", "Unitat mòbil") parked on a
# street or square: their street address *is* the location, and the venue
# text isn't a searchable place (see is_mobile_unit).
MOBILE_UNIT_RE = re.compile(
    r"\bunidad\s+m[oó][vb]il|\bunitat\s+m[oò]bil", re.IGNORECASE
)

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"


def hospital_info_url(hospital_id: str) -> str:
    """Build a fixed-point hospital's info page URL."""
    return urllib.parse.urljoin(URL_BASE, f"es/hospitales/{hospital_id}/")


def clean_locality(locality: str) -> str:
    """Un-invert a trailing sorting article, e.g. "Hospitalet de Llobregat,
    L'" -> "L'Hospitalet de Llobregat"."""
    match = LOCALITY_ARTICLE_SUFFIX_RE.match(locality)
    if not match:
        return locality
    name, article = match.groups()
    separator = "" if article.endswith("'") else " "
    return f"{article}{separator}{name}"


def is_mobile_unit(venue: str | None) -> bool:
    """Tell whether a stop is a donation bus (see MOBILE_UNIT_RE)."""
    return bool(venue and MOBILE_UNIT_RE.search(venue))


def section_after_heading(soup: BeautifulSoup, heading: str):
    """Return the element right after the <h3> whose text is `heading`."""
    for h3 in soup.find_all("h3"):
        if h3.get_text(strip=True) == heading:
            return h3.find_next_sibling()
    return None


def parse_hospital_ids(soup: BeautifulSoup) -> list[str]:
    """List the fixed-point hospital ids linked from the "Dónde donar" page."""
    ids = []
    for link in soup.find_all("a", href=True):
        match = HOSPITAL_ID_RE.search(link["href"])
        if match and match.group(1) not in ids:
            ids.append(match.group(1))
    return ids


def parse_hospital_info(soup: BeautifulSoup) -> dict:
    """Parse a hospital info page: name, "Horario" text, and "Ubicación".

    "Ubicación" is a street line, then "<CP>\\t\\t<town>", then the phone;
    "Horario" keeps its line breaks joined with " / " (they separate the
    regular schedule from one-off notices, which matters when translating
    it by hand into opening_hours_fijos.json).
    """
    name = soup.find("h1").get_text(strip=True)

    horario = None
    horario_block = section_after_heading(soup, "Horario")
    if horario_block:
        lines = [
            " ".join(line.split())
            for line in horario_block.get_text("\n", strip=True).split("\n")
        ]
        horario = " / ".join(line for line in lines if line)

    direccion = codigo_postal = localidad = telefono = None
    ubicacion_block = section_after_heading(soup, "Ubicación")
    if ubicacion_block:
        street = ubicacion_block.find(string=True, recursive=False)
        direccion = " ".join(street.split()) if street else None
        paragraphs = ubicacion_block.find_all("p")
        if paragraphs:
            codigo_postal, _, localidad = (
                paragraphs[0].get_text().strip().partition("\t")
            )
            localidad = clean_locality(localidad.strip())
        if len(paragraphs) > 1:
            telefono = paragraphs[1].get_text(" ", strip=True) or None

    return {
        "name": name,
        "horario": horario,
        "direccion": direccion,
        "codigo_postal": codigo_postal.strip() if codigo_postal else None,
        "localidad": localidad,
        "telefono": telefono,
    }


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape every fixed-point hospital from its info page.

    Every hospital listed takes both blood and plasma (each has both
    booking buttons on the "Dónde donar" page). The site's numeric hospital
    id isn't kept as center_id: bare ids like "4" could collide with other
    regions' keys in the shared opening_hours_fijos.json, so these are
    looked up by name instead.
    """
    soup = BeautifulSoup(SESSION.get(URL_FIXED_POINTS).text, features="lxml")
    points = []
    for hospital_id in parse_hospital_ids(soup):
        url = hospital_info_url(hospital_id)
        info_soup = BeautifulSoup(SESSION.get(url).text, features="lxml")
        point = parse_hospital_info(info_soup)
        point.update({"plasma": True, "url": url})
        points.append(point)
    return pd.DataFrame(points)


def link_date(href: str) -> str | None:
    """Pull a booking link's DD-MM-YYYY date out as "DD/MM/YYYY"."""
    match = LINK_DATE_RE.search(href)
    return "/".join(match.groups()) if match else None


def parse_mobile_cards(soup: BeautifulSoup) -> list[dict]:
    """Parse every stop card on the "Calendario de recogida" page.

    Each card has the town in an <h3>, then "<venue><br><street>" in a <p>,
    then one booking button per donation type it takes ("is-primary" for
    blood, "is-plasma" for plasma). A card with only a plasma button is a
    plasma-only stop.
    """
    cards = []
    for card in soup.select("div.boxes-grid > div.column"):
        town = card.find("h3")
        place = card.find("p")
        if not town or not place:
            continue
        lines = [line.strip() for line in place.get_text("\n").split("\n")]
        lines = [line for line in lines if line]
        hrefs = [link["href"] for link in card.find_all("a", href=True)]
        sangre_href = next((href for href in hrefs if "/sangre/" in href), None)
        plasma_href = next((href for href in hrefs if "/plasma/" in href), None)
        booking_href = sangre_href or plasma_href
        cards.append(
            {
                "localidad": town.get_text(strip=True),
                "venue": lines[0] if lines else None,
                "direccion": lines[1] if len(lines) > 1 else None,
                "fecha": link_date(booking_href) if booking_href else None,
                "sangre": sangre_href is not None,
                "plasma": plasma_href is not None,
                "url": (
                    urllib.parse.urljoin(URL_BASE, sangre_href)
                    if sangre_href
                    else URL_MOBILE_POINTS
                ),
            }
        )
    return cards


def parse_stop_hours(soup: BeautifulSoup) -> str | None:
    """Pull "De 16:00 a 20:00" from a stop's booking page, or None."""
    horari = soup.find("p", class_="horari")
    if not horari:
        return None
    return " ".join(horari.get_text(" ", strip=True).split()) or None


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape every upcoming mobile stop, plus its hours from its own page.

    Plasma-only stops have no blood-booking page, and their plasma one only
    lists bookable slots (not opening hours), so their horario stays None
    rather than being guessed from the slots.
    """
    soup = BeautifulSoup(SESSION.get(URL_MOBILE_POINTS).text, features="lxml")
    cards = parse_mobile_cards(soup)
    for card in cards:
        card["horario"] = None
        if card["sangre"]:
            stop_soup = BeautifulSoup(SESSION.get(card["url"]).text, features="lxml")
            card["horario"] = parse_stop_hours(stop_soup)
    return pd.DataFrame(cards)
