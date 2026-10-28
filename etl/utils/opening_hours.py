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

# Matches one "HH:MM a HH:MM" (or "HH:MM-HH:MM", Castilla-La Mancha's own
# phrasing) range, tolerating the other hour/minute separators sources
# use or mistype instead of ":" ("10.00", "17,00", "14;00", "9'30"), en/em
# dashes between the two times, and rows with several ranges in a day (e.g.
# "10:00 a 14:00 17:00 a 21:00" for a split morning/afternoon shift). Not
# anchored to the string start, so Castilla y León's "De HH:MM a HH:MM"
# phrasing (Madrid's omits the leading "De") matches just as well without
# special-casing.
TIME_RANGE_PATTERN = re.compile(
    r"(\d{1,2})[:.,;'](\d{2})\s*(?:a|-|–|—)\s*(\d{1,2})[:.,;'](\d{2})"
)

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


def parse_scheduled_hours(schedule: list[tuple[str, str]]) -> str | None:
    """Build an OSM opening_hours string from a list of dated days.

    For fixed points whose hours are published as a day-by-day schedule
    rather than a weekly pattern (Comunidad Valenciana's "Horarios sujetos a
    la programación de las donaciones"). Each (fecha, horario) pair becomes
    one dated rule (see parse_mobile_hours), joined in date order with ";",
    so every unlisted day is closed. Days that don't parse are skipped (and
    logged by parse_mobile_hours); returns None if none parse.
    """

    def date_key(day):
        match = DATE_PATTERN.match(day[0].strip())
        if not match:
            return (9999, 99, 99)
        day_num, month, year = match.groups()
        return (int(year), int(month), int(day_num))

    rules = [
        rule
        for rule in (
            parse_mobile_hours(fecha, horario)
            for fecha, horario in sorted(schedule, key=date_key)
        )
        if rule
    ]
    if not rules:
        return None

    candidate = "; ".join(rules)
    try:
        return str(OpeningHours(candidate))
    except ParserError:
        log.warning("Invalid scheduled opening_hours candidate %r", candidate)
        return None


def parse_weekly_hours(schedule: list[tuple[str, str]]) -> str | None:
    """Build an OSM opening_hours string from a fixed weekly timetable.

    For fixed points that publish one repeating week ("Lunes" ... "Sábado")
    rather than dated days. Each (weekday code, horario) pair becomes one
    weekly rule, e.g. ("Tu", "08:30 - 14:30 | 15:30 - 21:30"), so any weekday
    left out is closed. Pairs with no parseable time range are skipped; returns
    None if no day parses.
    """
    rules = []
    for weekday, horario in schedule:
        ranges = TIME_RANGE_PATTERN.findall(horario)
        if not ranges:
            continue
        times = ",".join(
            f"{open_h}:{open_m}-{close_h}:{close_m}"
            for open_h, open_m, close_h, close_m in ranges
        )
        rules.append(f"{weekday} {times}")
    if not rules:
        return None

    candidate = "; ".join(rules)
    try:
        return str(OpeningHours(candidate))
    except ParserError:
        log.warning("Invalid weekly opening_hours candidate %r", candidate)
        return None
