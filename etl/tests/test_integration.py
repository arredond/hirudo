"""Integration tests — these hit real external URLs.

Run with: uv run python -m pytest etl/tests/test_integration.py -v
They are excluded from the default test run (see pyproject.toml).
"""

import os

import pytest
from bs4 import BeautifulSoup
from utils.crawl import madrid as crawl

import main

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixed-point list page
# ---------------------------------------------------------------------------


def test_fixed_points_list_returns_rows():
    html = crawl.fetch_points_html(crawl.URL_FIXED_POINTS)
    soup = BeautifulSoup(html, "lxml")
    panel = soup.find("div", {"class": "panelResultados"})
    assert panel is not None, (
        "panelResultados div missing — list page layout may have changed"
    )
    rows = [crawl.extract_fixed_point_general(r) for r in panel.find_all("tr")]
    data_rows = [r for r in rows if r is not None]
    assert len(data_rows) > 5, f"Expected >5 fixed points, got {len(data_rows)}"


def test_fixed_points_list_row_has_expected_fields():
    html = crawl.fetch_points_html(crawl.URL_FIXED_POINTS)
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
    expected_keys = {
        "Horario de donaciones",
        "Dirección postal",
        "Municipio",
        "gmaps_url",
    }
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


# ---------------------------------------------------------------------------
# Blood-reserve levels (semáforo de necesidades) — donarsangre.org
#
# These hit the live site but never touch the database: the scraper is called
# directly, and the one test that exercises the full ETL step patches to_db.
# ---------------------------------------------------------------------------

ALL_BLOOD_TYPES = {"0-", "0+", "A-", "A+", "B-", "B+", "AB-", "AB+"}


def test_blood_levels_semaforo_layout_present():
    """Guards the assumptions scrape_blood_levels makes about the page."""
    html = crawl.SESSION.get(crawl.URL_BLOOD_LEVELS).text
    soup = BeautifulSoup(html, "lxml")

    semaforo = soup.find("ul", {"class": "semafor-list"})
    assert semaforo is not None, "semafor-list ul missing — page layout changed"

    items = semaforo.find_all("li")
    assert len(items) == 8, f"Expected 8 blood types, got {len(items)}"
    for item in items:
        heading = item.find("h3")
        assert heading is not None and item.find("p") is not None
        known = [c for c in heading["class"] if c in crawl.BLOOD_LEVEL_STATUS]
        assert known, f"No known has-background-* class on {heading['class']}"


def test_blood_levels_scrape_returns_results():
    """At minimum, scraping yields a non-empty DataFrame with the right shape."""
    df = crawl.scrape_blood_levels()
    assert not df.empty
    assert list(df.columns) == ["blood_type", "status", "level", "label"]


def test_blood_levels_returns_all_types():
    df = crawl.scrape_blood_levels()
    assert set(df["blood_type"]) == ALL_BLOOD_TYPES, (
        f"Unexpected blood types: {sorted(df['blood_type'])}"
    )
    assert set(df["status"]) <= {"urgent", "soon", "stable"}
    assert df["level"].between(1, 3).all()
    assert df["label"].str.len().gt(0).all()


def test_process_blood_levels_builds_uploadable_frame_without_writing(mocker):
    """Full ETL step against the live site, but with the DB write stubbed out."""
    mock_to_db = mocker.patch("main.to_db")

    main.process_blood_levels()

    mock_to_db.assert_called_once()
    uploaded, table_name = mock_to_db.call_args.args
    assert table_name == "blood_levels"
    assert mock_to_db.call_args.kwargs["if_exists"] == "append"

    # The frame carries every column the blood_levels table expects.
    assert set(uploaded.columns) == {
        "blood_type",
        "status",
        "level",
        "label",
        "region",
        "source",
        "updated_at",
    }
    assert len(uploaded) == 16  # 8 blood types x 2 regions
    assert set(uploaded["region"]) == {"Comunidad de Madrid", "Castilla y León"}
    assert set(uploaded["source"]) == {"donarsangre.org", "centrodehemoterapiacyl.es"}
    assert uploaded["updated_at"].nunique() == 1


@pytest.mark.skipif(
    not os.environ.get("GOOGLE_MAPS_API_KEY"),
    reason="GOOGLE_MAPS_API_KEY not set",
)
def test_geocode_known_madrid_address():
    from utils.geocode import geocode_address

    lng, lat, _location_type, score = geocode_address(
        "Puerta del Sol, s/n, Madrid, Comunidad de Madrid, Spain"
    )
    assert lng is not None and lat is not None
    assert 40.3 < lat < 40.5
    assert -3.8 < lng < -3.6
    assert score >= 4
