"""Tests for utils/crawl/navarra.py — scraping and parsing logic."""

import datetime

import pytest
import responses
from utils.crawl import navarra

from tests.conftest import (
    NAVARRA_CALENDAR_EVENTS,
    NAVARRA_CONTACT_PAMPLONA_HTML,
    NAVARRA_CONTACT_TUDELA_HTML,
)

TODAY = datetime.date(2026, 10, 28)


# ---------------------------------------------------------------------------
# parse_contact_page
# ---------------------------------------------------------------------------


def test_parse_contact_page_tudela():
    point = navarra.parse_contact_page(NAVARRA_CONTACT_TUDELA_HTML)

    assert point == {
        "direccion": "C/ Don Miguel Eza, nº 2",
        "localidad": "Tudela",
        "telefono": "848 421 991",
        "horario": (
            "Lunes y miércoles de 8:00h. a 13:30h. "
            "Martes y jueves de 8:00h. a 20:00h. Viernes cerrado"
        ),
        "latitude": pytest.approx(42.0607974),
        "longitude": pytest.approx(-1.6051186),
    }


def test_parse_contact_page_pamplona_two_line_address_and_hours():
    point = navarra.parse_contact_page(NAVARRA_CONTACT_PAMPLONA_HTML)

    assert point["direccion"] == "C/ Irunlarrea, 3 (Hospital de Navarra)"
    assert point["localidad"] == "Pamplona"
    assert point["telefono"] == "848 422 500"
    assert point["horario"] == (
        "De lunes a jueves de 8:00h. a 20:00h. Viernes de 8:00h. a 14:30h."
    )
    assert point["latitude"] == pytest.approx(42.804981957138)
    assert point["longitude"] == pytest.approx(-1.6653321776321)


def test_parse_contact_page_without_map_has_no_coordinates():
    point = navarra.parse_contact_page("<html></html>")

    assert point["latitude"] is None
    assert point["longitude"] is None


# ---------------------------------------------------------------------------
# parse_event / title_town
# ---------------------------------------------------------------------------


def test_parse_event_splits_town_hours_and_venue():
    event = {"title": "LUMBIER 16:45 - 21:00\nCentro Cívico", "start": "2026-10-28"}

    assert navarra.parse_event(event) == {
        "localidad": "Lumbier",
        "lugar": "Centro Cívico",
        "fecha": "28/10/2026",
        "horario": "16:45 a 21:00",
        "url": "https://adona.es/es/calendario-unidad-movil",
    }


def test_parse_event_reads_dotted_times():
    event = {
        "title": "LOS ARCOS 17.00 - 21.00\nCasa de la Villa",
        "start": "2026-10-29",
    }

    point = navarra.parse_event(event)

    assert point is not None
    assert point["localidad"] == "Los Arcos"
    assert point["horario"] == "17:00 a 21:00"


def test_parse_event_skips_placeholder_entry():
    assert navarra.parse_event({"title": ".  - \n", "start": "2026-10-30"}) is None


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("SAN MARTÍN DE UNX", "San Martín de Unx"),
        ("DONEZTEBE/SANTESTEBAN", "Doneztebe/Santesteban"),
        ("ETXARRI ARANATZ", "Etxarri Aranatz"),
        ("LERÍN", "Lerín"),
    ],
)
def test_title_town(raw, expected):
    assert navarra.title_town(raw) == expected


# ---------------------------------------------------------------------------
# scrape_fixed_points / scrape_mobile_points
# ---------------------------------------------------------------------------


@responses.activate
def test_scrape_fixed_points_reads_both_contact_pages():
    responses.add(
        responses.GET,
        navarra.FIXED_POINT_PAGES["Banco de Sangre de Pamplona"],
        body=NAVARRA_CONTACT_PAMPLONA_HTML,
    )
    responses.add(
        responses.GET,
        navarra.FIXED_POINT_PAGES["Banco de Sangre de Tudela"],
        body=NAVARRA_CONTACT_TUDELA_HTML,
    )

    df = navarra.scrape_fixed_points().set_index("name")

    assert list(df.index) == [
        "Banco de Sangre de Pamplona",
        "Banco de Sangre de Tudela",
    ]
    assert df.loc["Banco de Sangre de Tudela", "localidad"] == "Tudela"
    assert df.loc["Banco de Sangre de Pamplona", "localidad"] == "Pamplona"
    assert df.loc["Banco de Sangre de Tudela", "url"] == (
        "https://adona.es/es/contacto-adona/contacto-tudela"
    )


@responses.activate
def test_scrape_mobile_points_keeps_upcoming_stops_only():
    responses.add(
        responses.GET,
        navarra.URL_CALENDAR_EVENTS,
        json=NAVARRA_CALENDAR_EVENTS,
    )

    df = navarra.scrape_mobile_points(TODAY)

    # Yesterday's stop and the placeholder are dropped
    assert list(df["localidad"]) == ["Lumbier", "Los Arcos"]
    assert list(df["fecha"]) == ["28/10/2026", "29/10/2026"]


@responses.activate
def test_scrape_mobile_points_requests_a_unix_window_from_today():
    responses.add(
        responses.GET,
        navarra.URL_CALENDAR_EVENTS,
        json={"events": []},
    )

    df = navarra.scrape_mobile_points(TODAY)

    query = responses.calls[0].request.url
    assert query is not None
    start = int(query.split("start=")[1].split("&")[0])
    end = int(query.split("end=")[1].split("&")[0])
    assert start == 1793142000  # 2026-10-28 00:00 Europe/Madrid
    assert end - start == navarra.MOBILE_EVENTS_DAYS_AHEAD * 86400
    assert df.empty
