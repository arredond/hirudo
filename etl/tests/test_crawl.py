"""Tests for crawl.py — scraping and parsing logic."""

import responses
from bs4 import BeautifulSoup
from utils.crawl import (
    URL_BASE,
    URL_BLOOD_LEVELS,
    extract_fixed_point_details,
    extract_fixed_point_general,
    extract_gmaps_lat_lon,
    gmaps_url_from_coords,
    scrape_blood_levels,
)

from tests.conftest import DETAIL_PAGE_HTML, LIST_PAGE_HTML, SEMAFORO_PAGE_HTML

# ---------------------------------------------------------------------------
# extract_gmaps_lat_lon
# ---------------------------------------------------------------------------


def test_extract_gmaps_lat_lon_standard():
    url = "https://maps.google.com/maps?q=40.32246000,+-3.76751960&iwloc=A&hl=es"
    lat, lon = extract_gmaps_lat_lon(url)
    assert abs(lat - 40.32246) < 1e-4
    assert abs(lon - (-3.76751)) < 1e-4


def test_extract_gmaps_lat_lon_positive_coords():
    url = "https://maps.google.com/maps?q=51.5074,+0.1278"
    lat, lon = extract_gmaps_lat_lon(url)
    assert abs(lat - 51.5074) < 1e-4
    assert abs(lon - 0.1278) < 1e-4


def test_extract_gmaps_lat_lon_no_plus():
    url = "https://maps.google.com/maps?q=40.4168,-3.7038"
    lat, lon = extract_gmaps_lat_lon(url)
    assert abs(lat - 40.4168) < 1e-4
    assert abs(lon - (-3.7038)) < 1e-4


# ---------------------------------------------------------------------------
# extract_fixed_point_general
# ---------------------------------------------------------------------------


def _make_row(html):
    return BeautifulSoup(html, "lxml").find("tr")


def test_extract_fixed_point_general_returns_fields():
    html = """<tr>
      <td data-label="Nombre:"><a href="detalleCentros.aspx?ID=2544">Hospital Severo Ochoa</a></td>
    </tr>"""
    row = _make_row(html)
    result = extract_fixed_point_general(row)
    assert result["name"] == "Hospital Severo Ochoa"
    assert result["center_id"] == "2544"
    assert result["url"] == URL_BASE + "detalleCentros.aspx?ID=2544"


def test_extract_fixed_point_general_skips_header_rows():
    html = "<tr><th>Nombre</th><th>Municipio</th></tr>"
    row = _make_row(html)
    assert extract_fixed_point_general(row) is None


def test_extract_fixed_point_general_skips_empty_rows():
    html = "<tr><td>no label here</td></tr>"
    row = _make_row(html)
    assert extract_fixed_point_general(row) is None


# ---------------------------------------------------------------------------
# extract_fixed_point_details (uses mocked HTTP)
# ---------------------------------------------------------------------------


@responses.activate
def test_extract_fixed_point_details_parses_labels():
    url = "https://donarsangre.sanidadmadrid.org/detalleCentros.aspx?ID=2544"
    responses.add(responses.GET, url, body=DETAIL_PAGE_HTML, status=200)

    result = extract_fixed_point_details(url)

    assert result["Horario de donaciones"] == "Lunes a sábado de 9:00 a 20:30 h"
    assert result["Ubicación de las salas de donación"] == "Planta baja, Zona C"
    assert result["Dirección postal"] == "AVDA ORELLANA, 1"
    assert result["Municipio"] == "Leganés"


@responses.activate
def test_extract_fixed_point_details_extracts_coordinates():
    url = "https://donarsangre.sanidadmadrid.org/detalleCentros.aspx?ID=2544"
    responses.add(responses.GET, url, body=DETAIL_PAGE_HTML, status=200)

    result = extract_fixed_point_details(url)

    assert abs(result["latitude"] - 40.32246) < 1e-4
    assert abs(result["longitude"] - (-3.76751)) < 1e-4
    assert "gmaps_url" in result


# ---------------------------------------------------------------------------
# gmaps_url_from_coords
# ---------------------------------------------------------------------------


def test_gmaps_url_from_coords():
    class FakeRow:
        latitude = 40.32246
        longitude = -3.76751

    url = gmaps_url_from_coords(FakeRow())
    assert "40.32246" in url
    assert "-3.76751" in url
    assert url.startswith("https://www.google.com/maps")


# ---------------------------------------------------------------------------
# scrape_blood_levels (uses mocked HTTP)
# ---------------------------------------------------------------------------


@responses.activate
def test_scrape_blood_levels_maps_background_classes():
    responses.add(responses.GET, URL_BLOOD_LEVELS, body=SEMAFORO_PAGE_HTML, status=200)

    df = scrape_blood_levels()

    assert list(df.columns) == ["blood_type", "status", "level", "label"]
    assert len(df) == 3

    by_type = df.set_index("blood_type")
    assert by_type.loc["0-", "status"] == "urgent"
    assert by_type.loc["0-", "level"] == 1
    assert by_type.loc["0-", "label"] == "Dona hoy"
    assert by_type.loc["A+", "status"] == "soon"
    assert by_type.loc["A+", "level"] == 2
    assert by_type.loc["AB+", "status"] == "stable"
    assert by_type.loc["AB+", "level"] == 3


@responses.activate
def test_scrape_blood_levels_one_row_per_list_item():
    responses.add(responses.GET, URL_BLOOD_LEVELS, body=SEMAFORO_PAGE_HTML, status=200)

    df = scrape_blood_levels()

    # No duplicates, one row per <li> in the semáforo list
    assert df["blood_type"].is_unique
    assert set(df["blood_type"]) == {"0-", "A+", "AB+"}


@responses.activate
def test_scrape_blood_levels_flattens_and_strips_text():
    """Blood type and label come from tags with surrounding whitespace and
    nested markup (<strong>); both must be flattened to clean text."""
    html = """
    <html><body><ul class="semafor-list">
      <li>
        <h3 class="is-flex has-background-warning has-text-black rounded">
            B+
        </h3>
        <p class="is-size-10">Dona en los <strong>próximos días</strong></p>
      </li>
    </ul></body></html>
    """
    responses.add(responses.GET, URL_BLOOD_LEVELS, body=html, status=200)

    df = scrape_blood_levels()

    assert df.loc[0, "blood_type"] == "B+"
    assert df.loc[0, "label"] == "Dona en los próximos días"
    assert df.loc[0, "status"] == "soon"


# ---------------------------------------------------------------------------
# Integration smoke test: list page parsing
# ---------------------------------------------------------------------------


def test_list_page_parsing():
    soup = BeautifulSoup(LIST_PAGE_HTML, "lxml")
    panel = soup.find("div", {"class": "panelResultados"})
    rows = panel.find_all("tr")
    results = [extract_fixed_point_general(r) for r in rows]
    data_rows = [r for r in results if r is not None]

    assert len(data_rows) == 2
    assert data_rows[0]["name"] == "Hospital Severo Ochoa"
    assert data_rows[0]["center_id"] == "2544"
    assert data_rows[1]["name"] == "Hospital Santa Cristina"
    assert data_rows[1]["center_id"] == "2545"
