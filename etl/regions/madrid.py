"""Comunidad de Madrid: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/madrid.py.
"""

import pandas as pd
from utils import db, geocode, opening_hours, points
from utils.crawl import crawl, madrid

REGION = "Comunidad de Madrid"

# Fixed points carry a handful of concepts every region has, under whatever
# name that region's own source happens to spell them with. Renaming them to
# one shared name per concept here — rather than in the frontend — keeps the
# app itself region-agnostic: it always reads "direccion"/"localidad"/
# "horario" regardless of which region a point came from. Region-specific
# extras with no equivalent elsewhere (e.g. Madrid's "observaciones") are left
# as-is; the frontend just treats them as absent for other regions.
FIXED_POINT_COLUMN_ALIASES = {
    "direccion_postal": "direccion",
    "municipio": "localidad",
    "horario_de_donaciones": "horario",
}


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape and enrich Comunidad de Madrid's fixed donation points."""
    manual_points = pd.read_json("utils/puntos_fijos_no_hospitales.json")
    other_donations = pd.read_json("utils/puntos_fijos_otras_donaciones.json")

    df = madrid.scrape_fixed_points()
    df.columns = df.columns.map(db.format_column)
    df = pd.concat([manual_points, df], ignore_index=True)
    df = df.rename(columns=FIXED_POINT_COLUMN_ALIASES)
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df = points.add_opening_hours(df)

    other_donations.columns = other_donations.columns.map(db.format_column)
    df = pd.merge(df, other_donations, on="name", how="left")
    df["region"] = REGION
    return df


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and geocode Comunidad de Madrid's mobile donation points."""
    df = madrid.scrape_mobile_points()
    df.columns = df.columns.map(db.format_column)

    # Strip location-type prefixes from the address field
    for prefix in ["Equipo móvil en ", "E Móvil en ", "Equipo Móvil detrás "]:
        df["direccion"] = df["direccion"].str.replace(prefix, "", regex=False)

    # Hardcoded fix for a recurring typo on the source site: "13.a45" instead
    # of "13:45", which otherwise fails opening_hours parsing.
    df["horario"] = df["horario"].str.replace("13.a45", "13:45", regex=False)

    df = geocode.geocode_mobile_points(df, geocode.load_geocoding_cache(), REGION)

    df["name"] = "Equipo móvil en " + df["lugar"]
    df["opening_hours"] = points.apply_rows(
        df,
        lambda row: opening_hours.parse_mobile_hours(row["fecha"], row["horario"]),
    )
    df["url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df["region"] = REGION

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
    """Scrape Comunidad de Madrid's blood-reserve levels ("semáforo de necesidades")."""
    df = madrid.scrape_blood_levels()
    df["region"] = REGION
    df["source"] = "donarsangre.org"
    return df
