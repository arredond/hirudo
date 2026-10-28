"""Crawl donasturias.org (Centro Comunitario de Sangre y Tejidos de Asturias)
and retrieve fixed and mobile blood donation spots and blood-reserve levels.

Fixed points are the centres listed on one page ("Puntos fijos"), each with a
free-text weekly schedule and a Google Maps embed. The embed carries the
centre's coordinates, so most points need no geocoding.

Mobile points come from The Events Calendar's REST API: one event per locality
and day, whose description has one paragraph per spot ("09.00-14.00 |
<strong>La Arena.</strong> C/ Menéndez Pelayo…"). The calendar also holds the
fixed centres' own days, titled "PUNTOS FIJOS", which are left out here since
the fixed points come from their page.

Blood levels ("Estado de las reservas de hematíes") are one gauge image per
blood type, with no legend and no text. The blood type is in the image's
filename; the level is read off the image: the needle's angle picks the rim
band it points at, and that band's colour is the status.
"""

import colorsys
import io
import math
import re
import urllib.parse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from PIL import Image
from utils.crawl import comunidad_valenciana

URL_BASE = "https://donasturias.org/"
URL_FIXED_POINTS = urllib.parse.urljoin(URL_BASE, "puntos-fijos/")
URL_EVENTS_API = urllib.parse.urljoin(URL_BASE, "wp-json/tribe/events/v1/events")

# The calendar's own title for its fixed-centre days (see module docstring).
FIXED_POINTS_EVENT_TITLE = "puntos fijos"

FIXED_POINT_COLUMNS = [
    "name",
    "direccion",
    "localidad",
    "codigo_postal",
    "horario",
    "latitude",
    "longitude",
]
MOBILE_POINT_COLUMNS = ["localidad", "lugar", "direccion", "fecha", "horario", "url"]

# A spot's hours, before its "|": "09.00-14.00 y 16.00-21.00" (dots as the
# separator, though a colon is accepted too).
TIME_RANGE_RE = re.compile(r"(\d{1,2})[.:](\d{2})\s*-\s*(\d{1,2})[.:](\d{2})")

# A fixed point's postcode line: "Calle Donato Argüelles, 20, 33206 Gijón, Asturias".
POSTCODE_RE = re.compile(r"(\d{5}),?\s+([^,]+),\s*Asturias")

# Google Maps embed coordinates: "ll=lat,lng" (map centre, marker at the place)
# or "!2d<lng>!3d<lat>" (the place's own marker).
EMBED_LL_RE = re.compile(r"[?&;]ll=(-?\d+\.\d+),(-?\d+\.\d+)")
EMBED_PLACE_RE = re.compile(r"!2d(-?\d+\.\d+)!3d(-?\d+\.\d+)")

# Spanish particles that str.title() wrongly capitalizes mid-name.
SPANISH_PARTICLE_RE = re.compile(r"(?<=\s)(?:De|Del|Y|La|En)(?=\s)")

# Gauge image filenames: blood type letters, "mas" for Rh+ ("omas230-1.jpg" is
# O+, "o-90.jpg" is O-), then a number that isn't the level.
GAUGE_FILENAME_RE = re.compile(
    r"^(AB|A|B|O)(mas)?\d*(?:-\d+)*\.(?:jpe?g|png)$", re.IGNORECASE
)

# Needle and rim pixel rules. The gauge is a round dial: the hub is a blue dot,
# the needle a red line from the hub, and the coloured bands sit on the rim.
GAUGE_RIM_FRACTION = 0.9  # rim radius, as a fraction of half the image's side
NEEDLE_START = 0.2  # the needle is searched from this fraction of the rim radius
NEEDLE_END = 0.95
NEEDLE_MIN_RUN = 0.3  # ... and must be at least this long to count
RIM_SAMPLE = (
    0.93  # where the coloured band is read: near the rim, past the needle's tip
)
RAY_STEP_DEGREES = 0.5

# Rim band hue (degrees) -> (status, level, label). Three bands, like Madrid's
# and Castilla y León's: red (urgent), yellow, green (good).
RED_BAND = ("red", 1, "Nivel rojo")
YELLOW_BAND = ("yellow", 2, "Nivel amarillo")
GREEN_BAND = ("green", 3, "Nivel verde")

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"


def clean_text(text: str) -> str:
    """Collapse whitespace and drop the invisible marks some pages carry."""
    return " ".join(text.replace("\u200b", "").replace("\u200e", "").split())


def title_name(text: str) -> str:
    """Title-case an all-caps page heading, keeping its particles lowercase."""
    return SPANISH_PARTICLE_RE.sub(lambda match: match.group().lower(), text.title())


def coordinates_from_embed(src: str) -> tuple[float, float] | tuple[None, None]:
    """Pull (latitude, longitude) out of a Google Maps embed URL, if it has one."""
    match = EMBED_LL_RE.search(src)
    if match:
        latitude, longitude = match.groups()
        return float(latitude), float(longitude)
    match = EMBED_PLACE_RE.search(src)
    if match:
        longitude, latitude = match.groups()
        return float(latitude), float(longitude)
    return None, None


def parse_fixed_point(heading: BeautifulSoup) -> dict:
    """Parse one fixed centre: its <h5> name and the paragraphs up to the next.

    The paragraphs run address, schedule (one or more lines), an image and a
    Google Maps iframe. The address line carries the postcode and town.
    """
    texts, src = [], None
    for sibling in heading.find_next_siblings():
        if sibling.name == "h5":
            break
        iframe = sibling.find("iframe")
        if iframe is not None:
            src = iframe.get("src")
        text = clean_text(sibling.get_text(" "))
        if text and sibling.find("img") is None and iframe is None:
            texts.append(text)

    address = texts[0] if texts else None
    postcode = POSTCODE_RE.search(address or "")
    latitude, longitude = coordinates_from_embed(src or "")
    return {
        "name": title_name(clean_text(heading.get_text())),
        "direccion": address,
        "localidad": postcode.group(2).strip() if postcode else None,
        "codigo_postal": postcode.group(1) if postcode else None,
        "horario": " / ".join(texts[1:]) or None,
        "latitude": latitude,
        "longitude": longitude,
    }


def parse_fixed_points(soup: BeautifulSoup) -> list[dict]:
    """Parse every fixed centre on the "Puntos fijos" page (one <h5> each)."""
    return [parse_fixed_point(heading) for heading in soup.select("main h5")]


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape the fixed donation centres from the "Puntos fijos" page."""
    soup = BeautifulSoup(SESSION.get(URL_FIXED_POINTS).text, features="lxml")
    df = pd.DataFrame(parse_fixed_points(soup), columns=FIXED_POINT_COLUMNS)
    df["url"] = URL_FIXED_POINTS
    return df


def format_time_ranges(hours: str) -> str | None:
    """Turn "09.00-14.00 y 16.00-21.00" into "09:00 a 14:00, 16:00 a 21:00"."""
    ranges = TIME_RANGE_RE.findall(hours)
    if not ranges:
        return None
    return ", ".join(
        f"{int(open_h):02d}:{open_m} a {int(close_h):02d}:{close_m}"
        for open_h, open_m, close_h, close_m in ranges
    )


def parse_spot(paragraph, town: str, fecha: str, url: str) -> dict | None:
    """Parse one spot paragraph ("HH.MM-HH.MM | <strong>Venue.</strong> Address.").

    The venue is the bold text when there is one, else the whole place text
    (cutting at the first ". " would split abbreviations like "Avda. Juan
    Sitges"). Returns None for paragraphs that aren't a spot.
    """
    text = clean_text(paragraph.get_text())
    hours, separator, place = text.partition("|")
    horario = format_time_ranges(hours)
    place = place.strip()
    if not separator or horario is None or not place:
        return None

    bold = paragraph.find("strong")
    venue = clean_text(bold.get_text()) if bold is not None else ""
    return {
        "localidad": town,
        "lugar": venue.strip(" .") or place.rstrip(". "),
        "direccion": place,
        "fecha": fecha,
        "horario": horario,
        "url": url,
    }


def parse_event(event: dict) -> list[dict]:
    """Flatten one calendar event (one town and day) into its spots.

    Each description paragraph is one spot; a spot open morning and afternoon
    keeps both ranges in its one "horario".
    """
    town = clean_text(BeautifulSoup(event["title"], features="lxml").get_text())
    fecha = pd.Timestamp(event["start_date"]).strftime("%d/%m/%Y")
    description = BeautifulSoup(event["description"], features="lxml")
    spots = [
        parse_spot(paragraph, town, fecha, event["url"])
        for paragraph in description.find_all("p")
    ]
    return [spot for spot in spots if spot is not None]


def is_fixed_points_event(event: dict) -> bool:
    """Tell the calendar's "PUNTOS FIJOS" days (the fixed centres) apart."""
    title = clean_text(BeautifulSoup(event["title"], features="lxml").get_text())
    return title.casefold() == FIXED_POINTS_EVENT_TITLE


def scrape_mobile_points(today=None) -> pd.DataFrame:
    """Scrape every mobile spot from today on, one row per spot.

    Starts from today (Madrid time) and follows next_rest_url to the last
    page. Fixed-centre days are skipped (see is_fixed_points_event).
    """
    today = today or comunidad_valenciana.madrid_today()
    params = {"per_page": 50, "start_date": today.strftime("%Y-%m-%d")}
    url = URL_EVENTS_API
    events = []
    while url:
        data = SESSION.get(url, params=params).json()
        events.extend(data.get("events", []))
        url = data.get("next_rest_url")
        params = None  # next_rest_url already carries every query param
    spots = []
    for event in events:
        if not is_fixed_points_event(event):
            spots.extend(parse_event(event))
    return pd.DataFrame(spots, columns=MOBILE_POINT_COLUMNS)


def gauge_blood_type(filename: str) -> str | None:
    """Read a gauge image's blood type from its filename ("omas230-1.jpg" -> "0+")."""
    match = GAUGE_FILENAME_RE.match(filename)
    if not match:
        return None
    group, rh_positive = match.group(1).upper(), match.group(2)
    return ("0" if group == "O" else group) + ("+" if rh_positive else "-")


def is_needle_pixel(rgb: tuple) -> bool:
    """A needle is a red-orange line: strong red, little green and blue."""
    red, green, blue = rgb
    return red > 150 and green < 120 and blue < 110 and red - green > 90


def find_hub(image: Image.Image) -> tuple[float, float]:
    """Centre of the gauge's blue hub; falls back to the image's centre."""
    pixels = image.load()
    width, height = image.size
    xs, ys = [], []
    for y in range(height):
        for x in range(width):
            red, green, blue = pixels[x, y]
            if blue > red + 60 and blue > green + 30:
                xs.append(x)
                ys.append(y)
    if not xs:
        return (width - 1) / 2, (height - 1) / 2
    return sum(xs) / len(xs), sum(ys) / len(ys)


def angle_difference(first: float, second: float) -> float:
    """Smallest difference between two angles in degrees."""
    return abs((first - second + 180) % 360 - 180)


def needle_angle(image: Image.Image, hub: tuple[float, float], rim: float):
    """Angle (degrees, counterclockwise from 3 o'clock) of the needle, or None.

    Casts a ray from the hub at every RAY_STEP_DEGREES and measures how far
    the needle colour runs continuously from near the hub; the longest run
    is the needle, averaged over the neighbouring rays that run as far.
    """
    pixels = image.load()
    width, height = image.size
    hub_x, hub_y = hub
    start, end = NEEDLE_START * rim, NEEDLE_END * rim
    runs = []
    for step in range(round(360 / RAY_STEP_DEGREES)):
        angle = step * RAY_STEP_DEGREES
        theta = math.radians(angle)
        last_hit = None
        radius = start
        while radius < end:
            x = round(hub_x + radius * math.cos(theta))
            y = round(hub_y - radius * math.sin(theta))
            if not (0 <= x < width and 0 <= y < height):
                break
            if is_needle_pixel(pixels[x, y]):
                last_hit = radius
            elif radius - (start if last_hit is None else last_hit) > 2.0:
                break
            radius += 0.5
        runs.append((last_hit - start if last_hit is not None else 0.0, angle))

    best_run, best_angle = max(runs)
    if best_run < NEEDLE_MIN_RUN * rim:
        return None
    near = [
        angle
        for run, angle in runs
        if run >= best_run - 2 and angle_difference(angle, best_angle) <= 3
    ]
    sine = sum(math.sin(math.radians(angle)) for angle in near)
    cosine = sum(math.cos(math.radians(angle)) for angle in near)
    return math.degrees(math.atan2(sine, cosine)) % 360


def band_for_hue(hue: float):
    """Map a rim band's hue (degrees) to its (status, level, label)."""
    if hue < 25 or hue >= 340:
        return RED_BAND
    if hue < 70:
        return YELLOW_BAND
    if 70 <= hue < 180:
        return GREEN_BAND
    return None


def gauge_level(image: Image.Image):
    """Read a gauge's level: the rim band under its needle, or None.

    Three rim samples around the needle's angle are classified and the
    majority band kept, so a needle sitting on a band edge isn't decided by
    one anti-aliased pixel.
    """
    rim = min(image.size) / 2 * GAUGE_RIM_FRACTION
    hub = find_hub(image)
    angle = needle_angle(image, hub, rim)
    if angle is None:
        return None

    pixels = image.load()
    votes = []
    for offset in (-2, 0, 2):
        theta = math.radians(angle + offset)
        x = round(hub[0] + RIM_SAMPLE * rim * math.cos(theta))
        y = round(hub[1] - RIM_SAMPLE * rim * math.sin(theta))
        red, green, blue = (channel / 255 for channel in pixels[x, y])
        hue, saturation, _ = colorsys.rgb_to_hsv(red, green, blue)
        if saturation > 0.5:
            votes.append(band_for_hue(hue * 360))
    votes = [vote for vote in votes if vote is not None]
    if not votes:
        return None
    winner = max(set(votes), key=votes.count)
    return winner if votes.count(winner) >= 2 else None


def parse_gauge_images(gauges: list[tuple[str, Image.Image]]) -> list[dict]:
    """Read every blood type's level off its gauge image.

    Gauges whose needle or band can't be read are left out rather than guessed.
    """
    blood_levels = []
    for blood_type, image in gauges:
        band = gauge_level(image.convert("RGB"))
        if band is None:
            continue
        status, level, label = band
        blood_levels.append(
            {"blood_type": blood_type, "status": status, "level": level, "label": label}
        )
    return blood_levels


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape the "Estado de las reservas de hematíes" gauges from the homepage."""
    soup = BeautifulSoup(SESSION.get(URL_BASE).text, features="lxml")
    gauges = []
    seen = set()
    for img in soup.find_all("img", src=True):
        filename = img["src"].rsplit("/", 1)[-1]
        blood_type = gauge_blood_type(filename)
        if blood_type is None or blood_type in seen:
            continue
        seen.add(blood_type)
        image_url = urllib.parse.urljoin(URL_BASE, img["src"])
        image = Image.open(io.BytesIO(SESSION.get(image_url).content))
        gauges.append((blood_type, image))
    return pd.DataFrame(
        parse_gauge_images(gauges), columns=["blood_type", "status", "level", "label"]
    )
