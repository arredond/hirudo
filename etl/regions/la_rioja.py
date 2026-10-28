"""La Rioja: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/la_rioja.py.
"""

import pandas as pd
from utils import geocode, opening_hours, points
from utils.crawl import crawl, la_rioja

REGION = "La Rioja"


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape La Rioja's fixed donation point (the Banco de Sangre).

    Its coordinates come from the page's own map marker, so nothing is
    geocoded. Hours come from the hand-built opening_hours_fijos.json lookup,
    keyed by name.
    """
    df = la_rioja.scrape_fixed_points()
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and geocode La Rioja's mobile donation points.

    Each stop's exact coordinates come from its detail page's embedded map.
    Some stops' maps carry none, so those are geocoded from their street
    address (or their town) through the geocoding cache, and the page's
    coordinates win wherever they exist.
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
    df = la_rioja.scrape_mobile_points()
    if df.empty:
        return pd.DataFrame(columns=output_cols + ["latitude", "longitude"])

    missing = df["latitude"].isna()
    df["address_direccion"] = df.apply(
        lambda row: geocode.build_full_address(
            row["direccion"] or row["localidad"], row["localidad"], REGION
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


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape La Rioja's blood-reserve levels ("Estado de las reservas")."""
    df = la_rioja.scrape_blood_levels()
    df["region"] = REGION
    df["source"] = "bancosangrerioja.org"
    return df
