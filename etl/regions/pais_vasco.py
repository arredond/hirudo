"""País Vasco: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/pais_vasco.py.
"""

import pandas as pd
from utils import opening_hours, points
from utils.crawl import crawl, pais_vasco

REGION = "País Vasco"


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape País Vasco's fixed donation points (the permanent centres).

    Like Comunidad Valenciana's, their hours are a day-by-day schedule from
    the same listings as the mobile stops (see pais_vasco.py), so
    opening_hours is built from it each run (see opening_hours.parse_scheduled_hours).
    Every listing links to the spot's coordinates, so nothing is geocoded.
    Plasma-only ones get sangre: False; the rest leave both flags unset (the
    source doesn't say which centres take plasma, only to book it by phone).
    """
    df = pais_vasco.scrape_fixed_points()
    df["opening_hours"] = df["schedule"].apply(opening_hours.parse_scheduled_hours)
    df["plasma"] = df["plasma_only"].where(df["plasma_only"])
    df["sangre"] = (~df["plasma_only"]).where(df["plasma_only"])
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df["region"] = REGION
    return df.drop(columns=["schedule", "plasma_only"])


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape País Vasco's mobile donation points.

    Every stop links to its exact coordinates on Google Maps, so nothing is
    geocoded. Plasma-only stops ("Solo Plasma/Cita") get sangre: False, like
    Castilla-La Mancha's; company/school-only ones ("(colecta privada)")
    keep that note in their name, as the source shows it.
    """
    df = pais_vasco.scrape_mobile_points()
    df["name"] = "Equipo móvil en " + df["lugar"]
    df["opening_hours"] = points.apply_rows(
        df,
        lambda row: opening_hours.parse_mobile_hours(row["fecha"], row["horario"]),
    )
    df["plasma"] = df["plasma_only"]
    df["sangre"] = ~df["plasma_only"]
    df["medula"] = False
    df["region"] = REGION

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
        "medula",
        "region",
    ]
    return df[output_cols + ["latitude", "longitude"]]


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape País Vasco's blood-reserve levels ("niveles de sangre actuales")."""
    df = pais_vasco.scrape_blood_levels()
    df["region"] = REGION
    df["source"] = "donantesdesangre.eus"
    return df
