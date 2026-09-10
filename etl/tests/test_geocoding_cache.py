"""Tests for geocode_mobile_points — cache hit/miss logic and coord selection."""

import pandas as pd
import pytest

from main import geocode_mobile_points

CACHE_COLS = ["address", "longitude", "latitude", "location_type", "score"]


def _mobile_df(**kwargs):
    """Build a minimal mobile-points DataFrame with one row."""
    defaults = {
        "lugar": ["Plaza Mayor, 1"],
        "localidad": ["Madrid"],
        "direccion": ["Calle Mayor, 5"],
    }
    defaults.update(kwargs)
    return pd.DataFrame(defaults)


def _cache(*rows):
    """Build a geocoding cache DataFrame from (address, lng, lat, score) tuples."""
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


LUGAR_ADDR = "Plaza Mayor, 1, Madrid, Community of Madrid, Spain"
DIR_ADDR = "Calle Mayor, 5, Madrid, Community of Madrid, Spain"


# ---------------------------------------------------------------------------
# Cache hits — no API calls made
# ---------------------------------------------------------------------------


def test_fully_cached_makes_no_api_calls(mocker):
    cache = _cache(
        (LUGAR_ADDR, -3.70, 40.41, 9),
        (DIR_ADDR, -3.71, 40.42, 9),
    )
    mock_geocode = mocker.patch("main.geocode_address")
    mock_to_db = mocker.patch("main.to_db")

    geocode_mobile_points(_mobile_df(), cache)

    mock_geocode.assert_not_called()
    mock_to_db.assert_not_called()


def test_partially_cached_geocodes_only_missing(mocker):
    # lugar is cached, direccion is not
    cache = _cache((LUGAR_ADDR, -3.70, 40.41, 9))
    mock_geocode = mocker.patch(
        "main.geocode_address", return_value=(-3.71, 40.42, "ROOFTOP", 9)
    )
    mocker.patch("main.to_db")

    geocode_mobile_points(_mobile_df(), cache)

    assert mock_geocode.call_count == 1
    mock_geocode.assert_called_once_with(DIR_ADDR)


def test_nothing_cached_geocodes_all_unique_addresses(mocker):
    mock_geocode = mocker.patch(
        "main.geocode_address", return_value=(-3.70, 40.41, "ROOFTOP", 9)
    )
    mocker.patch("main.to_db")

    geocode_mobile_points(_mobile_df(), _empty_cache())

    # Two unique addresses: lugar and direccion
    assert mock_geocode.call_count == 2
    called_addresses = {c.args[0] for c in mock_geocode.call_args_list}
    assert called_addresses == {LUGAR_ADDR, DIR_ADDR}


def test_same_address_in_lugar_and_direccion_geocoded_once(mocker):
    """When lugar and direccion resolve to the same address string, geocode only once."""
    df = _mobile_df(lugar=["Plaza Mayor, 1"], direccion=["Plaza Mayor, 1"])
    mock_geocode = mocker.patch(
        "main.geocode_address", return_value=(-3.70, 40.41, "ROOFTOP", 9)
    )
    mocker.patch("main.to_db")

    geocode_mobile_points(df, _empty_cache())

    assert mock_geocode.call_count == 1


# ---------------------------------------------------------------------------
# Cache is saved when new addresses are geocoded
# ---------------------------------------------------------------------------


def test_new_geocoding_results_saved_to_db(mocker):
    mocker.patch("main.geocode_address", return_value=(-3.70, 40.41, "ROOFTOP", 9))
    mock_to_db = mocker.patch("main.to_db")

    geocode_mobile_points(_mobile_df(), _empty_cache())

    mock_to_db.assert_called_once()
    saved_cache = mock_to_db.call_args.args[0]
    assert set(saved_cache["address"]) == {LUGAR_ADDR, DIR_ADDR}


def test_cache_not_saved_when_nothing_new(mocker):
    cache = _cache(
        (LUGAR_ADDR, -3.70, 40.41, 9),
        (DIR_ADDR, -3.71, 40.42, 9),
    )
    mocker.patch("main.geocode_address")
    mock_to_db = mocker.patch("main.to_db")

    geocode_mobile_points(_mobile_df(), cache)

    mock_to_db.assert_not_called()


# ---------------------------------------------------------------------------
# Coordinate selection — higher score wins
# ---------------------------------------------------------------------------


def test_direccion_used_when_higher_score(mocker):
    cache = _cache(
        (LUGAR_ADDR, -3.70, 40.41, 4),  # APPROXIMATE
        (DIR_ADDR, -3.80, 40.50, 9),  # ROOFTOP
    )
    mocker.patch("main.geocode_address")
    mocker.patch("main.to_db")

    result = geocode_mobile_points(_mobile_df(), cache)

    assert result["longitude"].iloc[0] == pytest.approx(-3.80)
    assert result["latitude"].iloc[0] == pytest.approx(40.50)


def test_lugar_used_when_higher_score(mocker):
    cache = _cache(
        (LUGAR_ADDR, -3.70, 40.41, 9),  # ROOFTOP
        (DIR_ADDR, -3.80, 40.50, 4),  # APPROXIMATE
    )
    mocker.patch("main.geocode_address")
    mocker.patch("main.to_db")

    result = geocode_mobile_points(_mobile_df(), cache)

    assert result["longitude"].iloc[0] == pytest.approx(-3.70)
    assert result["latitude"].iloc[0] == pytest.approx(40.41)


def test_lugar_used_when_scores_equal(mocker):
    cache = _cache(
        (LUGAR_ADDR, -3.70, 40.41, 7),
        (DIR_ADDR, -3.80, 40.50, 7),
    )
    mocker.patch("main.geocode_address")
    mocker.patch("main.to_db")

    result = geocode_mobile_points(_mobile_df(), cache)

    assert result["longitude"].iloc[0] == pytest.approx(-3.70)


def test_lugar_used_when_direccion_score_is_none(mocker):
    cache = _cache(
        (LUGAR_ADDR, -3.70, 40.41, 7),
        (DIR_ADDR, None, None, None),
    )
    mocker.patch("main.geocode_address")
    mocker.patch("main.to_db")

    result = geocode_mobile_points(_mobile_df(), cache)

    assert result["longitude"].iloc[0] == pytest.approx(-3.70)


# ---------------------------------------------------------------------------
# Multiple rows
# ---------------------------------------------------------------------------


def test_multiple_rows_each_get_coords(mocker):
    df = pd.DataFrame(
        {
            "lugar": ["Plaza Mayor, 1", "Gran Vía, 10"],
            "localidad": ["Madrid", "Madrid"],
            "direccion": ["Calle Mayor, 5", "Calle Alcalá, 2"],
        }
    )
    addr_lugar_1 = "Plaza Mayor, 1, Madrid, Community of Madrid, Spain"
    addr_dir_1 = "Calle Mayor, 5, Madrid, Community of Madrid, Spain"
    addr_lugar_2 = "Gran Vía, 10, Madrid, Community of Madrid, Spain"
    addr_dir_2 = "Calle Alcalá, 2, Madrid, Community of Madrid, Spain"

    cache = _cache(
        (addr_lugar_1, -3.70, 40.41, 9),
        (addr_dir_1, -3.71, 40.42, 4),
        (addr_lugar_2, -3.72, 40.43, 6),
        (addr_dir_2, -3.73, 40.44, 9),
    )
    mocker.patch("main.geocode_address")
    mocker.patch("main.to_db")

    result = geocode_mobile_points(df, cache)

    # Row 0: lugar wins (score 9 > 4)
    assert result["longitude"].iloc[0] == pytest.approx(-3.70)
    # Row 1: direccion wins (score 9 > 6)
    assert result["longitude"].iloc[1] == pytest.approx(-3.73)
