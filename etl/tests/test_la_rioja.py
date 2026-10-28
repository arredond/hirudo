"""Tests for utils/crawl/la_rioja.py — scraping and parsing logic."""

import datetime

import pandas as pd
import pytest
import responses
from utils.crawl import la_rioja

from tests.conftest import (
    LA_RIOJA_CALENDAR_HTML,
    LA_RIOJA_FIXED_POINT_HTML,
    LA_RIOJA_HOME_HTML,
    LA_RIOJA_STOP_MAP_HTML,
    LA_RIOJA_STOP_NO_MAP_HTML,
)

TODAY = datetime.date(2026, 10, 28)
STOP_URL = "https://www.bancosangrerioja.org/el-banco-de-sangre/calendario-extracciones/colecta?c="


@responses.activate
def test_scrape_fixed_points_reads_marker_and_legend_hours():
    responses.add(
        responses.GET, la_rioja.URL_FIXED_POINTS, body=LA_RIOJA_FIXED_POINT_HTML
    )

    df = la_rioja.scrape_fixed_points()

    assert len(df) == 1
    point = df.iloc[0]
    assert point["name"] == "Banco de Sangre del Hospital San Pedro"
    assert point["localidad"] == "Logroño"
    assert point["latitude"] == pytest.approx(42.451333)
    assert point["longitude"] == pytest.approx(-2.427574)
    assert point["horario"] == (
        "De lunes a viernes de 8 a 20 horas Sábados de 9 a 14 horas"
    )


@responses.activate
def test_scrape_blood_levels_maps_level_digit_to_status():
    responses.add(responses.GET, la_rioja.URL_BASE, body=LA_RIOJA_HOME_HTML)

    df = la_rioja.scrape_blood_levels().set_index("blood_type")

    assert df.index.tolist() == ["0-", "0+", "A-", "A+", "B-", "B+", "AB-", "AB+"]
    assert df.loc["A+", "status"] == "red"
    assert df.loc["A+", "level"] == 1
    assert df.loc["B-", "status"] == "orange"
    assert df.loc["B-", "level"] == 2
    assert df.loc["0+", "status"] == "green"
    assert df.loc["0+", "level"] == 3
    assert df.loc["0+", "label"] == "Dona en tu próxima colecta"


def test_parse_calendar_keeps_stops_from_today_on():
    stops = la_rioja.parse_calendar(
        LA_RIOJA_CALENDAR_HTML, datetime.date(2026, 10, 1), TODAY
    )

    assert [stop["url"] for stop in stops] == [
        STOP_URL + "5013",
        STOP_URL + "5014",
        STOP_URL + "5038",
    ]
    assert stops[0] == {
        "lugar": "Logroño - Cosme García",
        "localidad": "Logroño",
        "direccion": "Ies Cosme García",
        "fecha": "28/10/2026",
        "horario": "09:30-13:45",
        "url": STOP_URL + "5013",
    }
    assert stops[1]["direccion"] == "Avda. La Rioja, parada de autobús"
    assert stops[1]["horario"] == "17:30-21:00"


def test_parse_calendar_drops_stops_on_days_already_past():
    stops = la_rioja.parse_calendar(
        LA_RIOJA_CALENDAR_HTML, datetime.date(2026, 10, 1), datetime.date(2026, 10, 29)
    )

    assert [stop["url"] for stop in stops] == [STOP_URL + "5038"]
    assert stops[0]["fecha"] == "29/10/2026"


@responses.activate
def test_scrape_mobile_points_reads_current_and_next_month_with_map_coords():
    responses.add(
        responses.GET,
        la_rioja.URL_CALENDAR,
        body=LA_RIOJA_CALENDAR_HTML,
        match=[responses.matchers.query_param_matcher({"f": "10-2026"})],
    )
    responses.add(
        responses.GET,
        la_rioja.URL_CALENDAR,
        body="<html></html>",
        match=[responses.matchers.query_param_matcher({"f": "11-2026"})],
    )
    responses.add(responses.GET, STOP_URL + "5013", body=LA_RIOJA_STOP_MAP_HTML)
    responses.add(responses.GET, STOP_URL + "5014", body=LA_RIOJA_STOP_NO_MAP_HTML)
    responses.add(responses.GET, STOP_URL + "5038", body=LA_RIOJA_STOP_NO_MAP_HTML)

    df = la_rioja.scrape_mobile_points(TODAY).set_index("url")

    assert len(df) == 3
    assert df.loc[STOP_URL + "5013", "latitude"] == pytest.approx(42.455)
    assert df.loc[STOP_URL + "5013", "longitude"] == pytest.approx(-2.451745)
    # A stop whose map has no coordinates is left empty for geocoding
    assert pd.isna(df.loc[STOP_URL + "5014", "latitude"])
    assert pd.isna(df.loc[STOP_URL + "5014", "longitude"])


@responses.activate
def test_fetch_stop_coordinates_none_when_map_has_no_coords():
    responses.add(responses.GET, STOP_URL + "5014", body=LA_RIOJA_STOP_NO_MAP_HTML)

    assert la_rioja.fetch_stop_coordinates(STOP_URL + "5014") == (None, None)


@responses.activate
def test_fetch_stop_coordinates_none_when_map_is_pinned_at_zero():
    html = LA_RIOJA_STOP_NO_MAP_HTML.replace("q=%2C", "q=0%2C0")
    responses.add(responses.GET, STOP_URL + "5049", body=html)

    assert la_rioja.fetch_stop_coordinates(STOP_URL + "5049") == (None, None)
