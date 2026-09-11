"""Tests for process_fixed_points / process_mobile_points — region stamping.

These mock every I/O boundary (scraping, geocoding, DB) and only check that
each uploaded frame carries the region column.
"""

import geopandas as gpd
import pandas as pd

import main


def test_process_fixed_points_stamps_region(mocker):
    manual_points = pd.DataFrame(
        {"name": ["Manual Center"], "latitude": [40.4], "longitude": [-3.7]}
    )
    other_donations = pd.DataFrame({"name": ["Manual Center"], "plasma": ["yes"]})
    scraped = pd.DataFrame(
        {"name": ["Hospital X"], "latitude": [40.5], "longitude": [-3.6]}
    )

    mocker.patch("main.pd.read_json", side_effect=[manual_points, other_donations])
    mocker.patch("main.scrape_fixed_points", return_value=scraped)
    mocker.patch("main.open", mocker.mock_open())
    mocker.patch("main.json.load", return_value={})
    mock_to_db = mocker.patch("main.to_db")

    main.process_fixed_points()

    mock_to_db.assert_called_once()
    uploaded, table_name = mock_to_db.call_args.args
    assert table_name == "puntos_fijos"
    assert isinstance(uploaded, gpd.GeoDataFrame)
    assert set(uploaded["region"]) == {"Comunidad de Madrid"}


def test_process_mobile_points_stamps_region_and_keeps_it_in_output(mocker):
    scraped = pd.DataFrame(
        {
            "Localidad": ["Madrid"],
            "Lugar": ["Plaza Mayor"],
            "Dirección": ["Calle Mayor 1"],
            "Fecha": ["2026-09-15"],
            "Horario": ["10:00-14:00"],
        }
    )

    def fake_geocode(df, geocoding_cache):
        df["longitude"] = -3.7
        df["latitude"] = 40.4
        return df

    mocker.patch("main.scrape_mobile_points", return_value=scraped)
    mocker.patch("main.from_db", return_value=pd.DataFrame())
    mocker.patch("main.geocode_mobile_points", side_effect=fake_geocode)
    mock_to_db = mocker.patch("main.to_db")

    main.process_mobile_points()

    mock_to_db.assert_called_once()
    uploaded, table_name = mock_to_db.call_args.args
    assert table_name == "puntos_moviles"
    # region survives the explicit output_cols projection
    assert "region" in uploaded.columns
    assert set(uploaded["region"]) == {"Comunidad de Madrid"}
