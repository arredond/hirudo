"""Canarias: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/canarias.py.
"""

import pandas as pd
from utils import geocode, opening_hours, points
from utils.crawl import canarias, crawl

REGION = "Canarias"


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape and geocode Canarias' fixed donation points.

    Each point's map link carries its coordinates, used as-is; only a point
    whose link has none is geocoded from its address (see geocode.geocode_points).
    Hours come from the hand-built opening_hours_fijos.json lookup, keyed by
    name.
    """
    df = canarias.scrape_fixed_points()
    missing = df["latitude"].isna()
    df["address_direccion"] = df.apply(
        lambda row: geocode.build_full_address(
            row["direccion"] if pd.notna(row["direccion"]) else row["localidad"],
            row["localidad"],
            REGION,
        ),
        axis=1,
    ).where(missing)
    df = geocode.geocode_missing_coords(df, "address_direccion")
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df.drop(columns=["address_direccion"])


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and geocode Canarias' mobile donation points.

    Each stop's map link carries its coordinates. A stop whose link has none
    is geocoded from its street address (or its town) through the geocoding
    cache, and the page's coordinates win wherever they exist.
    """
    output_cols = [
        "name",
        "localidad",
        "direccion",
        "fecha",
        "horario",
        "opening_hours",
        "url",
        "region",
    ]
    df = canarias.scrape_mobile_points()
    if df.empty:
        return pd.DataFrame(columns=output_cols + ["latitude", "longitude"])

    missing = df["latitude"].isna()
    df["address_direccion"] = df.apply(
        lambda row: geocode.build_full_address(
            row["direccion"] if pd.notna(row["direccion"]) else row["lugar"],
            row["localidad"],
            REGION,
        ),
        axis=1,
    ).where(missing)
    df = geocode.geocode_missing_coords(df, "address_direccion")

    df["name"] = "Equipo móvil en " + df["lugar"]
    df["opening_hours"] = df.apply(
        lambda row: opening_hours.parse_mobile_hours(row["fecha"], row["horario"]),
        axis=1,
    )
    df["region"] = REGION
    return df[output_cols + ["latitude", "longitude"]]
