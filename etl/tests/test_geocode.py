"""Tests for geocode.py — address building and geocoding logic."""

import pandas as pd
from utils.geocode import build_full_address, geocode_address

# ---------------------------------------------------------------------------
# build_full_address
# ---------------------------------------------------------------------------


def _make_row(**kwargs):
    return pd.Series(kwargs)


def test_build_full_address_lugar():
    row = _make_row(lugar="Calle Mayor, 1", localidad="Madrid")
    result = build_full_address(row, "lugar")
    assert result == "Calle Mayor, 1, Madrid, Community of Madrid, Spain"


def test_build_full_address_direccion():
    row = _make_row(direccion="Av. de la Paz, 5", localidad="Alcalá de Henares")
    result = build_full_address(row, "direccion")
    assert result == "Av. de la Paz, 5, Alcalá de Henares, Community of Madrid, Spain"


# ---------------------------------------------------------------------------
# geocode_address (mocked Google Maps client)
# ---------------------------------------------------------------------------


def test_geocode_address_returns_none_on_empty_results(mocker):
    mock_client = mocker.MagicMock()
    mock_client.geocode.return_value = []
    mocker.patch("googlemaps.Client", return_value=mock_client)
    mocker.patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "fake-key"})

    result = geocode_address("Nowhere Street, Madrid, Spain")
    assert result == (None, None, None, None)


def test_geocode_address_returns_coordinates(mocker):
    mock_client = mocker.MagicMock()
    mock_client.geocode.return_value = [
        {
            "geometry": {
                "location": {"lng": -3.7038, "lat": 40.4168},
                "location_type": "ROOFTOP",
            }
        }
    ]
    mocker.patch("googlemaps.Client", return_value=mock_client)
    mocker.patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "fake-key"})

    lng, lat, location_type, score = geocode_address("Calle Mayor, Madrid, Spain")
    assert abs(lng - (-3.7038)) < 1e-4
    assert abs(lat - 40.4168) < 1e-4
    assert location_type == "ROOFTOP"
    assert score == 9


def test_geocode_address_scores_location_types(mocker):
    def make_result(loc_type):
        return [
            {"geometry": {"location": {"lng": 0, "lat": 0}, "location_type": loc_type}}
        ]

    mock_client = mocker.MagicMock()
    mocker.patch("googlemaps.Client", return_value=mock_client)
    mocker.patch.dict("os.environ", {"GOOGLE_MAPS_API_KEY": "fake-key"})

    for loc_type, expected_score in [
        ("ROOFTOP", 9),
        ("RANGE_INTERPOLATED", 7),
        ("GEOMETRIC_CENTER", 6),
        ("APPROXIMATE", 4),
    ]:
        mock_client.geocode.return_value = make_result(loc_type)
        _, _, _, score = geocode_address("any address")
        assert score == expected_score, f"{loc_type} should score {expected_score}"
