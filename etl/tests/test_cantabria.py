"""Tests for utils/crawl/cantabria.py — scraping and parsing logic."""

import pytest
import responses
from bs4 import BeautifulSoup
from utils.crawl import cantabria

from tests.conftest import CANTABRIA_HOME_HTML

MAPS_SHORT_URL = "https://maps.app.goo.gl/UwoRmWBNeAMJKgKMA"


def test_parse_fixed_points_takes_only_the_spot_slide():
    soup = BeautifulSoup(CANTABRIA_HOME_HTML, "lxml")
    points = cantabria.parse_fixed_points(soup)

    assert len(points) == 1
    assert points[0]["name"] == (
        "Banco de Sangre y Tejidos del Hospital Universitario Marqués de Valdecilla"
    )


def test_parse_fixed_points_splits_address_phone_and_hours():
    soup = BeautifulSoup(CANTABRIA_HOME_HTML, "lxml")
    spot = cantabria.parse_fixed_points(soup)[0]

    assert spot["localidad"] == "Santander"
    assert spot["direccion"] == "Avenida de Valdecilla s/n., Pabellón 13, Planta 0"
    assert spot["telefono"] == "942 202 689"
    assert spot["horario"] == "lunes a viernes de 8:30 a 21:00h"
    assert spot["gmaps_url"] == MAPS_SHORT_URL
    assert spot["url"] == "https://www.hdsc.org/"


def test_parse_fixed_points_empty_without_maps_link():
    soup = BeautifulSoup("<html><body><p>Sin puntos</p></body></html>", "lxml")

    assert cantabria.parse_fixed_points(soup) == []


@responses.activate
def test_scrape_fixed_points_resolves_coordinates_from_short_link():
    responses.add(responses.GET, cantabria.URL_BASE, body=CANTABRIA_HOME_HTML)
    responses.add(
        responses.GET,
        MAPS_SHORT_URL,
        status=302,
        headers={
            "Location": "https://www.google.es/maps/place/Asociaci%C3%B3n/"
            "@43.4564414,-3.8306491,17z/data=!3m1!4b1!4m6!3m5!"
            "1s0xd4949821eda16e1:0x79b50ee1bc72d01f!8m2!3d43.4564414!4d-3.8280688"
        },
    )

    df = cantabria.scrape_fixed_points()

    assert len(df) == 1
    spot = df.iloc[0]
    assert spot["latitude"] == pytest.approx(43.4564414)
    assert spot["longitude"] == pytest.approx(-3.8280688)
    assert spot["telefono"] == "942 202 689"


def test_normalize_whitespace_collapses_runs():
    assert cantabria.normalize_whitespace("  Pabellón \n  13,  Planta 0 ") == (
        "Pabellón 13, Planta 0"
    )
