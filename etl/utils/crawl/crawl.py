"""Logic shared across region-specific crawl modules."""


def gmaps_url_from_coords(row) -> str:
    """Compose a Google Maps URL from a row's latitude and longitude."""
    return f"https://www.google.com/maps?q={row.latitude}+{row.longitude}"
