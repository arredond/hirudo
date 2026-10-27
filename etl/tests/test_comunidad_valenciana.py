"""Tests for utils/crawl/comunidad_valenciana.py — scraping and parsing logic."""

import datetime

import pytest
import responses
from bs4 import BeautifulSoup
from utils.crawl import comunidad_valenciana as cv

from tests.conftest import VALENCIA_PROVINCE_PAGE_HTML

TODAY = datetime.date(2026, 10, 27)

# ---------------------------------------------------------------------------
# infer_date
# ---------------------------------------------------------------------------


def test_infer_date_uses_weekday_to_pick_year():
    assert cv.infer_date("Martes, 27 de octubre", TODAY) == datetime.date(2026, 10, 27)
    assert cv.infer_date("Miércoles, 25 de noviembre", TODAY) == (
        datetime.date(2026, 11, 25)
    )


def test_infer_date_rolls_over_into_next_year():
    # Jan 5 2027 is a Tuesday; Jan 5 2026 was a Monday
    assert cv.infer_date("Martes, 5 de enero", datetime.date(2026, 12, 28)) == (
        datetime.date(2027, 1, 5)
    )


def test_infer_date_unparseable_returns_none():
    assert cv.infer_date("Próximamente", TODAY) is None
    assert cv.infer_date("Martes, 27 de brumario", TODAY) is None


# ---------------------------------------------------------------------------
# split_ubicacion / is_plasma_only
# ---------------------------------------------------------------------------


def test_split_ubicacion_strips_town_prefix():
    assert cv.split_ubicacion(
        "CABANES-CASAL JOVE LOCAL, CARRER  DELEGADO VALERA, N. 50", "CABANES"
    ) == ("CASAL JOVE LOCAL", "CARRER DELEGADO VALERA, N. 50", None)


def test_split_ubicacion_keeps_hyphenated_town_whole():
    venue, _, _ = cv.split_ubicacion(
        "VILA-REAL-CONFRARIA PURÍSSIMA SANG SALÓ PARROQUIAL, CARRER S. JOAN PAU II",
        "VILA-REAL",
    )
    assert venue == "CONFRARIA PURÍSSIMA SANG SALÓ PARROQUIAL"


def test_split_ubicacion_strips_differently_spelled_town_prefix():
    # "CASTELLÓN-" prefix vs. "CASTELLÓ DE LA PLANA" Población
    venue, direccion, _ = cv.split_ubicacion(
        "CASTELLÓN-UJI C.JURÍDICAS Y ECONÓMICAS HALL, AVDA. VICENT SOS BAYNAT, S/N",
        "CASTELLÓ DE LA PLANA",
    )
    assert venue == "UJI C.JURÍDICAS Y ECONÓMICAS HALL"
    assert direccion == "AVDA. VICENT SOS BAYNAT, S/N"


@pytest.mark.parametrize(
    ("ubicacion", "venue", "restriction"),
    [
        (
            "CASTELLÓN-PROP (SOLO EMPLEADOS), AVDA. HERMANOS BOU, S/N",
            "PROP",
            "(SOLO EMPLEADOS)",
        ),
        (
            "VALENCIA-FACULTAD DE MEDICINA- SOLO ALUMNOS- HALL, AVDA. BLASCO IBAÑEZ, Nº 15",
            "FACULTAD DE MEDICINA HALL",
            "(SOLO ALUMNOS)",
        ),
        (
            "PATERNA-ORLIMAN SOLO EMPLEADOS SALA REUNIONES, C/ AUSIAS MARCH, 3",
            "ORLIMAN SALA REUNIONES",
            "(SOLO EMPLEADOS)",
        ),
        (
            (
                "ELDA-CIPFP VALLE DE ELDA BIBLIOTECA. (EXCLUSIVA PARA PROFESORADO Y "
                "ALUMNADO), CARRETERA DE SAX 37"
            ),
            "CIPFP VALLE DE ELDA BIBLIOTECA.",
            "(EXCLUSIVA PARA PROFESORADO Y ALUMNADO)",
        ),
    ],
)
def test_split_ubicacion_extracts_restriction(ubicacion, venue, restriction):
    poblacion = ubicacion.split("-")[0]
    got_venue, _, got_restriction = cv.split_ubicacion(ubicacion, poblacion)
    assert got_venue == venue
    assert got_restriction == restriction


def test_split_ubicacion_drops_plasma_only_marker():
    ubicacion = (
        "ELCHE-SOLO DONACIÓN DE PLASMA CON CITA PREVIA-ELCHE HOSPITAL GENERAL , "
        "C/ ALMAZARA Nº 11"
    )
    assert cv.is_plasma_only(ubicacion)
    assert cv.split_ubicacion(ubicacion, "ELCHE") == (
        "ELCHE HOSPITAL GENERAL",
        "C/ ALMAZARA Nº 11",
        None,
    )


# ---------------------------------------------------------------------------
# join_time_ranges / summarize_schedule
# ---------------------------------------------------------------------------


def test_join_time_ranges_sorts_and_fuses_touching_ranges():
    assert cv.join_time_ranges(["16:30-20:30", "09:30-13:30"]) == (
        "09:30-13:30, 16:30-20:30"
    )
    assert cv.join_time_ranges(["14:00-21:00", "08:30-14:00"]) == "08:30-21:00"


def test_summarize_schedule_lists_upcoming_days_only():
    schedule = [
        ("28/10/2026", "08:30-14:30"),
        ("26/10/2026", "08:30-14:30"),  # already past
        ("27/10/2026", "08:30-21:00"),
    ]
    assert cv.summarize_schedule(schedule, TODAY) == (
        "mar 27/10 08:30-21:00 · mié 28/10 08:30-14:30"
    )


def test_summarize_schedule_nothing_upcoming():
    assert cv.summarize_schedule([], TODAY) == "Sin horarios programados próximamente"


# ---------------------------------------------------------------------------
# parse_schedule / scrape_*
# ---------------------------------------------------------------------------


def test_parse_schedule_drops_label_prefixes_and_header_row():
    soup = BeautifulSoup(VALENCIA_PROVINCE_PAGE_HTML, "lxml")
    rows = cv.parse_schedule(soup, TODAY)

    assert len(rows) == 8
    assert rows[2] == {
        "poblacion": "CABANES",
        "ubicacion": "CABANES-CASAL JOVE LOCAL, CARRER DELEGADO VALERA, N. 50",
        "horario": "16:30-20:30",
        "fecha": "27/10/2026",
    }


@responses.activate
def test_scrape_fixed_points_takes_own_rows_as_schedule(mocker):
    mocker.patch.object(cv, "PROVINCES", ["castellon"])
    responses.add(
        responses.GET, cv.province_url("castellon"), body=VALENCIA_PROVINCE_PAGE_HTML
    )

    df = cv.scrape_fixed_points(TODAY)

    assert len(df) == 1
    point = df.iloc[0]
    assert point["name"] == "Centro de Transfusión de Castellón"
    assert point["direccion"] == "AVDA. BENICASIM, S/N"
    assert point["codigo_postal"] == "12004"
    assert bool(point["plasma"])
    # Morning + afternoon rows fused into one back-to-back range
    assert sorted(point["schedule"]) == [
        ("27/10/2026", "08:30-21:00"),
        ("28/10/2026", "08:30-14:30"),
    ]
    assert point["horario"] == "mar 27/10 08:30-21:00 · mié 28/10 08:30-14:30"


@responses.activate
def test_scrape_mobile_points_excludes_fixed_and_merges_same_day(mocker):
    mocker.patch.object(cv, "PROVINCES", ["castellon"])
    responses.add(
        responses.GET, cv.province_url("castellon"), body=VALENCIA_PROVINCE_PAGE_HTML
    )

    df = cv.scrape_mobile_points(TODAY).set_index("venue")

    assert set(df.index) == {
        "CASAL JOVE LOCAL",
        "HOSPITAL LA PLANA HALL PRINCIPAL",
        "PROP",
        "ELCHE HOSPITAL GENERAL",
    }
    assert df.loc["HOSPITAL LA PLANA HALL PRINCIPAL", "horario"] == (
        "09:30-13:30, 16:30-20:30"
    )
    assert df.loc["PROP", "restriction"] == "(SOLO EMPLEADOS)"
    assert df.loc["ELCHE HOSPITAL GENERAL", "plasma_only"]
    assert not df.loc["CASAL JOVE LOCAL", "plasma_only"]
