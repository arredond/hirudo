"""Castilla y León: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/castilla_y_leon.py.
"""

import pandas as pd
from utils import db, geocode, opening_hours, points
from utils.crawl import castilla_y_leon, crawl

REGION = "Castilla y León"

LOCATION_COLUMN_ALIASES = {"province": "localidad"}


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape Castilla y León's fixed donation points.

    Each point's Google Maps short link already carries its coordinates (in
    its first redirect, no consent-page follow needed), so no geocoding API
    call is required — and that same short link is kept as gmaps_url so the
    app can link straight to it instead of a composed one.
    """
    df = castilla_y_leon.scrape_fixed_points()
    df.columns = df.columns.map(db.format_column)
    df = df.rename(columns=LOCATION_COLUMN_ALIASES)
    df["localidad"] = df["localidad"].str.title()
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and geocode Castilla y León's mobile donation points.

    Unlike fixed points, mobile points only link to a Google Maps *search*
    (not a specific place), so there's no shortcut around geocoding here.

    The raw "direccion" text often runs the street address, locality, and
    province together with no punctuation (e.g. "El Cabildo, s/n Valladolid
    (VALLADOLID)"), which makes Google drop the house number and geocode the
    street's midpoint instead of the actual point. When "campana" names a
    recognizable place (a shop, a landmark) rather than a generic org/town
    name, geocoding that name plus the locality directly resolves the actual
    point instead — so both candidates are geocoded and the better-scoring
    one is kept (see geocode.geocode_points).
    """
    df = castilla_y_leon.scrape_mobile_points()
    if df.empty:
        # The source page can drop its mobile-points table entirely (see
        # castilla_y_leon.is_mobile_points_table) — upload the other regions
        # rather than failing the whole run.
        return pd.DataFrame(
            columns=[
                "name",
                "localidad",
                "direccion",
                "fecha",
                "horario",
                "opening_hours",
                "url",
                "region",
                "latitude",
                "longitude",
            ]
        )
    df.columns = df.columns.map(db.format_column)
    df["address_direccion"] = df["direccion"].apply(
        lambda direccion: geocode.build_full_address(direccion, REGION)
    )
    df["address_campana"] = points.apply_rows(
        df,
        lambda row: (
            geocode.build_full_address(row["campana"], row["province"].title(), REGION)
            if pd.notna(row["campana"])
            else None
        ),
    )

    df = geocode.geocode_points(
        df, geocode.load_geocoding_cache(), ["address_direccion", "address_campana"]
    )

    df["name"] = "Equipo móvil en " + df["campana"].fillna(df["ubicacion"])
    df["opening_hours"] = points.apply_rows(
        df,
        lambda row: (
            opening_hours.parse_mobile_hours(row["fecha"], row["horario"])
            if pd.notna(row["fecha"])
            else None
        ),
    )
    df["url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df["region"] = REGION
    df = df.rename(columns=LOCATION_COLUMN_ALIASES)
    df["localidad"] = df["localidad"].str.title()

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
    return df[output_cols + ["latitude", "longitude"]]


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape Castilla y León's blood-reserve levels ("niveles de sangre actuales")."""
    df = castilla_y_leon.scrape_blood_levels()
    df["region"] = REGION
    df["source"] = "centrodehemoterapiacyl.es"
    return df
