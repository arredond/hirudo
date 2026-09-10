"""Integration tests — these hit real external URLs.

Run with: uv run python -m pytest etl/tests/test_integration.py -v
They are excluded from the default test run (see pyproject.toml).
"""

import os

import pytest

from utils import crawl

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixed-point list page
# ---------------------------------------------------------------------------


def test_fixed_points_list_returns_rows():
    html = crawl.fetch_points_html(crawl.URL_FIXED_POINTS)
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    panel = soup.find("div", {"class": "panelResultados"})
    assert panel is not None, "panelResultados div missing — list page layout may have changed"
    rows = [crawl.extract_fixed_point_general(r) for r in panel.find_all("tr")]
    data_rows = [r for r in rows if r is not None]
    assert len(data_rows) > 5, f"Expected >5 fixed points, got {len(data_rows)}"


def test_fixed_points_list_row_has_expected_fields():
    html = crawl.fetch_points_html(crawl.URL_FIXED_POINTS)
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    panel = soup.find("div", {"class": "panelResultados"})
    rows = [crawl.extract_fixed_point_general(r) for r in panel.find_all("tr")]
    first = next(r for r in rows if r is not None)
    assert "name" in first
    assert "center_id" in first
    assert "url" in first
    assert first["url"].startswith("https://")


# ---------------------------------------------------------------------------
# Fixed-point detail page
# ---------------------------------------------------------------------------


KNOWN_CENTER_ID = "2544"
KNOWN_CENTER_URL = f"{crawl.URL_BASE}detalleCentros.aspx?ID={KNOWN_CENTER_ID}"


def test_fixed_point_detail_returns_coordinates():
    result = crawl.extract_fixed_point_details(KNOWN_CENTER_URL)
    assert "latitude" in result
    assert "longitude" in result
    # Sanity-check: coordinates should be somewhere in the Madrid region
    assert 39.5 < result["latitude"] < 41.5, "Latitude outside Madrid bounds"
    assert -4.5 < result["longitude"] < -3.0, "Longitude outside Madrid bounds"


def test_fixed_point_detail_has_address_fields():
    result = crawl.extract_fixed_point_details(KNOWN_CENTER_URL)
    # These label keys come from the page HTML — if they go missing the scraper is broken
    expected_keys = {"Horario de donaciones", "Dirección postal", "Municipio", "gmaps_url"}
    missing = expected_keys - result.keys()
    assert not missing, f"Detail page is missing expected fields: {missing}"


def test_fixed_point_detail_gmaps_link_parseable():
    result = crawl.extract_fixed_point_details(KNOWN_CENTER_URL)
    # extract_gmaps_lat_lon must not raise on the live URL format
    lat, lon = crawl.extract_gmaps_lat_lon(result["gmaps_url"])
    assert isinstance(lat, float)
    assert isinstance(lon, float)


# ---------------------------------------------------------------------------
# Mobile-point list page
# ---------------------------------------------------------------------------


def test_mobile_points_list_returns_dataframe():
    df = crawl.scrape_mobile_points()
    assert len(df) > 0, "Mobile points returned an empty DataFrame"
    assert set(df.columns) >= {"Localidad", "Lugar", "Dirección", "Fecha", "Horario"}, (
        f"Unexpected columns: {list(df.columns)}"
    )


# ---------------------------------------------------------------------------
# Geocoding (only runs when API key is present)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_MAPS_API_KEY"),
    reason="GOOGLE_MAPS_API_KEY not set",
)
def test_geocode_known_madrid_address():
    from utils.geocode import geocode_address

    lng, lat, location_type, score = geocode_address(
        "Puerta del Sol, s/n, Madrid, Community of Madrid, Spain"
    )
    assert lng is not None and lat is not None
    assert 40.3 < lat < 40.5
    assert -3.8 < lng < -3.6
    assert score >= 4
