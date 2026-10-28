"""Crawl the Servicio Andaluz de Salud's donation centres (Andalucía).

Each of the eight provinces has one Centro de transfusión, tejidos y células
(CTTC), each with its own page on sspa.juntadeandalucia.es, all built from the
same template. A page gives:

- the centre's own postal address and one repeating weekly timetable: the
  province's fixed donation point, and
- a "Se puede donar en..." table of the province's upcoming mobile collections
  (colectas): date, town, venue and hours, a few weeks ahead.

Neither part carries coordinates, so every point is geocoded from its text
(see main.py). The pages publish no blood-reserve levels, so there's no
scrape_blood_levels() here. Mobile collections aren't split by donation type
(sangre or plasma) either, so those flags are left unset.
"""

import functools
import re
import urllib.parse
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup
from utils.crawl import crawl

URL_CENTERS = (
    "https://www.sspa.juntadeandalucia.es/servicioandaluzdesalud/"
    "el-sas/servicios-y-centros/informacion-por-centros/"
)

# Each province's CTTC page, by the ID at the end of its URL (linked from
# https://www.juntadeandalucia.es/temas/salud/servicios/donacion-sangre.html).
CENTER_IDS = {
    "Almería": 20585,
    "Cádiz": 16502,
    "Córdoba": 16503,
    "Granada": 16504,
    "Huelva": 16505,
    "Jaén": 16506,
    "Málaga": 16507,
    "Sevilla": 16508,
}

# The weekday names the timetable prints, as OSM opening_hours codes.
WEEKDAY_CODES = {
    "Lunes": "Mo",
    "Martes": "Tu",
    "Miércoles": "We",
    "Jueves": "Th",
    "Viernes": "Fr",
    "Sábado": "Sa",
    "Domingo": "Su",
}

# One "from - to" range in a mobile stop's hours. The source writes them every
# which way: "09:00 - 14:30", "09:00 a 14:30", "DE 17,30 a 21,00", "17 a 21
# HORAS", "10 a 14 Y 17 a 21 HORAS"; several ranges can share a day, split by
# " y " or " / ".
HOURS_RANGE_RE = re.compile(
    r"(\d{1,2})(?:[:.,](\d{2}))?\s*(?:a|A|-)\s*(\d{1,2})(?:[:.,](\d{2}))?"
)

MOBILE_COLUMNS = {
    "Fecha": "fecha",
    "Localidad": "localidad",
    "Lugar": "lugar",
    "Hora": "horario",
}

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"


def center_url(province: str) -> str:
    """Build a province's CTTC page URL."""
    return urllib.parse.urljoin(URL_CENTERS, str(CENTER_IDS[province]))


@functools.cache
def fetch_center(province: str) -> BeautifulSoup:
    """Fetch and parse a province's CTTC page.

    Cached, since the fixed point and the mobile collections both come out of
    the same page.
    """
    html = SESSION.get(center_url(province)).text
    return BeautifulSoup(html, features="lxml")


def parse_fixed_point(soup: BeautifulSoup) -> dict:
    """Parse a CTTC page's own address and weekly timetable.

    The timetable is one <tr> per weekday, with that day's ranges as <li>s.
    Days the page doesn't list are closed.
    """
    schedule = []
    for row in soup.select_one("table.center-schedule__table").select("tr"):
        day, hours = row.find_all("td")
        ranges = [item.get_text(" ", strip=True) for item in hours.select("li")]
        schedule.append((day.get_text(strip=True), " | ".join(ranges)))

    postal = soup.select_one(".center-address__address-postal")
    direccion = postal.select_one(".field--name-field-direccion").get_text(
        " ", strip=True
    )
    codigo_postal = postal.select_one(".field--name-field-codigo-postal").get_text(
        strip=True
    )
    localidad = postal.select_one(".field--name-field-municipio").get_text(strip=True)

    return {
        "name": soup.select_one(".center-label__title--main").get_text(" ", strip=True),
        "localidad": crawl.title_name(localidad),
        "direccion": f"{direccion}, {codigo_postal}",
        "horario": "; ".join(f"{day} {hours}" for day, hours in schedule if hours),
        "schedule": [
            (WEEKDAY_CODES[day], hours)
            for day, hours in schedule
            if day in WEEKDAY_CODES
        ],
    }


def normalize_hours(horario: str) -> str:
    """Rewrite a mobile stop's hours as "HH:MM - HH:MM" ranges joined by " | ".

    Text with no time range at all (e.g. "DESDE LAS 17,00 HORAS") is returned
    unchanged, so parse_mobile_hours logs it downstream.
    """
    ranges = []
    for open_h, open_m, close_h, close_m in HOURS_RANGE_RE.findall(horario):
        ranges.append(
            f"{int(open_h):02d}:{open_m or '00'} - {int(close_h):02d}:{close_m or '00'}"
        )
    return " | ".join(ranges) if ranges else horario


def parse_mobile_points(soup: BeautifulSoup, province: str) -> pd.DataFrame:
    """Parse a CTTC page's "Se puede donar en..." table of mobile collections.

    The source writes dates as "DD-MM-YYYY"; they're rebuilt as "DD/MM/YYYY"
    to match the other regions. Returns an empty frame when the page has no
    such table.
    """
    columns = ["fecha", "localidad", "lugar", "horario", "url"]
    table = soup.select_one("div.center-blood table.views-table")
    if table is None:
        return pd.DataFrame(columns=columns)

    df = pd.read_html(StringIO(str(table)))[0].rename(columns=MOBILE_COLUMNS)
    df["fecha"] = pd.to_datetime(df["fecha"], format="%d-%m-%Y").dt.strftime("%d/%m/%Y")
    df["localidad"] = df["localidad"].apply(crawl.title_name)
    df["horario"] = df["horario"].apply(normalize_hours)
    df["url"] = center_url(province)
    return df[columns]


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape each province's CTTC page for its fixed donation point.

    Each row carries the day-by-day weekly timetable as "schedule" (see
    opening_hours.parse_weekly_hours) and a readable "horario" summary.
    """
    rows = []
    for province in CENTER_IDS:
        point = parse_fixed_point(fetch_center(province))
        point["provincia"] = province
        point["url"] = center_url(province)
        rows.append(point)
    return pd.DataFrame(rows)


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape every province's upcoming mobile collections."""
    frames = [
        parse_mobile_points(fetch_center(province), province) for province in CENTER_IDS
    ]
    return pd.concat(frames, ignore_index=True)
