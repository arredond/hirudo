"""Tests for geocode_points — cache-backed geocoding from one or more
pre-built full-address columns, keeping the best-scoring candidate per row."""

import pandas as pd
import pytest

from main import geocode_points

CACHE_COLS = ["address", "longitude", "latitude", "location_type", "score"]


def _cache(*rows):
    return pd.DataFrame(
        [
            {
                "address": a,
                "longitude": lng,
                "latitude": lat,
                "location_type": "ROOFTOP",
                "score": s,
            }
            for a, lng, lat, s in rows
        ],
        columns=CACHE_COLS,
    )


def _empty_cache():
    return pd.DataFrame(columns=CACHE_COLS)


ADDR = "Plaza Mayor, 1, Ávila, Castilla y León, Spain"


def test_fully_cached_makes_no_api_calls(mocker):
    df = pd.DataFrame({"full_address": [ADDR]})
    cache = _cache((ADDR, -4.69, 40.65, 9))
    mock_geocode = mocker.patch("main.geocode_address")
    mock_to_db = mocker.patch("main.to_db")

    result = geocode_points(df, cache, "full_address")

    mock_geocode.assert_not_called()
    mock_to_db.assert_not_called()
    assert result["longitude"].iloc[0] == pytest.approx(-4.69)
    assert result["latitude"].iloc[0] == pytest.approx(40.65)


def test_missing_address_is_geocoded_and_cached(mocker):
    df = pd.DataFrame({"full_address": [ADDR]})
    mocker.patch("main.geocode_address", return_value=(-4.69, 40.65, "ROOFTOP", 9))
    mock_to_db = mocker.patch("main.to_db")

    result = geocode_points(df, _empty_cache(), "full_address")

    mock_to_db.assert_called_once()
    saved_cache = mock_to_db.call_args.args[0]
    assert set(saved_cache["address"]) == {ADDR}
    assert result["longitude"].iloc[0] == pytest.approx(-4.69)


def test_duplicate_addresses_geocoded_once_and_both_rows_get_coords(mocker):
    df = pd.DataFrame({"full_address": [ADDR, ADDR]})
    mock_geocode = mocker.patch(
        "main.geocode_address", return_value=(-4.69, 40.65, "ROOFTOP", 9)
    )
    mocker.patch("main.to_db")

    result = geocode_points(df, _empty_cache(), "full_address")

    assert mock_geocode.call_count == 1
    assert len(result) == 2
    assert result["longitude"].tolist() == pytest.approx([-4.69, -4.69])


def test_drops_the_helper_address_column():
    df = pd.DataFrame({"full_address": [ADDR]})
    cache = _cache((ADDR, -4.69, 40.65, 9))

    result = geocode_points(df, cache, "full_address")

    assert "address" not in result.columns
    assert "full_address" in result.columns


# ---------------------------------------------------------------------------
# Multiple candidate columns — best-scoring one wins
# ---------------------------------------------------------------------------

POI_ADDR = "El Corte Inglés, Salamanca, Castilla y León, Spain"
STREET_ADDR = (
    "Av. María Auxiliadora 71-85 Salamanca (SALAMANCA), Castilla y León, Spain"
)


def test_poi_candidate_wins_when_better_scored(mocker):
    df = pd.DataFrame(
        {"address_direccion": [STREET_ADDR], "address_campana": [POI_ADDR]}
    )
    cache = _cache(
        (STREET_ADDR, -5.6578, 40.9718, 6),  # GEOMETRIC_CENTER
        (POI_ADDR, -5.6573, 40.9739, 9),  # ROOFTOP
    )
    mocker.patch("main.geocode_address")
    mocker.patch("main.to_db")

    result = geocode_points(df, cache, ["address_direccion", "address_campana"])

    assert result["longitude"].iloc[0] == pytest.approx(-5.6573)
    assert result["latitude"].iloc[0] == pytest.approx(40.9739)


def test_street_candidate_wins_when_better_scored():
    df = pd.DataFrame(
        {"address_direccion": [STREET_ADDR], "address_campana": [POI_ADDR]}
    )
    cache = _cache(
        (STREET_ADDR, -5.6554, 40.9710, 9),  # ROOFTOP
        (POI_ADDR, -5.6572, 40.9736, 6),
    )

    result = geocode_points(df, cache, ["address_direccion", "address_campana"])

    assert result["longitude"].iloc[0] == pytest.approx(-5.6554)


def test_falls_back_to_street_when_no_campana():
    """A continuation row with no 'campana' has a null POI candidate."""
    df = pd.DataFrame({"address_direccion": [STREET_ADDR], "address_campana": [None]})
    cache = _cache((STREET_ADDR, -5.6578, 40.9718, 6))

    result = geocode_points(df, cache, ["address_direccion", "address_campana"])

    assert result["longitude"].iloc[0] == pytest.approx(-5.6578)


def test_falls_back_to_street_on_tied_score():
    df = pd.DataFrame(
        {"address_direccion": [STREET_ADDR], "address_campana": [POI_ADDR]}
    )
    cache = _cache(
        (STREET_ADDR, -5.6578, 40.9718, 7),
        (POI_ADDR, -5.6572, 40.9736, 7),
    )

    result = geocode_points(df, cache, ["address_direccion", "address_campana"])

    assert result["longitude"].iloc[0] == pytest.approx(-5.6578)


def test_geocodes_only_addresses_actually_present(mocker):
    """A null 'campana' candidate must not trigger a geocode call for None."""
    df = pd.DataFrame({"address_direccion": [STREET_ADDR], "address_campana": [None]})
    mock_geocode = mocker.patch(
        "main.geocode_address", return_value=(-5.6578, 40.9718, "GEOMETRIC_CENTER", 6)
    )
    mocker.patch("main.to_db")

    geocode_points(df, _empty_cache(), ["address_direccion", "address_campana"])

    mock_geocode.assert_called_once_with(STREET_ADDR)
