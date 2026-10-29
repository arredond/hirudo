"""Logic shared across region-specific crawl modules."""

import pathlib
import re
import tempfile

import certifi
import requests
from bs4 import Tag

# A maps.app.goo.gl short link's first redirect (before Google's consent
# flow) already carries the place's coordinates: a precise pin as
# "!3d<lat>!4d<lon>" when available, else the viewport center as
# "@<lat>,<lon>". Checking the precise pair first avoids falling back to the
# coarser viewport center when both are present.
GMAPS_PIN_RE = re.compile(r"!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)")
GMAPS_VIEWPORT_RE = re.compile(r"@(-?\d+\.\d+),(-?\d+\.\d+)")

# Wording sources use for a point that only takes donors by appointment:
# "Con cita previa telefónica ..." (Canarias), "... PLASMA CON CITA PREVIA"
# (Comunidad Valenciana), "Solo Plasma/Cita" (País Vasco), "previa cita".
APPOINTMENT_RE = re.compile(
    r"\bcon\s+cita\b|\bcita\s+previa\b|\bprevia\s+cita\b|/\s*cita\b",
    re.IGNORECASE,
)

CERTS_DIR = pathlib.Path(__file__).resolve().parent.parent / "certs"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def required[T](value: T | None, description: str) -> T:
    """Return `value`, raising if a lookup the page layout guarantees is missing.

    For BeautifulSoup `find`/`select_one` results and regex matches: a missing
    element means the source changed its markup, so fail loudly naming what
    was expected instead of with an AttributeError on None further down.
    """
    if value is None:
        raise ValueError(f"Expected {description} not found; did the page change?")
    return value


def attribute(tag: Tag, name: str) -> str:
    """A tag's attribute as a string.

    BeautifulSoup types attribute values as possibly multi-valued (a list, as
    for "class"); single-valued ones like "href" or "src" are plain strings.
    """
    value = tag[name]
    return value if isinstance(value, str) else " ".join(value)


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


def requires_appointment(text) -> bool:
    """Tell whether a point's text says it only takes donors by appointment."""
    return isinstance(text, str) and bool(APPOINTMENT_RE.search(text))


def ca_bundle_with(*cert_names: str) -> str:
    """Return the path of a CA bundle: certifi's roots plus extra certs.

    For sites whose server omits an intermediate certificate from its TLS
    chain. Browsers and macOS curl fetch the missing intermediate themselves
    (via the leaf's AIA URL), but requests doesn't, so verification fails
    there and on Cloud Run. Appending the intermediate (shipped in
    utils/certs/) to certifi's roots keeps verification on.
    """
    bundle = pathlib.Path(certifi.where()).read_text()
    for name in cert_names:
        bundle += "\n" + (CERTS_DIR / name).read_text()
    with tempfile.NamedTemporaryFile(
        "w", suffix=".pem", prefix="ca_bundle_", delete=False
    ) as f:
        f.write(bundle)
    return f.name


# Lowercase particles inside Spanish place names ("Alcalá de Guadaíra",
# "Puebla del Río") that str.title() would otherwise capitalize.
SPANISH_PARTICLE_RE = re.compile(r"(?<=\s)(?:De|Del|La|Las|Los|El|Y)(?=\s)")


def title_name(text: str) -> str:
    """Title-case an all-caps Spanish place name, keeping its particles lowercase."""
    return SPANISH_PARTICLE_RE.sub(lambda match: match.group().lower(), text.title())
