"""Tests for db.py — column formatting, GeoDataFrame construction, and uploads."""

import geopandas as gpd
import pandas as pd
import pytest
from utils.db import format_column, gdf_from_df, to_db

# ---------------------------------------------------------------------------
# format_column
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Horario de donaciones", "horario_de_donaciones"),
        ("Ubicación de las salas de donación", "ubicacion_de_las_salas_de_donacion"),
        ("Dirección postal", "direccion_postal"),
        ("Código postal", "codigo_postal"),
        ("Información general", "informacion_general"),
        ("name", "name"),
        ("center_id", "center_id"),
        ("Precio (%)", "precio_pct"),
        ("some/path", "some_path"),
        # Multiple spaces or underscores collapse to one
        ("foo  bar", "foo_bar"),
    ],
)
def test_format_column(raw, expected):
    assert format_column(raw) == expected


# ---------------------------------------------------------------------------
# gdf_from_df
# ---------------------------------------------------------------------------


def test_gdf_from_df_creates_geometry():
    df = pd.DataFrame(
        {
            "name": ["A", "B"],
            "latitude": [40.4168, 40.32246],
            "longitude": [-3.7038, -3.76751],
        }
    )
    gdf = gdf_from_df(df)

    assert "geometry" in gdf.columns
    assert "latitude" not in gdf.columns
    assert "longitude" not in gdf.columns
    assert gdf.crs.to_epsg() == 4326
    assert len(gdf) == 2


def test_gdf_from_df_point_order():
    df = pd.DataFrame({"latitude": [1.0], "longitude": [2.0]})
    gdf = gdf_from_df(df)
    point = gdf.geometry.iloc[0]
    # GeoDataFrame uses (longitude, latitude) = (x, y)
    assert point.x == pytest.approx(2.0)
    assert point.y == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# to_db — if_exists passthrough
# ---------------------------------------------------------------------------


def test_to_db_defaults_to_replace_for_dataframe(mocker):
    mocker.patch("utils.db.get_pg_engine", return_value="ENGINE")
    mock_to_sql = mocker.patch.object(pd.DataFrame, "to_sql")

    to_db(pd.DataFrame({"a": [1]}), "some_table")

    mock_to_sql.assert_called_once_with(
        "some_table", "ENGINE", if_exists="replace", index=False
    )


def test_to_db_forwards_append_for_dataframe(mocker):
    mocker.patch("utils.db.get_pg_engine", return_value="ENGINE")
    mock_to_sql = mocker.patch.object(pd.DataFrame, "to_sql")

    to_db(pd.DataFrame({"a": [1]}), "blood_levels", if_exists="append")

    assert mock_to_sql.call_args.kwargs["if_exists"] == "append"


def test_to_db_forwards_if_exists_for_geodataframe(mocker):
    mocker.patch("utils.db.get_pg_engine", return_value="ENGINE")
    mock_to_postgis = mocker.patch.object(gpd.GeoDataFrame, "to_postgis")

    gdf = gpd.GeoDataFrame(
        {"a": [1]}, geometry=gpd.points_from_xy([0.0], [0.0]), crs="EPSG:4326"
    )
    to_db(gdf, "puntos_moviles", if_exists="append")

    assert mock_to_postgis.call_args.kwargs["if_exists"] == "append"


def test_to_db_rejects_non_dataframe(mocker):
    mocker.patch("utils.db.get_pg_engine", return_value="ENGINE")
    with pytest.raises(TypeError):
        to_db({"not": "a frame"}, "some_table")
