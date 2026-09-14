"""Tests for process_fixed_points / process_mobile_points — region stamping.

These mock every I/O boundary (scraping, geocoding, DB) and only check that
each uploaded frame carries the region column for both regions.
"""

import geopandas as gpd
import pandas as pd

import main


def test_process_fixed_points_stamps_region(mocker):
    manual_points = pd.DataFrame(
        {"name": ["Manual Center"], "latitude": [40.4], "longitude": [-3.7]}
    )
    other_donations = pd.DataFrame({"name": ["Manual Center"], "plasma": ["yes"]})
    scraped_madrid = pd.DataFrame(
        {"name": ["Hospital X"], "latitude": [40.5], "longitude": [-3.6]}
    )
    scraped_cyl = pd.DataFrame(
        {
            "name": ["Hospital Y"],
            "direccion": ["Calle Y, 1"],
            "gmaps_url": ["https://maps.app.goo.gl/abc"],
            "province": ["avila"],
            "url": ["https://www.centrodehemoterapiacyl.es/puntos-de-donacion/avila/"],
            "horario": ["Lunes a viernes: 9:00 a 14:00"],
            "latitude": [40.6],
            "longitude": [-4.7],
        }
    )

    mocker.patch("main.pd.read_json", side_effect=[manual_points, other_donations])
    mocker.patch("main.madrid.scrape_fixed_points", return_value=scraped_madrid)
    mocker.patch("main.castilla_y_leon.scrape_fixed_points", return_value=scraped_cyl)
    mocker.patch("main.open", mocker.mock_open())
    mocker.patch("main.json.load", return_value={})
    mock_to_db = mocker.patch("main.to_db")

    main.process_fixed_points()

    mock_to_db.assert_called_once()
    uploaded, table_name = mock_to_db.call_args.args
    assert table_name == "puntos_fijos"
    assert isinstance(uploaded, gpd.GeoDataFrame)
    assert set(uploaded["region"]) == {"Comunidad de Madrid", "Castilla y León"}


def test_scrape_mobile_points_madrid_fixes_known_horario_typo(mocker):
    """Recurring source-site typo: "13.a45" instead of "13:45", which
    otherwise fails opening_hours parsing."""
    scraped = pd.DataFrame(
        {
            "Localidad": ["Madrid"],
            "Lugar": ["C/ Londres (Prr Sgda F)"],
            "Dirección": ["C/ Londres"],
            "Fecha": ["14/09/2026"],
            "Horario": ["10:00 a 13.a45"],
        }
    )

    def fake_geocode(df, geocoding_cache):
        df["longitude"] = -3.7
        df["latitude"] = 40.4
        return df

    mocker.patch("main.madrid.scrape_mobile_points", return_value=scraped)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.geocode_mobile_points", side_effect=fake_geocode)

    df = main.scrape_mobile_points_madrid()

    assert df["horario"].iloc[0] == "10:00 a 13:45"
    assert df["opening_hours"].iloc[0] is not None


def test_scrape_mobile_points_cyl_builds_poi_and_street_candidates(mocker):
    scraped = pd.DataFrame(
        {
            "campana": ["EL CORTE INGLÉS", None],
            "fecha": ["14/09/2026", "18/09/2026"],
            "ubicacion": ["Autobús de Donación", "Autobús de Donación"],
            "horario": ["De 08:45 a 14:15", "De 08:45 a 14:15"],
            "direccion": [
                "Av. María Auxiliadora 71-85 Salamanca (SALAMANCA)",
                "Av. María Auxiliadora 71-85 Salamanca (SALAMANCA)",
            ],
            "province": ["salamanca", "salamanca"],
        }
    )

    captured = {}

    def fake_geocode_points(df, geocoding_cache, address_columns):
        captured["address_columns"] = address_columns
        captured["df"] = df.copy()
        df["longitude"] = -5.66
        df["latitude"] = 40.97
        return df

    mocker.patch("main.castilla_y_leon.scrape_mobile_points", return_value=scraped)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.geocode_points", side_effect=fake_geocode_points)

    main.scrape_mobile_points_cyl()

    assert captured["address_columns"] == ["address_direccion", "address_campana"]
    seen = captured["df"]
    assert seen["address_campana"].iloc[0] == (
        "EL CORTE INGLÉS, Salamanca, Castilla y León, Spain"
    )
    # No campana on the second (continuation) row -> no POI candidate
    assert pd.isna(seen["address_campana"].iloc[1])
    assert seen["address_direccion"].iloc[0] == (
        "Av. María Auxiliadora 71-85 Salamanca (SALAMANCA), Castilla y León, Spain"
    )


def test_process_mobile_points_stamps_region_and_keeps_it_in_output(mocker):
    scraped_madrid = pd.DataFrame(
        {
            "Localidad": ["Madrid"],
            "Lugar": ["Plaza Mayor"],
            "Dirección": ["Calle Mayor 1"],
            "Fecha": ["2026-09-15"],
            "Horario": ["10:00-14:00"],
        }
    )
    scraped_cyl = pd.DataFrame(
        {
            "campana": ["EL BARCO DE ÁVILA"],
            "fecha": ["16/09/2026"],
            "ubicacion": ["Centro de Salud"],
            "horario": ["De 16:45 a 20:15"],
            "direccion": ["C/ Eras s/n El Barco de Avila (AVILA)"],
            "province": ["avila"],
        }
    )

    def fake_geocode_mobile(df, geocoding_cache):
        df["longitude"] = -3.7
        df["latitude"] = 40.4
        return df

    def fake_geocode_points(df, geocoding_cache, address_column):
        df["longitude"] = -4.7
        df["latitude"] = 40.6
        return df

    mocker.patch("main.madrid.scrape_mobile_points", return_value=scraped_madrid)
    mocker.patch("main.castilla_y_leon.scrape_mobile_points", return_value=scraped_cyl)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.geocode_mobile_points", side_effect=fake_geocode_mobile)
    mocker.patch("main.geocode_points", side_effect=fake_geocode_points)
    mock_to_db = mocker.patch("main.to_db")

    main.process_mobile_points()

    mock_to_db.assert_called_once()
    uploaded, table_name = mock_to_db.call_args.args
    assert table_name == "puntos_moviles"
    # region survives the explicit output_cols projection
    assert "region" in uploaded.columns
    assert set(uploaded["region"]) == {"Comunidad de Madrid", "Castilla y León"}
