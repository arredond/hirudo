"""Illes Balears: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/balears.py.
"""

import pandas as pd
from utils import opening_hours, points
from utils.crawl import balears, crawl

REGION = "Illes Balears"


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape the Illes Balears' fixed donation centres (Palma, Mahón, Eivissa).

    Each centre's detail page carries its coordinates in its map script, so
    nothing is geocoded. Hours come from the hand-built opening_hours_fijos.json
    lookup, keyed by name; Mahón and Eivissa publish no fixed hours (only "consult
    the campaign calendar"), so they have no entry and surface as a warning.
    """
    df = balears.scrape_fixed_points()
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape the Illes Balears' mobile donation points (the day calendar).

    Each stop's exact coordinates come from its detail page's map script, so
    nothing is geocoded. Each stop is named by its venue. Aféresis sessions
    (apheresis, i.e. plasma) are flagged plasma and not sangre, as Andalucía's
    plasma-only sessions are; every other stop leaves both flags unset.
    """
    output_cols = [
        "name",
        "localidad",
        "direccion",
        "fecha",
        "horario",
        "opening_hours",
        "url",
        "plasma",
        "sangre",
        "region",
    ]
    df = balears.scrape_mobile_points()
    if df.empty:
        return pd.DataFrame(columns=output_cols + ["latitude", "longitude"])

    df["name"] = "Equipo móvil en " + df["lugar"]
    df["opening_hours"] = df.apply(
        lambda row: opening_hours.parse_mobile_hours(
            row["fecha"], row["horario"] or ""
        ),
        axis=1,
    )
    df["plasma"] = df["aferesis"].where(df["aferesis"])
    df["sangre"] = (~df["aferesis"]).where(df["aferesis"])
    df["region"] = REGION
    return df[output_cols + ["latitude", "longitude"]]


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape the Illes Balears' blood-reserve levels ("Niveles de la reserva")."""
    df = balears.scrape_blood_levels()
    df["region"] = REGION
    df["source"] = "donasang.org"
    return df
