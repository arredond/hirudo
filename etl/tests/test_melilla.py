"""Tests for utils/crawl/melilla.py — scraping and parsing logic."""

import pytest
import requests
import responses
from bs4 import BeautifulSoup
from utils.crawl import melilla

from tests.conftest import MELILLA_DONACION_HTML


def test_parse_fixed_point_reads_name_address_phone_and_hours():
    soup = BeautifulSoup(MELILLA_DONACION_HTML, "lxml")

    spot = melilla.parse_fixed_point(soup)

    assert spot["name"] == "Centro de Transfusión de Melilla"
    assert spot["localidad"] == "Melilla"
    assert spot["direccion"] == "C. Cuerpo Nacional de Policia, n 4"
    assert spot["telefono"] == "951 320 224 y 951 320 225"
    assert spot["horario"] == "De 8:30 h. a 14:30 h."
    assert spot["url"] == melilla.URL_FIXED_POINTS


def test_parse_fixed_point_raises_without_the_spot_block():
    soup = BeautifulSoup("<html><body><p>Sin datos</p></body></html>", "lxml")

    with pytest.raises(ValueError, match="No Centro de Transfusión entry"):
        melilla.parse_fixed_point(soup)


@responses.activate
def test_scrape_fixed_points_returns_the_single_spot():
    responses.add(
        responses.GET,
        melilla.URL_FIXED_POINTS,
        body=MELILLA_DONACION_HTML.encode("utf-8"),
        content_type="text/html; charset=utf-8",
    )

    df = melilla.scrape_fixed_points()

    assert len(df) == 1
    assert df.iloc[0]["name"] == "Centro de Transfusión de Melilla"
    assert df.iloc[0]["direccion"] == "C. Cuerpo Nacional de Policia, n 4"


@responses.activate
def test_scrape_fixed_points_raises_when_the_page_is_gone():
    responses.add(responses.GET, melilla.URL_FIXED_POINTS, status=404)

    with pytest.raises(requests.HTTPError):
        melilla.scrape_fixed_points()
