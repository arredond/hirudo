"""Tests for db.py — column formatting and GeoDataFrame construction."""

import pandas as pd
import pytest
from utils.db import format_column, gdf_from_df

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
