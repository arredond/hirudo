"""Crawl the Hermandad de Donantes de Sangre de Cantabria (hdsc.org) for its fixed donation spot.

The homepage's "dónde donar" slider is the only machine-readable source of
the spot: its address, phone and opening hours sit in plain text, and its
Google Maps short link carries the coordinates (see crawl.resolve_gmaps_coords).

No mobile points are scraped: the weekly "Agenda semanal unidad móvil" is
published only as images (the post's <img> tags have no alt text, and the
media library names carry no schedule), with no text, feed, iCal or
events-API alternative to read instead. No blood-levels widget exists on the
site either, so there's no scrape_blood_levels() here (like Aragón).
"""

import re

import pandas as pd
import requests
from bs4 import BeautifulSoup
from utils.crawl import crawl

URL_BASE = "https://www.hdsc.org/"

# Only the spot's own slide links to Google Maps (the others link to e-mail
# and the activities page), so the Maps link identifies it.
GMAPS_LINK_RE = re.compile(r"maps\.app\.goo\.gl|google\.[a-z.]+/maps")

# "... esperar. Estamos de lunes a viernes de 8:30 a 21:00h ." (the slide
# splits the hours into bold runs, so they come back space-separated).
HOURS_RE = re.compile(r"Estamos de (.+?)\s*\.?$")

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace (the slider's markup has line breaks inside text)."""
    return " ".join(text.split())


def parse_fixed_points(soup: BeautifulSoup) -> list[dict]:
    """Parse the homepage's "dónde donar" slides that name a spot with a Maps link.

    Each such slide has the address as a Maps-linked <a> with one line per
    part ("Avenida de Valdecilla s/n.", "Pabellón 13, Planta 0", "Santander"),
    the centre's name in its <h3>, a tel: link, and a sentence ending
    "Estamos de <hours>.".
    """
    points = []
    for slide in soup.select("sr7-slide"):
        maps_link = slide.find("a", href=GMAPS_LINK_RE)
        heading = slide.find("h3")
        if maps_link is None or heading is None:
            continue
        lines = [normalize_whitespace(line) for line in maps_link.stripped_strings]
        phone = slide.find("a", href=re.compile(r"^tel:"))
        hours = HOURS_RE.search(normalize_whitespace(slide.get_text(" ")))
        points.append(
            {
                "name": normalize_whitespace(heading.get_text()),
                "localidad": lines[-1],
                "direccion": ", ".join(lines[:-1]),
                "telefono": normalize_whitespace(phone.get_text()) if phone else None,
                "horario": hours.group(1) if hours else None,
                "gmaps_url": maps_link["href"],
                "url": URL_BASE,
            }
        )
    return points


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape the fixed donation spot(s) from the homepage, with coordinates
    resolved from each one's Google Maps short link."""
    html = SESSION.get(URL_BASE).text
    soup = BeautifulSoup(html, features="lxml")
    points = parse_fixed_points(soup)
    for point in points:
        point["latitude"], point["longitude"] = crawl.resolve_gmaps_coords(
            point["gmaps_url"]
        )
    return pd.DataFrame(points)
