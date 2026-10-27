"""Tests for utils/crawl/pais_vasco.py — scraping and parsing logic."""

import datetime

import pytest
import responses
from utils.crawl import pais_vasco

from tests.conftest import PAIS_VASCO_DAY_HTML, PAIS_VASCO_LEVELS_HTML

TODAY = datetime.date(2026, 10, 27)


@pytest.fixture
def one_day_bizkaia(mocker):
    """Fetch only today's Bizkaia listing (and none for other days/provinces)."""
    mocker.patch.object(pais_vasco, "PROVINCES", ["Bizkaia"])
    mocker.patch.object(pais_vasco, "DAYS_AHEAD", 2)
    pais_vasco.fetch_listings.cache_clear()
    responses.add(
        responses.GET,
        pais_vasco.URL_DAY_LISTING,
        body=PAIS_VASCO_DAY_HTML,
        match=[
            responses.matchers.query_param_matcher(
                {"idioma": "ES", "provincia": "Bizkaia", "fechaInicio": "2026/10/27"}
            )
        ],
    )
    responses.add(responses.GET, pais_vasco.URL_DAY_LISTING, body="")
    yield
    pais_vasco.fetch_listings.cache_clear()


def test_parse_day_listing():
    spots = pais_vasco.parse_day_listing(PAIS_VASCO_DAY_HTML, TODAY)

    assert spots[0] == {
        "localidad": "Galdakao",
        "lugar": "GALDAKAO Planta 0-CVTTH",
        "direccion": "Barrio Labeaga 46A",
        "fecha": "27/10/2026",
        "horario": "08:30-14:30",
        "latitude": 43.222799979715,
        "longitude": -2.8175108989617,
    }
    assert len(spots) == 5


@responses.activate
def test_scrape_fixed_points_takes_centres_as_schedule(one_day_bizkaia):
    df = pais_vasco.scrape_fixed_points(TODAY)

    assert len(df) == 1
    point = df.iloc[0]
    assert point["name"] == "Centro Vasco de Transfusión y Tejidos Humanos (Galdakao)"
    assert point["schedule"] == [("27/10/2026", "08:30-14:30")]
    assert point["horario"] == "mar 27/10 08:30-14:30"
    assert point["latitude"] == pytest.approx(43.2228, abs=1e-4)


@responses.activate
def test_scrape_mobile_points_merges_same_day_and_flags_plasma(one_day_bizkaia):
    df = pais_vasco.scrape_mobile_points(TODAY).set_index("lugar")

    # Fixed centre excluded, exact repeat dropped, two shifts merged
    assert set(df.index) == {
        "Bilbao Bombero Etxaniz - Solo Plasma/Cita",
        "Plaza Circular",
    }
    plasma = df.loc["Bilbao Bombero Etxaniz - Solo Plasma/Cita"]
    assert plasma["horario"] == "08:30-13:00, 14:00-18:30"
    assert plasma["plasma_only"]
    assert not df.loc["Plaza Circular", "plasma_only"]


@responses.activate
def test_scrape_blood_levels_maps_bag_images():
    responses.add(
        responses.GET, pais_vasco.URL_BLOOD_LEVELS, body=PAIS_VASCO_LEVELS_HTML
    )

    df = pais_vasco.scrape_blood_levels()

    assert df.to_dict("records") == [
        {
            "blood_type": "O+",
            "status": "yellow",
            "level": 2,
            "label": "Dona en 2 o 3 días",
        },
        {"blood_type": "O-", "status": "red", "level": 1, "label": "Dona urgente"},
        {
            "blood_type": "B+",
            "status": "green",
            "level": 3,
            "label": "Dona en la próxima colecta",
        },
    ]


@pytest.mark.parametrize(
    ("lugar", "expected"),
    [
        ("GALDAKAO Planta 0-CVTTH", True),
        ("Zalla ambulatorio", True),
        ("Anbulategia/Ambulatorio", True),
        ("Lezo Anbulategia", True),
        ("TGEEZ-CVTTH - USANSOLO ospitalea", True),
        ("HOSPITAL ARRASATE-COLECTA PLASMAS", True),
        ("Plaza Circular", False),
        ("Bilbao Bombero Etxaniz - Solo Plasma/Cita", False),
    ],
)
def test_is_fixed_point(lugar, expected):
    assert pais_vasco.is_fixed_point(lugar) == expected


def test_fixed_point_name_adds_town_to_generic_names():
    assert pais_vasco.fixed_point_name("Anbulategia/Ambulatorio", "Zarautz") == (
        "Anbulategia/Ambulatorio (Zarautz)"
    )
    assert pais_vasco.fixed_point_name("AMBULATORIO OLAGUIBEL", "Vitoria-Gasteiz") == (
        "Ambulatorio Olaguibel (Vitoria-Gasteiz)"
    )
