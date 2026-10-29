"""Andalucía: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/andalucia.py.
"""

import pandas as pd
from utils import geocode, opening_hours, points
from utils.crawl import andalucia, crawl

REGION = "Andalucía"


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape and geocode Andalucía's fixed donation points (one CTTC per province).

    Each centre's weekly timetable goes straight into opening_hours (see
    opening_hours.parse_weekly_hours), so nothing comes from the hand-built lookup. The
    pages carry no coordinates, so each centre is geocoded from its street
    address (see geocode.geocode_points).
    """
    df = andalucia.scrape_fixed_points()
    df["opening_hours"] = df["schedule"].apply(opening_hours.parse_weekly_hours)
    df["full_address"] = df.apply(
        lambda row: geocode.build_full_address(
            row["direccion"], row["localidad"], REGION
        ),
        axis=1,
    )
    df = geocode.geocode_points(df, geocode.load_geocoding_cache(), "full_address")
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df["region"] = REGION
    return df.drop(columns=["schedule", "full_address", "provincia"])


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and geocode Andalucía's mobile donation points.

    Like Castilla-La Mancha's, a stop has only a town and a venue ("Lugar",
    e.g. "CENTRO DE SALUD"), so that pair is the one geocoding candidate.
    Hours are parsed per day (see opening_hours.parse_mobile_hours); open-ended ones such
    as "DESDE LAS 17,00 HORAS" are assumed to close at 20:00 (see
    andalucia.normalize_hours). Plasma-only sessions at a centre
    are flagged plasma (and not sangre); every other stop leaves both unset,
    since the source doesn't say.
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
    df = andalucia.scrape_mobile_points()
    if df.empty:
        return pd.DataFrame(columns=output_cols + ["latitude", "longitude"])

    df["full_address"] = df.apply(
        lambda row: geocode.build_full_address(row["lugar"], row["localidad"], REGION),
        axis=1,
    )
    df = geocode.geocode_points(df, geocode.load_geocoding_cache(), "full_address")

    df["name"] = "Equipo móvil en " + df["lugar"] + ", " + df["localidad"]
    df["direccion"] = df["lugar"]
    df["opening_hours"] = points.apply_rows(
        df,
        lambda row: opening_hours.parse_mobile_hours(row["fecha"], row["horario"]),
    )
    df["plasma"] = df["plasma_only"].where(df["plasma_only"])
    df["sangre"] = (~df["plasma_only"]).where(df["plasma_only"])
    df["region"] = REGION
    return df[output_cols + ["latitude", "longitude"]]
