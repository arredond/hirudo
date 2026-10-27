"""Crawl ADOS (Axencia de Doazón de Órganos e Sangue, Galicia) pages and retrieve
fixed and mobile blood donation spots and blood-reserve levels.

Fixed points are the seven "Locais de doazón" on one accordion page, each
with free-text hours (hand-translated into opening_hours_fijos.json, keyed by
name), an address block, and — for most — GPS coordinates in degrees,
minutes and seconds. Mobile points ("Desprazamentos das unidades móbiles")
are one page of ~3 weeks of donation-bus stops, grouped by health area and
date. Everything is in Galician.

Blood levels ("Semáforo") are published only as an image: one four-light
traffic light per blood type, so the lit light's colour is read straight
from the image's pixels (see parse_blood_levels_image).
"""

import io
import re
import urllib.parse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image

URL_BASE = "https://ados.sergas.gal/"
URL_FIXED_POINTS = urllib.parse.urljoin(URL_BASE, "cartafol/ADOS-locais")
URL_MOBILE_POINTS = urllib.parse.urljoin(URL_BASE, "cartafol/proximos-desprazamentos")
URL_BLOOD_LEVELS = urllib.parse.urljoin(URL_BASE, "cartafol/sangue-semaforo")

# "Coordenadas GPS: 43°20'38.8"N 8°23'20.0"W." — the degree sign is sometimes
# "º" and the seconds mark sometimes two single quotes.
DMS_RE = re.compile(
    r"(\d+)\s*[°º]\s*(\d+)\s*'\s*([\d.]+)\s*(?:\"|'')\s*([NSEW])", re.IGNORECASE
)

# A postcode line ("15405 Ferrol") or a street line ending in one
# ("As Xubias, 84. 15006 A Coruña") names the point's town.
POSTCODE_RE = re.compile(r"\b(\d{5})\s+(.+)$")

# Fixed-point names are "Local de doazón de <city>"; the city stands in as
# the locality when the address block has no postcode line.
FIXED_POINT_CITY_RE = re.compile(r"^Local de doaz[óo]n d[ae]\s+(.+)$")

# Mobile stops' location text starts with the bus itself ("UNIDADE MÓBIL NA
# PRAZA DO CARMEN", "UM no aparcadoiro da Facultade…", spelled MÓBIL,
# MOBIL or MOVIL) and/or a preposition of place ("NA PRAZA PÚBLICA", "EN LA
# CALLE…"), neither of which a geocoder or Places can use.
MOBILE_UNIT_PREFIX_RE = re.compile(
    r"^(?:UNIDADE\s+M[ÓO][BV]IL\s+|UM\s+)?"
    r"(?:(?:NA|NO|NAS|NOS|EN(?:\s+LA)?|ENTRE|DENTRO\s+D[AO]S?|DETR[ÁA]S\s+D[AO]S?"
    r"|XUNTO\s+[AÁÓ]O?S?|DIANTE\s+D[AOE]S?|FRONTE\s+[AÁÓ]O?S?"
    r"|(?:AO|A)\s+CAR[ÓO]N\s+D[AO]S?)\s+)?",
    re.IGNORECASE,
)

# A row can list several places within its concello, each prefixed by its
# own parish/village: "QUINS: UNIDADE MOBIL DIANTE DO CENTRO DE SAÚDE".
LOCATION_PLACE_PREFIX_RE = re.compile(r"^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ .'-]{1,40}):\s*(.+)$")

# Unfilled template slots ("Localización 2") carry hours but no place.
PLACEHOLDER_LOCATION_RE = re.compile(r"^Localizaci[óo]n\s+\d+$", re.IGNORECASE)

# The semáforo image's cards, in reading order (two rows of four). The
# labels are drawn into the image, so the order has to be hardcoded.
BLOOD_LEVEL_IMAGE_TYPES = ["A+", "A-", "B+", "B-", "0+", "0-", "AB+", "AB-"]

# Lit light hue -> (status, level, label). Galicia uses four levels (red,
# orange, yellow, green from top to bottom) where Madrid and Castilla y León
# use three; like theirs, status is the colour itself and level 1 = most
# urgent. Hue ranges are on Pillow's 0-255 scale (red wraps around).
BLOOD_LEVEL_COLOURS = [
    ((0, 10), ("red", 1, "Nivel rojo")),
    ((10, 30), ("orange", 2, "Nivel naranja")),
    ((30, 55), ("yellow", 3, "Nivel amarillo")),
    ((55, 130), ("green", 4, "Nivel verde")),
    ((235, 256), ("red", 1, "Nivel rojo")),
]

# A pixel counts as part of a lit light when it's this saturated and bright
# (the unlit lights are grey), and a card needs this many such pixels.
LIT_MIN_SATURATION = 120
LIT_MIN_VALUE = 120
LIT_MIN_PIXELS = 100

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"


def clean_text(text: str) -> str:
    """Collapse whitespace and drop the zero-width spaces SharePoint sprinkles in."""
    return " ".join(text.replace("\u200b", "").split())


def dms_to_decimal(degrees: str, minutes: str, seconds: str, hemisphere: str):
    """Convert degrees/minutes/seconds to signed decimal degrees."""
    value = int(degrees) + int(minutes) / 60 + float(seconds) / 3600
    return -value if hemisphere.upper() in "SW" else value


def parse_gps(text: str) -> tuple[float, float] | tuple[None, None]:
    """Pull (latitude, longitude) out of a "Coordenadas GPS" line."""
    matches = DMS_RE.findall(text)
    if len(matches) != 2:
        return None, None
    latitude, longitude = (dms_to_decimal(*match) for match in matches)
    return latitude, longitude


def parse_fixed_point(block) -> dict:
    """Parse one "Local de doazón" accordion block.

    Its paragraphs run "Horario", the hours lines, "Enderezo", then the
    address lines (venue first), "Teléfono …", parking notes and the GPS
    line. The hours lines keep their order joined with " / " (Ourense and
    Pontevedra list a winter and a summer schedule).
    """
    name = clean_text(block.select_one(".accordion-content-block-title").get_text())
    data = block.select_one(".accordion-content-block-data")
    lines = [clean_text(p.get_text(" ")) for p in data.find_all("p")]
    lines = [line for line in lines if line]

    section = None
    horario, address_lines = [], []
    latitude = longitude = None
    for line in lines:
        if line in ("Horario", "Enderezo"):
            section = line
        elif line.startswith("Coordenadas GPS"):
            latitude, longitude = parse_gps(line)
        elif line.startswith("Teléfono"):
            section = None
        elif section == "Horario":
            horario.append(line)
        elif section == "Enderezo":
            address_lines.append(line)

    postcode = next(filter(None, map(POSTCODE_RE.search, address_lines)), None)
    if postcode:
        codigo_postal, localidad = postcode.groups()
    else:
        city = FIXED_POINT_CITY_RE.match(name)
        codigo_postal, localidad = None, city.group(1) if city else None

    return {
        "name": name,
        "venue": address_lines[0] if address_lines else None,
        "direccion": " · ".join(address_lines) or None,
        "localidad": localidad,
        "codigo_postal": codigo_postal,
        "horario": " / ".join(horario) or None,
        "latitude": latitude,
        "longitude": longitude,
    }


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape every "Local de doazón". All of them take plasma too."""
    soup = BeautifulSoup(SESSION.get(URL_FIXED_POINTS).text, features="lxml")
    points = [
        parse_fixed_point(block)
        for block in soup.select("div.accordion-simple div.accordion-content-block")
    ]
    df = pd.DataFrame(points)
    df["plasma"] = True
    df["url"] = URL_FIXED_POINTS
    return df


def strip_mobile_unit_prefix(location: str) -> str:
    """Drop the "UNIDADE MÓBIL NA …" lead-in from a stop's location text."""
    return MOBILE_UNIT_PREFIX_RE.sub("", location).strip()


def parse_mobile_points(soup: BeautifulSoup) -> list[dict]:
    """Parse every stop on the "Desprazamentos" page.

    Each health area (<details>) has one table per date; each row has the
    concello, the collection place ("Lugar de colecta", maybe with a
    "Provisional" badge) and one or more location + hours items. Each
    location item becomes its own stop; template placeholders with no real
    location are dropped.
    """
    stops = []
    for area in soup.select("details.group-details"):
        area_name = clean_text(area.summary.get_text())
        for header in area.select("div.date-header"):
            fecha = clean_text(header.get_text()).split(",")[-1].strip()
            table = header.find_next_sibling("div", class_="table-wrapper")
            if table is None:
                continue
            for row in table.select("tbody tr"):
                cells = row.find_all("td")
                if len(cells) != 3:
                    continue
                provisional = bool(row.select(".provisional-badge")) or (
                    "provisional-row" in (row.get("class") or [])
                )
                lugar_tag = cells[1].find("strong")
                lugar = clean_text((lugar_tag or cells[1]).get_text())
                for item in cells[2].select("div.location-item"):
                    location = clean_text(item.select_one(".location-name").get_text())
                    horario = clean_text(item.select_one(".schedule-time").get_text())
                    if PLACEHOLDER_LOCATION_RE.match(location):
                        continue
                    item_lugar = lugar
                    prefixed = LOCATION_PLACE_PREFIX_RE.match(location)
                    if prefixed:
                        item_lugar, location = prefixed.groups()
                    stops.append(
                        {
                            "area": area_name,
                            "fecha": fecha,
                            "concello": clean_text(cells[0].get_text()),
                            "lugar": item_lugar,
                            "direccion": location,
                            "place_text": strip_mobile_unit_prefix(location),
                            "horario": horario,
                            "provisional": provisional,
                        }
                    )
    return stops


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape every upcoming donation-bus stop."""
    soup = BeautifulSoup(SESSION.get(URL_MOBILE_POINTS).text, features="lxml")
    df = pd.DataFrame(parse_mobile_points(soup))
    df["url"] = URL_MOBILE_POINTS
    return df


def lit_light_colour(card: Image.Image):
    """Return the (status, level, label) of a card's lit light, or None."""
    hues = [
        hue
        for hue, saturation, value in card.convert("HSV").get_flattened_data()
        if saturation > LIT_MIN_SATURATION and value > LIT_MIN_VALUE
    ]
    if len(hues) < LIT_MIN_PIXELS:
        return None
    median_hue = sorted(hues)[len(hues) // 2]
    return next(
        (
            status
            for (low, high), status in BLOOD_LEVEL_COLOURS
            if low <= median_hue < high
        ),
        None,
    )


def parse_blood_levels_image(image: Image.Image) -> list[dict]:
    """Read every blood type's level off the semáforo image.

    The image is a 4x2 grid of cards (see BLOOD_LEVEL_IMAGE_TYPES), each with
    four grey lights of which one is lit; the lit light's hue says the
    level (see BLOOD_LEVEL_COLOURS). Cards with no recognizable lit light
    are left out rather than guessed.
    """
    width, height = image.size
    blood_levels = []
    for index, blood_type in enumerate(BLOOD_LEVEL_IMAGE_TYPES):
        row, column = divmod(index, 4)
        card = image.crop(
            (
                column * width // 4,
                row * height // 2,
                (column + 1) * width // 4,
                (row + 1) * height // 2,
            )
        )
        colour = lit_light_colour(card)
        if colour is None:
            continue
        status, level, label = colour
        blood_levels.append(
            {"blood_type": blood_type, "status": status, "level": level, "label": label}
        )
    return blood_levels


def blood_levels_image_url(soup: BeautifulSoup) -> str | None:
    """Find the current semáforo image (its filename carries its date)."""
    img = soup.find("img", src=re.compile(r"/Semaforo_[^/]*\.png$", re.IGNORECASE))
    return urllib.parse.urljoin(URL_BASE, img["src"]) if img else None


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape the "Semáforo" blood-reserve levels from its image."""
    soup = BeautifulSoup(SESSION.get(URL_BLOOD_LEVELS).text, features="lxml")
    image_url = blood_levels_image_url(soup)
    if image_url is None:
        return pd.DataFrame(columns=["blood_type", "status", "level", "label"])
    image = Image.open(io.BytesIO(SESSION.get(image_url).content)).convert("RGB")
    return pd.DataFrame(parse_blood_levels_image(image))
