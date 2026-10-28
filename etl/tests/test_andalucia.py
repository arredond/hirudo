"""Tests for utils/crawl/andalucia.py and regions/andalucia.py."""

import pandas as pd
import pytest
import responses
from bs4 import BeautifulSoup
from regions import andalucia as regions_andalucia
from utils.crawl import andalucia

from tests.conftest import ANDALUCIA_CENTER_HTML


@pytest.fixture
def no_cache():
    """Make sure each test fetches its pages afresh rather than from the cache."""
    andalucia.fetch_center.cache_clear()
    yield
    andalucia.fetch_center.cache_clear()


def center_soup() -> BeautifulSoup:
    return BeautifulSoup(ANDALUCIA_CENTER_HTML, features="lxml")


def test_parse_fixed_point_reads_address_and_weekly_timetable():
    point = andalucia.parse_fixed_point(center_soup())

    assert point["name"] == "Centro de transfusión, tejidos y células de Sevilla"
    assert point["localidad"] == "Sevilla"
    assert point["direccion"] == "Avda. Manuel Siurot, 39, 41013"
    assert point["schedule"] == [
        ("Mo", "08:30 - 14:30 | 15:30 - 21:30"),
        ("Sa", "09:00 - 15:00"),
    ]
    assert point["horario"] == (
        "Lunes 08:30 - 14:30 | 15:30 - 21:30; Sábado 09:00 - 15:00"
    )


def test_parse_mobile_points_rebuilds_dates_and_normalizes_hours():
    df = andalucia.parse_mobile_points(center_soup(), "Sevilla")

    assert df["fecha"].tolist() == [
        "28/10/2026",
        "29/10/2026",
        "29/10/2026",
        "30/10/2026",
    ]
    assert df["localidad"].tolist() == [
        "Dos Hermanas",
        "Alcalá de Guadaira",
        "Coria del Río",
        "Villamanrique de la Condesa",
    ]
    assert df["horario"].tolist() == [
        "17:00 - 21:00",
        "17:00 - 21:00",
        "09:30 - 13:30 | 16:30 - 20:30",
        "17:00 - 20:00",
    ]
    assert set(df["url"]) == {andalucia.center_url("Sevilla")}


def test_parse_mobile_points_without_table_is_empty():
    page = BeautifulSoup("<html><body><p>Sin colectas</p></body></html>", "lxml")

    assert andalucia.parse_mobile_points(page, "Sevilla").empty


@pytest.mark.parametrize(
    ("horario", "expected"),
    [
        ("09:00 - 14:30", "09:00 - 14:30"),
        ("DE 17,30 a 21,00", "17:30 - 21:00"),
        ("17 a 21 HORAS", "17:00 - 21:00"),
        ("16 a 20:30 HORAS", "16:00 - 20:30"),
        ("10 a 14 Y 17 a 21 HORAS", "10:00 - 14:00 | 17:00 - 21:00"),
        ("10:00-14:00 /17:00-21:00", "10:00 - 14:00 | 17:00 - 21:00"),
        ("DESDE LAS 17,00 HORAS", "17:00 - 20:00"),
        ("DESDE LAS 9,30 HORAS", "09:30 - 20:00"),
        ("DESDE LAS 20,30 HORAS", "DESDE LAS 20,30 HORAS"),
    ],
)
def test_normalize_hours(horario, expected):
    assert andalucia.normalize_hours(horario) == expected


@responses.activate
def test_scrape_fixed_points_reads_every_province(no_cache):
    for province in andalucia.CENTER_IDS:
        responses.add(
            responses.GET, andalucia.center_url(province), body=ANDALUCIA_CENTER_HTML
        )

    df = andalucia.scrape_fixed_points()

    assert df["provincia"].tolist() == list(andalucia.CENTER_IDS)
    assert set(df["url"]) == {andalucia.center_url(p) for p in andalucia.CENTER_IDS}


@responses.activate
def test_scrape_mobile_points_stacks_every_province(no_cache):
    for province in andalucia.CENTER_IDS:
        responses.add(
            responses.GET, andalucia.center_url(province), body=ANDALUCIA_CENTER_HTML
        )

    df = andalucia.scrape_mobile_points()

    assert len(df) == 4 * len(andalucia.CENTER_IDS)


def test_scrape_fixed_points_andalucia_builds_weekly_opening_hours(mocker):
    scraped = pd.DataFrame(
        {
            "name": ["Centro de transfusión, tejidos y células de Sevilla"],
            "localidad": ["Sevilla"],
            "direccion": ["Avda. Manuel Siurot, 39, 41013"],
            "horario": ["Lunes 08:30 - 14:30 | 15:30 - 21:30; Sábado 09:00 - 15:00"],
            "schedule": [
                [("Mo", "08:30 - 14:30 | 15:30 - 21:30"), ("Sa", "09:00 - 15:00")]
            ],
            "provincia": ["Sevilla"],
            "url": [andalucia.center_url("Sevilla")],
        }
    )
    addresses = []

    def fake_geocode_points(df, geocoding_cache, address_column):
        addresses.extend(df[address_column])
        df["longitude"] = -5.98
        df["latitude"] = 37.39
        return df

    mocker.patch("utils.crawl.andalucia.scrape_fixed_points", return_value=scraped)
    mocker.patch("utils.geocode.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("utils.geocode.geocode_points", side_effect=fake_geocode_points)

    df = regions_andalucia.scrape_fixed_points()

    assert addresses == ["Avda. Manuel Siurot, 39, 41013, Sevilla, Andalucía, Spain"]
    assert df.iloc[0]["opening_hours"] == "Mo 08:30-14:30,15:30-21:30; Sa 09:00-15:00"
    assert df.iloc[0]["region"] == "Andalucía"
    assert df.iloc[0]["gmaps_url"].startswith("https://www.google.com/maps")
    assert "schedule" not in df.columns


def test_scrape_mobile_points_andalucia_names_and_parses_hours(mocker):
    scraped = pd.DataFrame(
        {
            "fecha": ["28/10/2026"],
            "localidad": ["Dos Hermanas"],
            "lugar": ["HERMANDAD DEL ROCÍO"],
            "horario": ["17:00 - 21:00"],
            "plasma_only": [False],
            "url": [andalucia.center_url("Sevilla")],
        }
    )

    def fake_geocode_points(df, geocoding_cache, address_column):
        df["longitude"] = -6.17
        df["latitude"] = 37.28
        return df

    mocker.patch("utils.crawl.andalucia.scrape_mobile_points", return_value=scraped)
    mocker.patch("utils.geocode.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("utils.geocode.geocode_points", side_effect=fake_geocode_points)

    df = regions_andalucia.scrape_mobile_points()

    row = df.iloc[0]
    assert row["name"] == "Equipo móvil en HERMANDAD DEL ROCÍO, Dos Hermanas"
    assert row["direccion"] == "HERMANDAD DEL ROCÍO"
    assert row["opening_hours"] == "2026 Oct 28 17:00-21:00"
    assert row["region"] == "Andalucía"
    assert row["latitude"] == pytest.approx(37.28)


def test_parse_mobile_points_flags_plasma_sessions_at_the_center():
    html = ANDALUCIA_CENTER_HTML.replace(
        "<tbody>\n        <tr>",
        """<tbody>
        <tr>
          <td>28-10-2026</td><td>X</td><td>PLASMA CENTRO DE TRANSFUSION</td>
          <td>SALA DE EXTRACCIONES</td><td>16:30 - 21:30</td>
        </tr>
        <tr>
          <td>10-11-2026</td><td>M</td><td>SEVILLA</td>
          <td>CTTC DONACIÓN PLASMA</td><td>16:00 - 21:00</td>
        </tr>
        <tr>""",
        1,
    )

    df = andalucia.parse_mobile_points(BeautifulSoup(html, "lxml"), "Sevilla")

    assert df.loc[0, "localidad"] == "Sevilla"
    assert df.loc[:1, "plasma_only"].tolist() == [True, True]
    assert not df.loc[2:, "plasma_only"].any()
