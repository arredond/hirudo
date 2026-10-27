"""Crawl Centro de Transfusión de la Comunitat Valenciana pages and retrieve fixed and mobile blood donation spots.

Each province's page has two parts: a short "Puntos Fijos de extracción"
list (name + address only, "Horarios sujetos a la programación de las
donaciones"), and a "Programación de las Donaciones" schedule — one table per
date, one row per (place, time range) — that lists the fixed points' actual
hours together with every mobile stop. Rows for a fixed point are split off
here as that point's own schedule; the rest are mobile stops. A place open
both morning and afternoon on the same day shows up as two rows, merged here
into one stop with both ranges.

No blood-levels ("niveles de sangre") widget exists on this site, so, like
Castilla-La Mancha, there's no scrape_blood_levels() here.
"""

import datetime
import re
import urllib.parse

import pandas as pd
import requests
import unidecode
from bs4 import BeautifulSoup

URL_BASE = "https://centro-transfusion.san.gva.es/"
URL_POINTS = urllib.parse.urljoin(URL_BASE, "es/puntos-de-donacion")

PROVINCES = ["castellon", "valencia", "alicante"]

MONTH_NAME_TO_NUM = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}
WEEKDAY_ABBREVIATIONS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
WEEKDAY_NAME_TO_NUM = {
    "lunes": 0,
    "martes": 1,
    "miercoles": 2,
    "jueves": 3,
    "viernes": 4,
    "sabado": 5,
    "domingo": 6,
}
# "Martes, 27 de octubre" — no year (see infer_date).
SCHEDULE_DATE_RE = re.compile(r"^(\w+),\s*(\d{1,2})\s+de\s+(\w+)$")

# "Ubicación" reads "<TOWN>-<VENUE>, <STREET>", e.g. "CABANES-CASAL JOVE
# LOCAL, CARRER DELEGADO VALERA, N. 50". The town prefix doesn't always
# spell the town the same way as the "Población" column (e.g. "CASTELLÓN-"
# vs. "CASTELLÓ DE LA PLANA"), and can itself contain a hyphen ("VILA-REAL").
TOWN_PREFIX_RE = re.compile(r"^[^-]+?\s*-\s*")

# Stops restricted to a group, written several ways: "(SOLO EMPLEADOS)",
# "-SOLO ALUMNOS-", "SOLO EMPLEADOS -", "EXCLUSIVA PARA PROFESORADO Y
# ALUMNADO)", or with no delimiter at all ("SOLO EMPLEADOS SALA REUNIONES").
# So the note is matched as the keyword followed only by known group words,
# stopping at the first other word. These stops are kept (not dropped), but
# the note is moved into the point's name so it's always visible — see
# split_ubicacion.
RESTRICTION_RE = re.compile(
    r"[(-]?\s*\b(s[oó]lo|exclusiva(?:\s+para)?)\s+"
    r"((?:(?:alumn\w*|profes\w*|emplead\w*|personal|padres|familiares|empresa"
    r"|del|instituto|y|e)\b[\s/,.-]*)+)\)?",
    re.IGNORECASE,
)

# Plasma-only mobile stops (hospitals taking plasmapheresis by appointment),
# e.g. "ELCHE-SOLO DONACIÓN DE PLASMA CON CITA PREVIA-ELCHE HOSPITAL GENERAL".
# Like Castilla-La Mancha's "(SÓLO PLASMA)" stops, these don't take whole
# blood, so they get sangre: False (see scrape_mobile_points_valencia).
PLASMA_ONLY_RE = re.compile(
    r"[-\s]*s[oó]lo\s+donaci[oó]n\s+de\s+plasma(?:\s+con\s+cita\s+previa)?[-\s]*",
    re.IGNORECASE,
)

# The source's own fixed-point names are long, all-caps venue descriptions
# ("CENTRO DE TRANSFUSIÓN C.V. SALA DONACIÓN-PARKING SUBTERRÁNEO
# HOSP.GRATUITO"), so the handful there are get a readable name here, matched
# by a distinctive substring of their "Ubicación". Unmatched ones (a new
# fixed point) fall back to the venue text.
FIXED_POINT_NAMES = [
    ("SALUD PÚBLICA SALA", "Centro de Salud Pública de Castellón"),
    ("CASTELLÓN-CENTRO DE TRANSFUSIÓN", "Centro de Transfusión de Castellón"),
    ("HOSPITAL LA FE", "Hospital Universitari i Politècnic La Fe"),
    (
        "VALENCIA-CENTRO DE TRANSFUSIÓN",
        "Centro de Transfusión de la Comunitat Valenciana",
    ),
    (
        "UNIVERSIDAD POLITECNICA",
        "Universitat Politècnica de València (Centro de Salud Laboral)",
    ),
    ("CENTRO DE TRANSFUSIÓN DE ALICANTE", "Centro de Transfusión de Alicante"),
]

# Plasma (plasmapheresis) is donated at the provincial transfusion centers,
# by phone appointment (https://centro-transfusion.san.gva.es/es/plasmaferesi).
PLASMA_MARKER = "CENTRO DE TRANSFUSIÓN"

SESSION = requests.Session()
SESSION.headers["User-Agent"] = "Mozilla/5.0"


def province_url(province: str) -> str:
    """Build the points page URL for a province slug."""
    return f"{URL_POINTS}?provincia={province}"


def normalize_whitespace(text: str) -> str:
    """Collapse runs of whitespace (the source pads with double spaces)."""
    return " ".join(text.split())


def infer_date(date_text: str, today: datetime.date) -> datetime.date | None:
    """Turn "Martes, 27 de octubre" into a date, inferring the missing year.

    The schedule only covers the next few weeks, so the year is whichever of
    last/this/next year makes the weekday name match, preferring the one
    closest to today — which handles the December→January rollover.
    Returns None for text that doesn't parse.
    """
    match = SCHEDULE_DATE_RE.match(unidecode.unidecode(date_text.strip()).lower())
    if not match:
        return None
    weekday_name, day, month_name = match.groups()
    weekday = WEEKDAY_NAME_TO_NUM.get(weekday_name)
    month = MONTH_NAME_TO_NUM.get(month_name)
    if weekday is None or month is None:
        return None

    candidates = []
    for year in (today.year - 1, today.year, today.year + 1):
        try:
            date = datetime.date(year, month, int(day))
        except ValueError:
            continue
        if date.weekday() == weekday:
            candidates.append(date)
    if not candidates:
        return None
    return min(candidates, key=lambda date: abs((date - today).days))


def split_ubicacion(
    ubicacion: str, poblacion: str
) -> tuple[str, str | None, str | None]:
    """Split an "Ubicación" into (venue, street address, restriction note).

    Any plasma-only marker is dropped from the text here; see
    is_plasma_only for detecting it.

    e.g. "BURJASSOT-Á PUNT SALA DE ESPERA DEL ESTUDIO, 2 (SOLO EMPLEADOS),
    POLIGONO ADEMUZ S/N" -> ("Á PUNT SALA DE ESPERA DEL ESTUDIO", "2,
    POLIGONO ADEMUZ S/N", "(SOLO EMPLEADOS)").
    """
    ubicacion = normalize_whitespace(PLASMA_ONLY_RE.sub("-", ubicacion))
    restriction = None
    restriction_match = RESTRICTION_RE.search(ubicacion)
    if restriction_match:
        keyword, groups = restriction_match.groups()
        keyword = normalize_whitespace(keyword).upper()
        restriction = f"({keyword} {groups.strip(' /,.-').upper()})"
        ubicacion = normalize_whitespace(
            ubicacion[: restriction_match.start()]
            + " "
            + ubicacion[restriction_match.end() :]
        )

    # Strip the town prefix, preferring the "Población" spelling when it
    # matches (so a hyphenated town like "VILA-REAL" isn't cut in half).
    poblacion_prefix = re.match(
        re.escape(unidecode.unidecode(poblacion)) + r"\s*-\s*",
        unidecode.unidecode(ubicacion),
        re.IGNORECASE,
    )
    if poblacion_prefix:
        ubicacion = ubicacion[poblacion_prefix.end() :]
    else:
        ubicacion = TOWN_PREFIX_RE.sub("", ubicacion, count=1)

    venue, _, direccion = ubicacion.partition(", ")
    return venue.strip(" ,-"), direccion.strip(" ,-") or None, restriction


def is_plasma_only(ubicacion: str) -> bool:
    """Tell whether a stop only takes plasma (see PLASMA_ONLY_RE)."""
    return bool(PLASMA_ONLY_RE.search(ubicacion))


def fixed_point_name(ubicacion: str, venue: str) -> str:
    """Pick a readable name for a fixed point (see FIXED_POINT_NAMES)."""
    for marker, name in FIXED_POINT_NAMES:
        if marker in ubicacion:
            return name
    return venue


def parse_fixed_points(soup: BeautifulSoup) -> list[dict]:
    """Parse the "Puntos Fijos de extracción" list — name/address + "CP-TOWN"."""
    points = []
    for block in soup.find_all("div", class_="puntosfijos"):
        paragraphs = [p.get_text(" ", strip=True) for p in block.find_all("p")]
        ubicacion = normalize_whitespace(paragraphs[0])
        codigo_postal, _, localidad = paragraphs[1].partition("-")
        points.append(
            {
                "ubicacion": ubicacion,
                "codigo_postal": codigo_postal.strip(),
                "localidad": localidad.strip(),
            }
        )
    return points


def parse_schedule(soup: BeautifulSoup, today: datetime.date) -> list[dict]:
    """Parse every "Programación de las Donaciones" row, one per time range.

    Each date heading (<p class="subtitulo2">) is followed by its own table;
    cells carry their column in their class ("poblacion"/"ubicacion"/
    "horario") plus a mobile-only "<b>Label:</b>" prefix that's dropped.
    """
    rows = []
    for table in soup.find_all("table", class_="datosCentro"):
        heading = table.find_previous_sibling("p", class_="subtitulo2")
        date = infer_date(heading.get_text(strip=True), today) if heading else None
        for tr in table.find_all("tr"):
            cells = {}
            for td in tr.find_all("td"):
                column = next(
                    (
                        c
                        for c in td.get("class", [])
                        if c in {"poblacion", "ubicacion", "horario"}
                    ),
                    None,
                )
                if column:
                    label = td.find("b")
                    if label:
                        label.extract()
                    cells[column] = normalize_whitespace(td.get_text(" ", strip=True))
            if len(cells) == 3:
                cells["fecha"] = date.strftime("%d/%m/%Y") if date else None
                rows.append(cells)
    return rows


def join_time_ranges(ranges: list[str]) -> str:
    """Join one day's "HH:MM-HH:MM" ranges in start order, fusing touching ones.

    e.g. ["16:30-20:30", "09:30-13:30"] -> "09:30-13:30, 16:30-20:30", and
    ["08:30-14:00", "14:00-21:00"] (a morning and an afternoon shift back to
    back) -> "08:30-21:00".
    """
    merged: list[list[str]] = []
    for time_range in sorted(ranges):
        start, end = time_range.split("-")
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return ", ".join(f"{start}-{end}" for start, end in merged)


def merge_same_day_rows(schedule: pd.DataFrame) -> pd.DataFrame:
    """Merge a place's several time ranges on one day into a single row.

    e.g. a 09:30-13:30 row and a 16:30-20:30 row become one row with horario
    "09:30-13:30, 16:30-20:30" — the multi-range form parse_mobile_hours
    already understands (see join_time_ranges).
    """
    return schedule.groupby(
        ["fecha", "poblacion", "ubicacion"], as_index=False, sort=False
    ).agg(horario=("horario", lambda ranges: join_time_ranges(list(ranges))))


def madrid_today() -> datetime.date:
    """Today's date in Spain (the ETL runs on Cloud Run, in UTC)."""
    return pd.Timestamp.now(tz="Europe/Madrid").date()


def parse_fecha(fecha: str) -> datetime.date:
    """Parse a "DD/MM/YYYY" date, as produced by parse_schedule."""
    day, month, year = (int(part) for part in fecha.split("/"))
    return datetime.date(year, month, day)


def summarize_schedule(
    schedule: list[tuple[str, str]], today: datetime.date, days: int = 7
) -> str:
    """Describe a fixed point's next few scheduled days as display text.

    e.g. "mar 27/10 08:30-14:30 · mié 28/10 08:30-14:00, 14:00-21:00". The
    full schedule (a few weeks) lives in opening_hours; this is just what
    fits on a card, refreshed every daily ETL run.
    """
    upcoming = sorted((parse_fecha(fecha), horario) for fecha, horario in schedule)
    upcoming = [(date, horario) for date, horario in upcoming if date >= today][:days]
    if not upcoming:
        return "Sin horarios programados próximamente"
    return " · ".join(
        f"{WEEKDAY_ABBREVIATIONS[date.weekday()]} {date:%d/%m} {horario}"
        for date, horario in upcoming
    )


def fetch_province(
    province: str, today: datetime.date
) -> tuple[list[dict], pd.DataFrame]:
    """Fetch one province page; return its fixed points and merged schedule."""
    html = SESSION.get(province_url(province)).text
    soup = BeautifulSoup(html, features="lxml")
    schedule = pd.DataFrame(
        parse_schedule(soup, today),
        columns=["poblacion", "ubicacion", "horario", "fecha"],
    )
    schedule = merge_same_day_rows(schedule.dropna(subset=["fecha"]))
    schedule["province"] = province
    return parse_fixed_points(soup), schedule


def scrape_fixed_points(today: datetime.date | None = None) -> pd.DataFrame:
    """Scrape every fixed point, each with its own dated schedule.

    "schedule" holds a list of (fecha, horario) pairs taken from the
    province's schedule rows at that point's exact "Ubicación".
    """
    today = today or madrid_today()
    points = []
    for province in PROVINCES:
        fixed_points, schedule = fetch_province(province, today)
        for point in fixed_points:
            venue, direccion, _ = split_ubicacion(
                point["ubicacion"], point["localidad"]
            )
            own_rows = schedule[schedule["ubicacion"] == point["ubicacion"]]
            own_schedule = list(zip(own_rows["fecha"], own_rows["horario"]))
            points.append(
                {
                    "name": fixed_point_name(point["ubicacion"], venue),
                    "direccion": direccion,
                    "localidad": point["localidad"].title(),
                    "codigo_postal": point["codigo_postal"],
                    "plasma": PLASMA_MARKER in point["ubicacion"],
                    "horario": summarize_schedule(own_schedule, today),
                    "schedule": own_schedule,
                    "url": province_url(province),
                }
            )
    return pd.DataFrame(points)


def scrape_mobile_points(today: datetime.date | None = None) -> pd.DataFrame:
    """Scrape every mobile stop: all schedule rows not at a fixed point."""
    today = today or madrid_today()
    frames = []
    for province in PROVINCES:
        fixed_points, schedule = fetch_province(province, today)
        fixed_ubicaciones = {point["ubicacion"] for point in fixed_points}
        mobile = schedule[~schedule["ubicacion"].isin(fixed_ubicaciones)]
        parts = pd.DataFrame(
            [
                split_ubicacion(row.ubicacion, row.poblacion)
                for row in mobile.itertuples()
            ],
            columns=["venue", "direccion", "restriction"],
            index=mobile.index,
        )
        mobile = mobile.join(parts)
        mobile["plasma_only"] = mobile["ubicacion"].apply(is_plasma_only)
        frames.append(mobile)
    return pd.concat(frames, ignore_index=True)
