"""Tests for utils/crawl/castilla_la_mancha.py — scraping and parsing logic."""

import responses
from bs4 import BeautifulSoup
from utils.crawl import castilla_la_mancha as clm

from tests.conftest import (
    CLM_FIXED_POINTS_HTML,
    CLM_MOBILE_PAGE1_HTML,
    CLM_MOBILE_PAGE2_HTML,
)

# ---------------------------------------------------------------------------
# parse_fixed_points
# ---------------------------------------------------------------------------


def test_parse_fixed_points_keeps_full_address_unsplit():
    """Addresses mix the center name into the same sentence as the street
    address with no reliable separator (Spanish abbreviation periods like
    "C/." and "Ntra." make splitting unreliable) — so it's kept whole."""
    soup = BeautifulSoup(CLM_FIXED_POINTS_HTML, "lxml")
    points = clm.parse_fixed_points(soup)

    albacete = next(p for p in points if p["localidad"] == "ALBACETE")
    assert (
        albacete["direccion"]
        == "Hospital General Universitario. C/. Hermanos Falcó, 37."
    )
    assert albacete["name"] == "ALBACETE"
    assert albacete["horario"] == "Lunes a viernes de 8:30 a 14:00 h."
    assert albacete["telefono"] == "967 24 30 72"


def test_parse_fixed_points_handles_address_with_no_period():
    soup = BeautifulSoup(CLM_FIXED_POINTS_HTML, "lxml")
    points = clm.parse_fixed_points(soup)

    ciudad_real = next(p for p in points if p["localidad"] == "CIUDAD REAL")
    assert ciudad_real["direccion"] == "Hospital General Universitario de Ciudad Real"


def test_parse_fixed_points_disambiguates_repeated_locality():
    soup = BeautifulSoup(CLM_FIXED_POINTS_HTML, "lxml")
    points = clm.parse_fixed_points(soup)

    toledo_names = [p["name"] for p in points if p["localidad"] == "TOLEDO"]
    assert toledo_names == ["TOLEDO (1)", "TOLEDO (2)"]
    assert len({p["name"] for p in points}) == len(points)  # every name unique


def test_parse_fixed_points_drops_contact_info_from_horario():
    soup = BeautifulSoup(CLM_FIXED_POINTS_HTML, "lxml")
    points = clm.parse_fixed_points(soup)

    toledo2 = next(p for p in points if p["name"] == "TOLEDO (2)")
    assert "WhatsApp" not in toledo2["horario"]
    assert "Email" not in toledo2["horario"]
    assert toledo2["horario"] == "Lunes a viernes, de 9:00 a 14:30 h."


# ---------------------------------------------------------------------------
# scrape_mobile_points_province — pagination
# ---------------------------------------------------------------------------


@responses.activate
def test_scrape_mobile_points_province_follows_pagination():
    url = clm.province_url("toledo")
    responses.add(responses.GET, url, body=CLM_MOBILE_PAGE1_HTML, status=200)
    responses.add(
        responses.GET, f"{url}?page=1", body=CLM_MOBILE_PAGE2_HTML, status=200
    )

    df = clm.scrape_mobile_points_province("toledo")

    assert len(df) == 2
    assert set(df["Localidad"]) == {"PUEBLA DE MONTALBAN,LA", "CONSUEGRA"}
    assert (df["province"] == "toledo").all()


@responses.activate
def test_scrape_mobile_points_province_stops_on_last_page():
    url = clm.province_url("toledo")
    responses.add(responses.GET, url, body=CLM_MOBILE_PAGE2_HTML, status=200)

    df = clm.scrape_mobile_points_province("toledo")

    assert len(df) == 1  # only fetched once, no pager-next to follow


# ---------------------------------------------------------------------------
# parse_clm_date
# ---------------------------------------------------------------------------


def test_parse_clm_date():
    assert clm.parse_clm_date("Lunes, 14 Septiembre, 2026") == "14/09/2026"
    assert clm.parse_clm_date("Miércoles, 30 Septiembre, 2026") == "30/09/2026"


def test_parse_clm_date_unrecognized_returns_none():
    assert clm.parse_clm_date("not a date") is None


# ---------------------------------------------------------------------------
# clean_locality
# ---------------------------------------------------------------------------


def test_clean_locality_unwinds_sorting_article():
    assert clm.clean_locality("PUEBLA DE ALMORADIEL,LA") == "La Puebla De Almoradiel"


def test_clean_locality_leaves_plain_names_alone():
    assert clm.clean_locality("CONSUEGRA") == "Consuegra"
