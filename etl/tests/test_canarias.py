"""Tests for utils/crawl/canarias.py — scraping and parsing logic."""

import datetime
import urllib.parse

import pandas as pd
import pytest
import responses
from regions import canarias as regions_canarias
from utils.crawl import canarias

from tests.conftest import (
    CANARIAS_FIXED_RESULTS_HTML,
    CANARIAS_HOME_HTML,
    CANARIAS_MOBILE_RESULTS_HTML,
    CANARIAS_PARTIAL_RESPONSE_XML,
)

TODAY = datetime.date(2026, 10, 28)


def mock_search(results_html: str) -> None:
    """Register the three requests an unfiltered search makes."""
    responses.add(responses.GET, canarias.URL_SEARCH, body=CANARIAS_HOME_HTML)
    responses.add(
        responses.POST,
        canarias.URL_SEARCH,
        status=302,
        headers={"Location": canarias.URL_RESULTS},
    )
    responses.add(responses.GET, canarias.URL_RESULTS, body=results_html)


def test_coordinates_from_link_reads_the_map_pair():
    href = "http://maps.google.es/maps?f=q&hl=es&q=28.081056%2C+-15.417814"

    assert canarias.coordinates_from_link(href) == (
        pytest.approx(28.081056),
        pytest.approx(-15.417814),
    )


def test_coordinates_from_link_treats_empty_or_outside_pairs_as_missing():
    assert canarias.coordinates_from_link("http://maps.google.es/maps?q=%2C") == (
        None,
        None,
    )
    assert canarias.coordinates_from_link("http://maps.google.es/maps?q=0%2C+0") == (
        None,
        None,
    )
    assert canarias.coordinates_from_link(None) == (None, None)


def test_parse_fecha_reads_spanish_month_abbreviations():
    assert canarias.parse_fecha("28-oct-2026") == datetime.date(2026, 10, 28)
    assert canarias.parse_fecha("2-dic-2026") == datetime.date(2026, 12, 2)
    assert canarias.parse_fecha("not a date") is None


@responses.activate
def test_scrape_fixed_points_reads_links_and_leaves_missing_coordinates_unset():
    mock_search(CANARIAS_FIXED_RESULTS_HTML)

    df = canarias.scrape_fixed_points()

    assert len(df) == 2
    maternal = df.iloc[0]
    assert maternal["name"] == "Hospital Universitario Materno- Infantil de Canarias"
    assert maternal["localidad"] == "Las Palmas de Gran Canaria"
    assert maternal["direccion"] == (
        "Avda. Maritima del Sur S/N Planta 3 - Edificio del Mar"
    )
    assert maternal["latitude"] == pytest.approx(28.081056)
    assert maternal["longitude"] == pytest.approx(-15.417814)
    assert df.iloc[1]["name"] == "Anexo Centro Salud de Vecindario"
    assert df.iloc[1]["localidad"] == "Santa Lucia de Tirajana"
    assert pd.isna(df.iloc[1]["direccion"])
    assert df.iloc[1]["latitude"] != df.iloc[1]["latitude"]  # NaN


@responses.activate
def test_scrape_mobile_points_drops_past_stops_and_reads_links():
    mock_search(CANARIAS_MOBILE_RESULTS_HTML)

    df = canarias.scrape_mobile_points(today=TODAY)

    assert df["fecha"].tolist() == ["28/10/2026", "29/10/2026", "29/10/2026"]
    assert df["localidad"].tolist() == [
        "Las Palmas de Gran Canaria",
        "Moya",
        "Las Palmas de Gran Canaria",
    ]
    assert df.iloc[1]["horario"] == "09:15-13:30 16:15-20:30"
    assert df.iloc[1]["lugar"] == "Junto Al Ayuntamiento"
    assert df.iloc[1]["direccion"] == "C/Miguel Hernandez ,13"
    assert df.iloc[0]["latitude"] == pytest.approx(28.131688879942423)
    assert df.iloc[2]["latitude"] != df.iloc[2]["latitude"]  # no map link


@responses.activate
def test_fetch_all_rows_pages_with_the_paginator_request_until_total():
    # The summary says 8 stops, but the first page holds only 4, so one
    # paginator request is needed for the rest.
    results_html = CANARIAS_MOBILE_RESULTS_HTML.replace(">4</div>", ">8</div>")
    mock_search(results_html)
    responses.add(
        responses.POST, canarias.URL_RESULTS, body=CANARIAS_PARTIAL_RESPONSE_XML
    )

    rows = canarias.fetch_all_rows(canarias.CAMPAIGN_MOBILE)

    assert len(rows) == 8
    paginator_call = responses.calls[-1].request
    assert paginator_call.url == canarias.URL_RESULTS
    body = urllib.parse.parse_qs(paginator_call.body)
    assert body["results:dataView_first"] == ["4"]
    assert body["javax.faces.ViewState"] == ["RESULTS-VS"]


def test_scrape_mobile_points_canarias_geocodes_only_stops_without_map(mocker):
    scraped = pd.DataFrame(
        {
            "lugar": ["Philip Morris Spain", "Moya Ayuntamiento"],
            "localidad": ["Las Palmas de Gran Canaria", "Moya"],
            "direccion": ["Bravo Murillo 28", None],
            "fecha": ["29/10/2026", "29/10/2026"],
            "horario": ["08:30-14:00", "09:15-13:30 16:15-20:30"],
            "url": [canarias.URL_BASE] * 2,
            "latitude": [None, 28.110843],
            "longitude": [None, -15.583667],
        }
    )
    seen = {}

    def fake_geocode_points(df, geocoding_cache, address_column):
        seen["addresses"] = df[address_column].tolist()
        df["longitude"] = -15.4
        df["latitude"] = 28.1
        return df

    mocker.patch("utils.crawl.canarias.scrape_mobile_points", return_value=scraped)
    mocker.patch("utils.geocode.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("utils.geocode.geocode_points", side_effect=fake_geocode_points)

    df = regions_canarias.scrape_mobile_points()

    # Only the stop without a map link is sent for geocoding
    assert seen["addresses"][0] == (
        "Bravo Murillo 28, Las Palmas de Gran Canaria, Canarias, Spain"
    )
    assert pd.isna(seen["addresses"][1])
    assert df["latitude"].tolist() == [28.1, 28.110843]
    assert df["name"].tolist() == [
        "Equipo móvil en Philip Morris Spain",
        "Equipo móvil en Moya Ayuntamiento",
    ]
    assert set(df["region"]) == {"Canarias"}


def test_scrape_fixed_points_canarias_uses_hand_built_hours(mocker):
    scraped = pd.DataFrame(
        {
            "name": ["Hospiten Bellevue"],
            "localidad": ["Puerto de la Cruz"],
            "direccion": ["C/ Alemania, 6"],
            "horario": ["De lunes a viernes de 11:00 a 13:30 y de 15:00 a 17:30h."],
            "latitude": [28.407359],
            "longitude": [-16.544069],
            "url": [canarias.URL_BASE],
        }
    )
    lookup = {"Hospiten Bellevue": "Mo-Fr 11:00-13:30,15:00-17:30; PH off"}
    mocker.patch("utils.crawl.canarias.scrape_fixed_points", return_value=scraped)
    mocker.patch("utils.geocode.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("utils.points.load_opening_hours_fijos", return_value=lookup)
    mocker.patch(
        "utils.geocode.geocode_points",
        side_effect=lambda df, cache, col: df.assign(
            longitude=-16.544069, latitude=28.407359
        ),
    )

    df = regions_canarias.scrape_fixed_points()

    assert df["opening_hours"].iloc[0] == "Mo-Fr 11:00-13:30,15:00-17:30; PH off"
    assert df["region"].iloc[0] == "Canarias"
    assert (
        df["gmaps_url"].iloc[0] == "https://www.google.com/maps?q=28.407359+-16.544069"
    )
