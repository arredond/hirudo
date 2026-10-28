"""Logic shared across region-specific crawl modules."""

import re


def gmaps_url_from_coords(row) -> str:
    """Compose a Google Maps URL from a row's latitude and longitude."""
    return f"https://www.google.com/maps?q={row.latitude}+{row.longitude}"


# Lowercase particles inside Spanish place names ("Alcalá de Guadaíra",
# "Puebla del Río") that str.title() would otherwise capitalize.
SPANISH_PARTICLE_RE = re.compile(r"(?<=\s)(?:De|Del|La|Las|Los|El|Y)(?=\s)")


def title_name(text: str) -> str:
    """Title-case an all-caps Spanish place name, keeping its particles lowercase."""
    return SPANISH_PARTICLE_RE.sub(lambda match: match.group().lower(), text.title())
