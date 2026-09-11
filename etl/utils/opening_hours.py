"""Build and validate OSM opening_hours strings (https://openingh.openstreetmap.de).

Fixed points have irregular, rarely-changing schedules that are translated by
hand into a lookup table (see opening_hours_fijos.json, built in an active
session). Mobile points are scraped fresh every run and only ever describe a
single day, so they are parsed here from their raw 'Fecha'/'Horario' strings.
"""

import logging
import re

from opening_hours import OpeningHours, ParserError

log = logging.getLogger(__name__)

MONTH_ABBREVIATIONS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

# Matches one "HH:MM a HH:MM" range, tolerating the "." separator some rows use
# instead of ":" (e.g. "10.00 a 14.00") and rows with several ranges in a day
# (e.g. "10:00 a 14:00 17:00 a 21:00" for a split morning/afternoon shift).
TIME_RANGE_PATTERN = re.compile(r"(\d{1,2})[:.](\d{2})\s*a\s*(\d{1,2})[:.](\d{2})")

DATE_PATTERN = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def parse_mobile_hours(fecha: str, horario: str) -> str | None:
    """Build a dated OSM opening_hours string for a mobile point's single day.

    'fecha' is expected as "DD/MM/YYYY" and 'horario' as one or more
    "HH:MM a HH:MM" ranges. Returns None and logs a warning if either field
    doesn't match the expected shape, instead of raising.
    """
    date_match = DATE_PATTERN.match(fecha.strip())
    if not date_match:
        log.warning("Could not parse mobile point date: %r", fecha)
        return None

    day, month, year = date_match.groups()
    time_ranges = TIME_RANGE_PATTERN.findall(horario)
    if not time_ranges:
        log.warning("Could not parse mobile point hours: %r", horario)
        return None

    ranges = ",".join(
        f"{open_h}:{open_m}-{close_h}:{close_m}"
        for open_h, open_m, close_h, close_m in time_ranges
    )
    candidate = f"{year} {MONTH_ABBREVIATIONS[int(month) - 1]} {int(day)} {ranges}"

    try:
        return str(OpeningHours(candidate))
    except ParserError:
        log.warning("Invalid opening_hours candidate %r (from %r)", candidate, horario)
        return None
