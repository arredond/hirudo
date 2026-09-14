"""Tests for utils/crawl/castilla_y_leon.py — scraping and parsing logic."""

import pandas as pd
import pytest
import responses
from bs4 import BeautifulSoup
from utils.crawl import castilla_y_leon

from tests.conftest import CYL_HOME_PAGE_HTML, CYL_PROVINCE_PAGE_HTML

# ---------------------------------------------------------------------------
# parse_fixed_points
# ---------------------------------------------------------------------------


def _fixed_points_table(html):
    soup = BeautifulSoup(html, "lxml")
    return soup.find("div", {"class": "entry-content"}).find("table")


def test_parse_fixed_points_multi_row_schedule():
    """Ávila-style table: rowspan cell with no cells of its own, schedule
    rows (2 days) follow, then a colspan closing note that must be skipped."""
    table = _fixed_points_table(CYL_PROVINCE_PAGE_HTML)
    points = castilla_y_leon.parse_fixed_points(table, "avila")

    assert len(points) == 1
    point = points[0]
    assert point["name"] == "HOSPITAL PROVINCIA DE ÁVILA"
    assert "C/ Jesús del Gran Poder, 44" in point["direccion"]
    assert "05004 Ávila" in point["direccion"]
    assert "Ver Ubicación" not in point["direccion"]
    assert point["gmaps_url"] == "https://maps.app.goo.gl/hRDcjSERk7mN4TSaA"
    assert (
        point["horario"] == "Martes y Jueves: 15.00 a 21.30 h; Viernes: 09.30 a 15.00 h"
    )
    assert point["province"] == "avila"


def test_parse_fixed_points_single_row_schedule():
    """Rowspan cell with the day/hours cells alongside it on the same row
    (a single-day schedule), as seen on some province pages."""
    html = """
    <div class="entry-content"><table><tbody>
      <tr><th>PUNTO FIJO</th><th colspan="2">HORARIO</th></tr>
      <tr>
        <td rowspan="1"><strong>CENTRO X</strong><br/>Calle Y, s/n</td>
        <td>Lunes a Sábado</td><td>9:00 a 22:00</td>
      </tr>
      <tr><td colspan="3">Festivos cerrado.</td></tr>
    </tbody></table></div>
    """
    table = _fixed_points_table(html)
    points = castilla_y_leon.parse_fixed_points(table, "valladolid")

    assert len(points) == 1
    assert points[0]["name"] == "CENTRO X"
    assert points[0]["horario"] == "Lunes a Sábado: 9:00 a 22:00"


def test_parse_fixed_points_multiple_points_in_one_table():
    html = """
    <div class="entry-content"><table><tbody>
      <tr><th>PUNTO FIJO</th><th colspan="2">HORARIO</th></tr>
      <tr>
        <td rowspan="1"><strong>CENTRO A</strong><br/>Calle A, 1</td>
        <td>Lunes</td><td>9:00 a 14:00</td>
      </tr>
      <tr>
        <td rowspan="1"><strong>CENTRO B</strong><br/>Calle B, 2</td>
        <td>Martes</td><td>9:00 a 14:00</td>
      </tr>
    </tbody></table></div>
    """
    table = _fixed_points_table(html)
    points = castilla_y_leon.parse_fixed_points(table, "leon")

    assert [p["name"] for p in points] == ["CENTRO A", "CENTRO B"]


# ---------------------------------------------------------------------------
# resolve_gmaps_coords
# ---------------------------------------------------------------------------


@responses.activate
def test_resolve_gmaps_coords_prefers_precise_pin():
    url = "https://maps.app.goo.gl/hRDcjSERk7mN4TSaA"
    responses.add(
        responses.GET,
        url,
        status=302,
        headers={
            "Location": "https://www.google.es/maps/place/X/@40.65,-4.69,17z/"
            "data=!3m2!4b1!8m2!3d40.6503096!4d-4.6924824"
        },
    )

    lat, lon = castilla_y_leon.resolve_gmaps_coords(url)

    assert lat == pytest.approx(40.6503096)
    assert lon == pytest.approx(-4.6924824)


@responses.activate
def test_resolve_gmaps_coords_falls_back_to_viewport():
    url = "https://maps.app.goo.gl/example"
    responses.add(
        responses.GET,
        url,
        status=302,
        headers={"Location": "https://www.google.es/maps/place/X/@40.65,-4.69,17z"},
    )

    lat, lon = castilla_y_leon.resolve_gmaps_coords(url)

    assert lat == pytest.approx(40.65)
    assert lon == pytest.approx(-4.69)


@responses.activate
def test_resolve_gmaps_coords_raises_when_unparseable():
    url = "https://maps.app.goo.gl/example"
    responses.add(
        responses.GET, url, status=302, headers={"Location": "https://google.es/maps"}
    )

    with pytest.raises(ValueError):
        castilla_y_leon.resolve_gmaps_coords(url)


# ---------------------------------------------------------------------------
# clean_mobile_point_row
# ---------------------------------------------------------------------------


def test_clean_mobile_point_row_splits_date_and_strips_link_text():
    row = pd.Series(
        {
            "Fecha - Ubicación": "14/09/2026 Consultorio Médico",
            "direccion": "Plaza Mayor El Hoyo de Pinares (AVILA) Ver Ubicación",
        }
    )
    cleaned = castilla_y_leon.clean_mobile_point_row(row)

    assert cleaned["fecha"] == "14/09/2026"
    assert cleaned["ubicacion"] == "Consultorio Médico"
    assert cleaned["direccion"] == "Plaza Mayor El Hoyo de Pinares (AVILA)"


def test_clean_mobile_point_row_no_date_match():
    row = pd.Series({"Fecha - Ubicación": "Sin fecha", "direccion": "Calle X"})
    cleaned = castilla_y_leon.clean_mobile_point_row(row)

    assert pd.isna(cleaned["fecha"])
    assert cleaned["ubicacion"] == "Sin fecha"


# ---------------------------------------------------------------------------
# scrape_fixed_points / scrape_mobile_points (mocked HTTP, single province)
# ---------------------------------------------------------------------------


@responses.activate
def test_scrape_fixed_points_resolves_coords(mocker):
    mocker.patch.object(castilla_y_leon, "PROVINCES", ["avila"])
    responses.add(
        responses.GET,
        castilla_y_leon.province_url("avila"),
        body=CYL_PROVINCE_PAGE_HTML,
        status=200,
    )
    responses.add(
        responses.GET,
        "https://maps.app.goo.gl/hRDcjSERk7mN4TSaA",
        status=302,
        headers={"Location": "https://www.google.es/maps/place/X/!3d40.65!4d-4.69"},
    )

    df = castilla_y_leon.scrape_fixed_points()

    assert len(df) == 1
    assert df.iloc[0]["name"] == "HOSPITAL PROVINCIA DE ÁVILA"
    assert df.iloc[0]["latitude"] == pytest.approx(40.65)
    assert df.iloc[0]["longitude"] == pytest.approx(-4.69)
    assert df.iloc[0]["url"] == castilla_y_leon.province_url("avila")


@responses.activate
def test_scrape_fixed_points_handles_more_than_one_per_province(mocker):
    """León-style page: 2 fixed-point tables before the mobile-points table.
    Every table but the last must be treated as a fixed point."""
    html = """
    <div class="entry-content">
      <table><tbody>
        <tr><th>PUNTO FIJO A</th><th colspan="2">HORARIO</th></tr>
        <tr><td rowspan="1"><strong>CENTRO A</strong><br/>Calle A, 1
          <a href="https://maps.app.goo.gl/aaa">Ver Ubicación</a></td>
          <td>Lunes</td><td>9:00 a 14:00</td></tr>
      </table>
      <table><tbody>
        <tr><th>PUNTO FIJO B</th><th colspan="2">HORARIO</th></tr>
        <tr><td rowspan="1"><strong>CENTRO B</strong><br/>Calle B, 2
          <a href="https://maps.app.goo.gl/bbb">Ver Ubicación</a></td>
          <td>Martes</td><td>9:00 a 14:00</td></tr>
      </table>
      <table><thead><tr><th>Campañas de donación</th><th>Fecha - Ubicación</th>
        <th>Horario</th><th>Dirección</th></tr></thead>
        <tbody><tr><td>PUEBLO X</td><td>14/09/2026 Plaza</td>
          <td>De 16:00 a 20:00</td><td>Calle Z Ver Ubicación</td></tr></tbody>
      </table>
    </div>
    """
    mocker.patch.object(castilla_y_leon, "PROVINCES", ["leon"])
    responses.add(
        responses.GET, castilla_y_leon.province_url("leon"), body=html, status=200
    )
    responses.add(
        responses.GET,
        "https://maps.app.goo.gl/aaa",
        status=302,
        headers={"Location": "https://google.es/maps/@40.1,-5.1,17z"},
    )
    responses.add(
        responses.GET,
        "https://maps.app.goo.gl/bbb",
        status=302,
        headers={"Location": "https://google.es/maps/@40.2,-5.2,17z"},
    )

    df = castilla_y_leon.scrape_fixed_points()

    assert list(df["name"]) == ["CENTRO A", "CENTRO B"]
    assert df.iloc[1]["latitude"] == pytest.approx(40.2)


@responses.activate
def test_scrape_mobile_points_single_province(mocker):
    mocker.patch.object(castilla_y_leon, "PROVINCES", ["avila"])
    responses.add(
        responses.GET,
        castilla_y_leon.province_url("avila"),
        body=CYL_PROVINCE_PAGE_HTML,
        status=200,
    )

    df = castilla_y_leon.scrape_mobile_points()

    assert len(df) == 1
    assert df.iloc[0]["campana"] == "EL HOYO DE PINARES"
    assert df.iloc[0]["fecha"] == "14/09/2026"
    assert df.iloc[0]["province"] == "avila"
    assert "Ver Ubicación" not in df.iloc[0]["direccion"]


# ---------------------------------------------------------------------------
# scrape_blood_levels
# ---------------------------------------------------------------------------


@responses.activate
def test_scrape_blood_levels_maps_title_attribute():
    responses.add(
        responses.GET, castilla_y_leon.URL_BASE, body=CYL_HOME_PAGE_HTML, status=200
    )

    df = castilla_y_leon.scrape_blood_levels()

    assert list(df.columns) == ["blood_type", "status", "level", "label"]
    by_type = df.set_index("blood_type")
    assert by_type.loc["A+", "status"] == "stable"
    assert by_type.loc["A+", "level"] == 3
    assert by_type.loc["A-", "status"] == "soon"
    assert by_type.loc["B+", "status"] == "urgent"
    assert by_type.loc["B+", "level"] == 1
