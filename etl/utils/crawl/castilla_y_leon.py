"""Crawl Castilla y León pages and retrieve fixed and mobile blood donation spots."""

import re
import urllib.parse
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL_BASE = "https://www.centrodehemoterapiacyl.es/"
URL_POINTS_INDEX = urllib.parse.urljoin(URL_BASE, "puntos-de-donacion/")

# The province pages aren't linked anywhere in a machine-readable way, so the
# list is hardcoded. Each page has the same layout: a fixed-point table
# followed by a mobile-points table.
PROVINCES = [
    "avila",
    "burgos",
    "leon",
    "palencia",
    "salamanca",
    "segovia",
    "soria",
    "valladolid",
    "zamora",
]

# The homepage's "Niveles de sangre actuales" widget renders one box per
# blood type, with the urgency level spelled out in its title attribute
# (e.g. title="Nivel Bajo AB-"). Mapping to (status, level), level 1 = most
# urgent, matching the scheme used for Comunidad de Madrid.
BLOOD_LEVEL_STATUS = {
    "Óptimo": ("stable", 3),
    "Medio": ("soon", 2),
    "Bajo": ("urgent", 1),
}

# A maps.app.goo.gl short link's first redirect (before Google's consent
# flow) already carries the place's coordinates: a precise pin as
# "!3d<lat>!4d<lon>" when available, else the viewport center as
# "@<lat>,<lon>". Checking the precise pair first avoids falling back to the
# coarser viewport center when both are present.
GMAPS_PIN_RE = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
GMAPS_VIEWPORT_RE = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")

DATE_RE = re.compile(r"\d{2}/\d{2}/\d{4}")

# The homepage 403s on requests' default User-Agent (it serves the Apache
# placeholder page instead), unlike the province subpages, which don't care.
# Setting a normal browser UA avoids that inconsistency altogether.
SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
)


def province_url(province: str) -> str:
    """Build the donation-points page URL for a province slug."""
    return urllib.parse.urljoin(URL_POINTS_INDEX, f"{province}/")


def resolve_gmaps_coords(short_url: str) -> tuple[float, float]:
    """Resolve a maps.app.goo.gl short link to (latitude, longitude).

    A single non-redirect-following GET is enough: the short link's first
    redirect Location header already contains the coordinates, so there is
    no need to follow it into Google's consent page (and no Geocoding API
    call, or its cost, is needed either).
    """
    response = SESSION.get(short_url, allow_redirects=False)
    location = response.headers["Location"]
    match = GMAPS_PIN_RE.search(location) or GMAPS_VIEWPORT_RE.search(location)
    if not match:
        raise ValueError(f"Could not extract coordinates from redirect: {location}")
    return float(match.group(1)), float(match.group(2))


def parse_fixed_points(table, province: str) -> list[dict]:
    """Parse a province's fixed-point table.

    Each fixed point starts with a rowspan'd cell holding its name, address,
    and a Google Maps short link; its schedule is listed either alongside
    that same cell (a single-day schedule) or across the following plain
    rows, until the next rowspan'd cell starts a new point or a closing
    colspan note row is reached.
    """
    points = []
    current = None
    for row in table.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if not cells or cells[0].name == "th":
            continue

        first = cells[0]
        if first.has_attr("rowspan"):
            if current:
                points.append(current)
            gmaps_link = first.find("a")
            lines = [
                line
                for line in first.stripped_strings
                if line.strip() and line.strip() != "Ver Ubicación"
            ]
            current = {
                "name": lines[0],
                "direccion": ", ".join(lines[1:]),
                "gmaps_url": gmaps_link.attrs["href"] if gmaps_link else None,
                "province": province,
                "schedule": [],
            }
            schedule_cells = cells[1:]
        elif current is not None and not first.has_attr("colspan"):
            schedule_cells = cells
        else:
            schedule_cells = []

        if len(schedule_cells) >= 2:
            day = schedule_cells[0].get_text(strip=True)
            hours = schedule_cells[1].get_text(strip=True)
            if day and hours:
                current["schedule"].append(f"{day}: {hours}")

    if current:
        points.append(current)

    for point in points:
        point["horario"] = "; ".join(point.pop("schedule"))
    return points


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape every province's fixed point(s), resolving coordinates from
    their Google Maps short link (no geocoding API call needed).

    Most provinces have one fixed-point table followed by the mobile-points
    table (2 tables total), but a province can have more than one fixed
    point — e.g. León also lists "Hospital del Bierzo" — as an extra table
    of the same shape. The mobile-points table is always last, so every
    table before it is treated as a fixed point.
    """
    fixed_points = []
    for province in PROVINCES:
        url = province_url(province)
        html = SESSION.get(url).text
        soup = BeautifulSoup(html, features="lxml")
        tables = soup.find("div", {"class": "entry-content"}).find_all("table")

        for table in tables[:-1]:
            for point in parse_fixed_points(table, province):
                if point["gmaps_url"]:
                    point["latitude"], point["longitude"] = resolve_gmaps_coords(
                        point["gmaps_url"]
                    )
                point["url"] = url
                fixed_points.append(point)

    return pd.DataFrame(fixed_points)


def clean_mobile_point_row(row: pd.Series) -> pd.Series:
    """Split the combined "Fecha - Ubicación" cell and strip the trailing
    "Ver Ubicación" link text pandas.read_html leaves in "direccion"."""
    fecha_ubicacion = row["Fecha - Ubicación"]
    date_match = DATE_RE.search(fecha_ubicacion)
    if date_match:
        row["fecha"] = date_match.group()
        row["ubicacion"] = fecha_ubicacion[date_match.end() :].strip()
    else:
        row["fecha"] = None
        row["ubicacion"] = fecha_ubicacion
    row["direccion"] = row["direccion"].replace("Ver Ubicación", "").strip()
    return row


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and return all mobile donation points as a DataFrame.

    The mobile-points table is always the last one on the page, regardless
    of how many fixed-point tables precede it (see scrape_fixed_points).
    """
    province_frames = []
    for province in PROVINCES:
        html = SESSION.get(province_url(province)).text
        soup = BeautifulSoup(html, features="lxml")
        tables = soup.find("div", {"class": "entry-content"}).find_all("table")
        if len(tables) < 2:
            continue  # no mobile points listed for this province

        df = pd.read_html(StringIO(str(tables[-1])))[0]
        df = df.rename(
            columns={
                "Campañas de donación": "campana",
                "Horario": "horario",
                "Dirección": "direccion",
            }
        )
        df = df.apply(clean_mobile_point_row, axis=1)
        df["province"] = province
        province_frames.append(
            df[["campana", "fecha", "ubicacion", "horario", "direccion", "province"]]
        )

    return pd.concat(province_frames, ignore_index=True)


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape the "Niveles de sangre actuales" blood-reserve levels widget."""
    html = SESSION.get(URL_BASE).text
    soup = BeautifulSoup(html, features="lxml")

    blood_levels = []
    for box in soup.find_all("div", title=re.compile(r"^Nivel ")):
        level_word, blood_type = box["title"].removeprefix("Nivel ").split(" ", 1)
        status, level = BLOOD_LEVEL_STATUS[level_word]
        blood_levels.append(
            {
                "blood_type": blood_type,
                "status": status,
                "level": level,
                "label": box["title"],
            }
        )

    return pd.DataFrame(blood_levels)
