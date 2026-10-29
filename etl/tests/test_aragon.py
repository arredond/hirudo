"""Tests for utils/crawl/aragon.py — scraping and parsing logic."""

import responses
from bs4 import BeautifulSoup
from utils.crawl import aragon

from tests.conftest import ARAGON_HOME_HTML, aragon_event

# ---------------------------------------------------------------------------
# parse_fixed_points
# ---------------------------------------------------------------------------


def test_parse_fixed_points_splits_address_phone_and_hours():
    soup = BeautifulSoup(ARAGON_HOME_HTML, "lxml")
    points = aragon.parse_fixed_points(soup)

    assert [p["name"] for p in points] == [
        "Banco de Sangre y Tejidos de Aragón",
        "Hospital Miguel Servet",
        "Hospital Obispo Polanco",
    ]
    servet = points[1]
    assert servet["localidad"] == "Zaragoza"
    assert servet["direccion"] == "Pº Isabel la Católica, 1-3"
    assert servet["telefono"] == "976 765 500"
    assert servet["horario"].startswith("de lunes a viernes de 9:00 h. a 13:00 h.")


def test_parse_fixed_points_province_from_heading():
    soup = BeautifulSoup(ARAGON_HOME_HTML, "lxml")
    points = aragon.parse_fixed_points(soup)

    assert points[2]["localidad"] == "Teruel"
    assert points[2]["direccion"] == "Ruiz Jarabo, s/n"


def test_parse_fixed_points_only_banco_takes_plasma():
    soup = BeautifulSoup(ARAGON_HOME_HTML, "lxml")
    points = aragon.parse_fixed_points(soup)

    assert [p["plasma"] for p in points] == [True, False, False]


# ---------------------------------------------------------------------------
# split_event_title / parse_event
# ---------------------------------------------------------------------------


def test_split_event_title_drops_venue_article():
    assert aragon.split_event_title("Sariñena, en el Centro de Salud") == (
        "Sariñena",
        "Centro de Salud",
    )
    assert aragon.split_event_title("Interfacultades, en la Sala Inter") == (
        "Interfacultades",
        "Sala Inter",
    )


def test_split_event_title_without_venue():
    assert aragon.split_event_title("Amazon Data Huesca") == (
        "Amazon Data Huesca",
        None,
    )


def test_parse_event_builds_fecha_and_horario():
    event = aragon_event(
        1, "Torrero, en el Centro Cívico", "2026-10-27 17:30:00", "2026-10-27 21:00:00"
    )
    row = aragon.parse_event(event)

    assert row["fecha"] == "27/10/2026"
    assert row["horario"] == "17:30 a 21:00"
    assert row["who"] == "Torrero"
    assert row["venue"] == "Centro Cívico"


def test_parse_event_unescapes_html_entities_in_title():
    event = aragon_event(
        1,
        "Farmacia Natalia Ros, en Miguel Servet&#8211;69",
        "2026-10-28 16:30:00",
        "2026-10-28 20:00:00",
    )
    assert (
        aragon.parse_event(event)["title"]
        == "Farmacia Natalia Ros, en Miguel Servet–69"
    )


# ---------------------------------------------------------------------------
# scrape_mobile_points — pagination
# ---------------------------------------------------------------------------


@responses.activate
def test_scrape_mobile_points_follows_next_rest_url():
    page2_url = f"{aragon.URL_EVENTS_API}?page=2"
    responses.add(
        responses.GET,
        aragon.URL_EVENTS_API,
        json={
            "events": [
                aragon_event(
                    1,
                    "Épila, en el Centro de Salud",
                    "2026-10-29 17:30:00",
                    "2026-10-29 21:00:00",
                )
            ],
            "next_rest_url": page2_url,
        },
    )
    responses.add(
        responses.GET,
        page2_url,
        json={
            "events": [
                aragon_event(
                    2,
                    "Amazon Data Huesca",
                    "2026-11-05 09:30:00",
                    "2026-11-05 13:00:00",
                )
            ]
        },
    )

    df = aragon.scrape_mobile_points()

    assert df["title"].tolist() == [
        "Épila, en el Centro de Salud",
        "Amazon Data Huesca",
    ]
    assert len(responses.calls) == 2
    url = responses.calls[0].request.url
    assert url is not None
    assert "start_date=" in url
