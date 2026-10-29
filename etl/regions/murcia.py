"""Región de Murcia: scrape and enrich its donation points for the ETL.

Raw page parsing lives in utils/crawl/murcia.py. Every point's map popup
carries its coordinates, so nothing is geocoded.
"""

import pandas as pd
from utils import opening_hours, points
from utils.crawl import crawl, murcia

REGION = "Región de Murcia"


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape Murcia's fixed donation points.

    Coordinates come from each point's map popup. Hours come from the
    hand-built opening_hours_fijos.json lookup, keyed by name.
    """
    df = murcia.scrape_fixed_points()
    if df.empty:
        return df.assign(gmaps_url=None, opening_hours=None, region=REGION)
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape Murcia's mobile donation points from its collection calendar."""
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
    df = murcia.scrape_mobile_points()
    if df.empty:
        return pd.DataFrame(columns=output_cols + ["latitude", "longitude"])

    df["name"] = "Equipo móvil en " + df["lugar"]
    df["opening_hours"] = points.apply_rows(
        df,
        lambda row: opening_hours.parse_mobile_hours(row["fecha"], row["horario"]),
    )
    df["region"] = REGION
    return df[output_cols + ["latitude", "longitude"]]


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape Murcia's blood-reserve levels ("Niveles de reserva")."""
    df = murcia.scrape_blood_levels()
    df["region"] = REGION
    df["source"] = "murciasalud.es"
    return df
