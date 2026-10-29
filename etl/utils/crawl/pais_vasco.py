"""Crawl donantesdesangre.eus (Euskadi) and retrieve fixed and mobile blood
donation spots and blood-reserve levels.

The "¿Dónde donar?" page loads each province's spots one day at a time from
a small endpoint (its calendar selector just changes the date), so the ETL
asks for every day in a window ahead (DAYS_AHEAD). Each spot is a town, a
place, a time range and a Google Maps link with the spot's exact
coordinates — no geocoding needed.

There's no separate list of fixed points: the permanent centres
(FIXED_POINT_NAMES) and the health centres and hospitals the stops visit
(is_fixed_point) show up in those same daily listings, so their rows are
split off into a day-by-day schedule, like Comunidad Valenciana's.

Blood levels come from another endpoint that renders one blood-bag image
per type; the image's filename says the level (BLOOD_LEVEL_STATUS).
"""

import datetime
import functools
import re
import urllib.parse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from utils.crawl import comunidad_valenciana, crawl

URL_BASE = "https://donantesdesangre.eus/"
URL_POINTS = urllib.parse.urljoin(URL_BASE, "donde-donar/")
URL_DAY_LISTING = urllib.parse.urljoin(
    URL_BASE, "wp-content/themes/hello-elementor/extracciones/index.php"
)
URL_BLOOD_LEVELS = urllib.parse.urljoin(
    URL_BASE, "wp-content/themes/hello-elementor/niveles-sangre/index.php"
)

PROVINCES = ["Araba", "Bizkaia", "Gipuzkoa"]

# The permanent centres publish their schedule about two months ahead;
# mobile stops, three to five weeks.
DAYS_AHEAD = 60

# Listing place text -> fixed point name, for the permanent centres.
FIXED_POINT_NAMES = {
    "GALDAKAO Planta 0-CVTTH": "Centro Vasco de Transfusión y Tejidos Humanos (Galdakao)",
    "Manuel Lekuona Donostia": "Punto de donación Manuel Lekuona (Donostia)",
    "AMBULATORIO OLAGUIBEL": "Ambulatorio Olaguibel (Vitoria-Gasteiz)",
}

# Spots at a health centre or hospital, in Spanish or Basque
# ("Anbulategia/Ambulatorio", "USANSOLO ospitalea"), are fixed points too.
FIXED_POINT_RE = re.compile(r"ambulatorio|anbulategi|hospital|ospitale", re.IGNORECASE)

# "27-10 de 8:30 a 14:30"
TIME_RANGE_RE = re.compile(r"de (\d{1,2}):(\d{2}) a (\d{1,2}):(\d{2})")

GMAPS_PLACE_RE = re.compile(r"/maps/place/(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")

# "Bilbao Bombero Etxaniz - Solo Plasma/Cita", "HOSPITAL ARRASATE-COLECTA PLASMAS"
PLASMA_ONLY_RE = re.compile(r"solo\s+plasma|colecta\s+plasmas?", re.IGNORECASE)

# Blood-bag image filename -> (status, level, label). The bag's fill and
# droplet colour show the level; the labels are the page's own legend.
BLOOD_LEVEL_STATUS = {
    "Reserva-Sangre-01.svg": ("green", 3, "Dona en la próxima colecta"),
    "Reserva-Sangre-02.svg": ("yellow", 2, "Dona en 2 o 3 días"),
    "Reserva-Sangre-03.svg": ("red", 1, "Dona urgente"),
}

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace (the source doubles some spaces)."""
    return " ".join(text.split())


def parse_day_listing(html: str, date: datetime.date) -> list[dict]:
    """Parse one province's spots for one day.

    Each spot is a <div class="contenedor_*">: the town ("Galdakao:"), the
    place, "DD-MM de H:MM a H:MM", and a link to the spot on Google Maps
    whose text is its street address.
    """
    soup = BeautifulSoup(html, features="lxml")
    spots = []
    for container in soup.select("div[class^=contenedor_]"):
        texts = container.find_all("span", class_="lugar")
        link = container.find("a", class_="direccion")
        hours = TIME_RANGE_RE.search(container.get_text(" "))
        coords = GMAPS_PLACE_RE.search(crawl.attribute(link, "href")) if link else None
        if len(texts) < 2 or not hours:
            continue
        open_h, open_m, close_h, close_m = hours.groups()
        spots.append(
            {
                "localidad": normalize_whitespace(texts[0].get_text()).rstrip(":"),
                "lugar": normalize_whitespace(texts[1].get_text()),
                "direccion": normalize_whitespace(link.get_text()) if link else None,
                "fecha": date.strftime("%d/%m/%Y"),
                "horario": f"{int(open_h):02d}:{open_m}-{int(close_h):02d}:{close_m}",
                "latitude": float(coords.group(1)) if coords else None,
                "longitude": float(coords.group(2)) if coords else None,
            }
        )
    return spots


@functools.cache
def fetch_listings(today: datetime.date) -> pd.DataFrame:
    """Fetch every province's spots for each day from today to DAYS_AHEAD.

    Cached, since fixed and mobile points both come out of the same
    listings. Exact repeats (the source lists some spots twice) are dropped.
    """
    spots = []
    for days in range(DAYS_AHEAD):
        date = today + datetime.timedelta(days=days)
        for province in PROVINCES:
            response = SESSION.get(
                URL_DAY_LISTING,
                params={
                    "idioma": "ES",
                    "provincia": province,
                    "fechaInicio": date.strftime("%Y/%m/%d"),
                },
            )
            for spot in parse_day_listing(response.text, date):
                spots.append({"province": province, **spot})
    return pd.DataFrame(spots).drop_duplicates(ignore_index=True)


def merge_same_day(df: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    """Join each spot's same-day time ranges ("09:15-14:00, 16:15-21:00")."""
    return df.groupby(keys + ["fecha"], as_index=False, sort=False, dropna=False).agg(
        horario=(
            "horario",
            lambda ranges: comunidad_valenciana.join_time_ranges(list(ranges)),
        )
    )


def is_fixed_point(lugar: str) -> bool:
    """Tell a permanent centre or health centre/hospital from a mobile stop."""
    return lugar in FIXED_POINT_NAMES or bool(FIXED_POINT_RE.search(lugar))


def fixed_point_name(lugar: str, localidad: str) -> str:
    """Name a fixed point: its FIXED_POINT_NAMES name, or "<place> (<town>)",
    since several towns list theirs as just "Anbulategia/Ambulatorio"."""
    return FIXED_POINT_NAMES.get(lugar) or f"{lugar} ({localidad})"


def scrape_fixed_points(today: datetime.date | None = None) -> pd.DataFrame:
    """Build the fixed points (see is_fixed_point) from the daily listings.

    Each gets its day-by-day schedule ([(fecha, horario)], for dated
    opening_hours) and a summary of its next days as horario. Most health
    centres are only visited on a day or two in the window, and their
    opening_hours says exactly that. Plasma-only ones (e.g. "HOSPITAL
    ARRASATE-COLECTA PLASMAS") are flagged.
    """
    today = today or comunidad_valenciana.madrid_today()
    df = fetch_listings(today)
    df = df[df["lugar"].apply(is_fixed_point)]
    keys = ["lugar", "localidad", "direccion", "latitude", "longitude"]
    days = merge_same_day(df, keys)

    points = []
    for (lugar, localidad, direccion, latitude, longitude), rows in days.groupby(
        keys, sort=False, dropna=False
    ):
        schedule = list(zip(rows["fecha"], rows["horario"], strict=True))
        points.append(
            {
                "name": fixed_point_name(lugar, localidad),
                "localidad": localidad,
                "direccion": direccion,
                "latitude": latitude,
                "longitude": longitude,
                "schedule": schedule,
                "horario": comunidad_valenciana.summarize_schedule(schedule, today),
                "plasma_only": bool(PLASMA_ONLY_RE.search(lugar)),
                "url": URL_POINTS,
            }
        )
    return pd.DataFrame(points)


def scrape_mobile_points(today: datetime.date | None = None) -> pd.DataFrame:
    """Scrape every mobile stop in the window (everything but fixed points).

    A stop open morning and afternoon is listed twice; those are merged into
    one row per day. Plasma-only stops ("Solo Plasma/Cita") are flagged.
    """
    today = today or comunidad_valenciana.madrid_today()
    df = fetch_listings(today)
    df = df[~df["lugar"].apply(is_fixed_point)]
    df = merge_same_day(
        df, ["province", "localidad", "lugar", "direccion", "latitude", "longitude"]
    )
    df["plasma_only"] = df["lugar"].str.contains(PLASMA_ONLY_RE)
    df["url"] = URL_POINTS
    return df


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape the "Niveles de sangre actuales" blood-bag images."""
    response = SESSION.get(URL_BLOOD_LEVELS, params={"idioma": "ES"})
    soup = BeautifulSoup(response.text, features="lxml")
    blood_levels = []
    for img in soup.select("img.bolsa_sangre"):
        filename = crawl.attribute(img, "src").rsplit("/", 1)[-1]
        if filename not in BLOOD_LEVEL_STATUS:
            continue
        status, level, label = BLOOD_LEVEL_STATUS[filename]
        blood_levels.append(
            {"blood_type": img["alt"], "status": status, "level": level, "label": label}
        )
    return pd.DataFrame(
        blood_levels, columns=["blood_type", "status", "level", "label"]
    )
