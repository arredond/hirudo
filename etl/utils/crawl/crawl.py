"""Logic shared across region-specific crawl modules."""

import re

import requests

# A maps.app.goo.gl short link's first redirect (before Google's consent
# flow) already carries the place's coordinates: a precise pin as
# "!3d<lat>!4d<lon>" when available, else the viewport center as
# "@<lat>,<lon>". Checking the precise pair first avoids falling back to the
# coarser viewport center when both are present.
GMAPS_PIN_RE = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
GMAPS_VIEWPORT_RE = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")

SESSION = requests.Session()
SESSION.headers["User-Agent"] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def gmaps_url_from_coords(row) -> str:
    """Compose a Google Maps URL from a row's latitude and longitude."""
    return f"https://www.google.com/maps?q={row.latitude}+{row.longitude}"


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
