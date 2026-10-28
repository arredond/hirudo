"""Crawl INGESA Melilla's "Centros de Donación" page for its one fixed donation spot.

The page (ingesa.sanidad.gob.es/melilla) describes a single spot, the Centro
de Transfusión, as plain text: street address, phone and hours. It has no
map link, so the spot is geocoded from its address (see
main.scrape_fixed_points_melilla). The page publishes no donation drives
(its campaigns pages list none) and no blood-levels widget, so there's no
scrape_mobile_points() or scrape_blood_levels() here.
"""

import re

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL_FIXED_POINTS = (
    "https://ingesa.sanidad.gob.es/melilla/Area-Sanitaria/Centros-de-Donaci-n.html"
)
LOCALIDAD = "Melilla"

# The spot's own paragraph starts with this bold label.
SPOT_LABEL_RE = re.compile(r"Centro de Transfusi")

# "C.\ Cuerpo Nacional de Policia, n 4" (the stray backslash is removed below).
ADDRESS_RE = re.compile(r"^C\.\\?\s")
PHONE_PREFIX = "Tlfs:"
HOURS_PREFIX = "Nuestro horario:"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace (the markup has line breaks and &nbsp; inside text)."""
    return " ".join(text.split())


def parse_fixed_point(soup: BeautifulSoup) -> dict:
    """Parse the Centro de Transfusión's paragraph, one <br>-separated line at a time.

    The paragraph reads, in order: the centre's name (<strong>), the health
    centre it's in, "Tlfs: <phones>", an e-mail, the street address, and
    "Nuestro horario: De <hours>" (the hours are bold, so they come back as
    their own string).
    """
    label = soup.find("strong", string=SPOT_LABEL_RE)
    if label is None:
        raise ValueError(f"No Centro de Transfusión entry on {URL_FIXED_POINTS}")
    lines = [normalize_whitespace(line) for line in label.parent.stripped_strings]

    try:
        address_line = next(line for line in lines if ADDRESS_RE.match(line))
        phone_line = next(line for line in lines if line.startswith(PHONE_PREFIX))
        hours_start = next(
            index for index, line in enumerate(lines) if line.startswith(HOURS_PREFIX)
        )
    except StopIteration:
        raise ValueError(f"Centro de Transfusión entry is missing fields: {lines}")

    horario = normalize_whitespace(" ".join(lines[hours_start:]))
    return {
        "name": normalize_whitespace(label.get_text()),
        "localidad": LOCALIDAD,
        "direccion": address_line.replace("\\", "").strip(),
        "telefono": phone_line.removeprefix(PHONE_PREFIX).strip(),
        "horario": horario.removeprefix(HOURS_PREFIX).strip(),
        "url": URL_FIXED_POINTS,
    }


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape Melilla's one fixed donation spot from its page (no coordinates: see module docstring)."""
    response = SESSION.get(URL_FIXED_POINTS)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, features="lxml")
    return pd.DataFrame([parse_fixed_point(soup)])
