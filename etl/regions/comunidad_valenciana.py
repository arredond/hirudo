"""Comunidad Valenciana: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/comunidad_valenciana.py.
"""

import pandas as pd
from utils import geocode, opening_hours, points
from utils.crawl import comunidad_valenciana, crawl

REGION = "Comunidad Valenciana"

PLACES_BOUNDS = (37.8, -1.6, 40.85, 0.75)


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape and geocode Comunidad Valenciana's fixed donation points.

    Their hours aren't a weekly pattern but a day-by-day schedule published
    alongside the mobile stops (see comunidad_valenciana.py), so
    opening_hours is built from that schedule each run (one dated rule per
    day, see opening_hours.parse_scheduled_hours) rather than read from the hand-built
    opening_hours_fijos.json lookup. Geocoded from the street address plus a
    Places search for the center's name (see geocode.geocode_points).
    """
    df = comunidad_valenciana.scrape_fixed_points()
    df["opening_hours"] = df["schedule"].apply(opening_hours.parse_scheduled_hours)
    df["address_direccion"] = df.apply(
        lambda row: geocode.build_full_address(
            row["direccion"], row["localidad"], REGION
        ),
        axis=1,
    )
    df["place_query"] = df["name"] + ", " + df["localidad"]
    geocoding_cache = geocode.refresh_places_cache(
        set(df["place_query"]), geocode.load_geocoding_cache(), PLACES_BOUNDS
    )
    df["place_name"] = points.apply_rows(
        df,
        lambda row: geocode.place_candidate(
            row["place_query"],
            row["localidad"],
            geocoding_cache,
            PLACES_BOUNDS,
        ),
    )
    df = geocode.geocode_points(
        df, geocoding_cache, ["address_direccion", "place_name"]
    )
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df["region"] = REGION
    return df.drop(
        columns=["schedule", "address_direccion", "place_query", "place_name"]
    )


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and geocode Comunidad Valenciana's mobile donation points.

    Each stop has a town ("Población") and a venue + street address
    ("Ubicación"), split apart by the crawler. Two candidates are tried and
    the best-scoring one kept (see geocode.geocode_points): the street address via
    the Geocoding API, and the venue name via a Places search (checked to be
    in the region and in the right town, see geocode.place_candidate).

    Stops restricted to a group (e.g. "(SOLO EMPLEADOS)") are kept, with
    the note appended to the name so it's always visible. Plasma-only stops
    ("SOLO DONACIÓN DE PLASMA CON CITA PREVIA") get sangre: False, like
    Castilla-La Mancha's.
    """
    df = comunidad_valenciana.scrape_mobile_points()
    df["localidad"] = df["poblacion"].str.title()
    df["address_direccion"] = df.apply(
        lambda row: geocode.build_full_address(
            row["direccion"] if pd.notna(row["direccion"]) else row["venue"],
            row["localidad"],
            REGION,
        ),
        axis=1,
    )
    df["place_query"] = df["venue"] + ", " + df["localidad"]
    geocoding_cache = geocode.refresh_places_cache(
        set(df["place_query"]), geocode.load_geocoding_cache(), PLACES_BOUNDS
    )
    df["place_venue"] = points.apply_rows(
        df,
        lambda row: geocode.place_candidate(
            row["place_query"],
            row["poblacion"],
            geocoding_cache,
            PLACES_BOUNDS,
        ),
    )
    df = geocode.geocode_points(
        df, geocoding_cache, ["address_direccion", "place_venue"]
    )

    df["name"] = "Equipo móvil en " + df["venue"]
    restricted = df["restriction"].notna()
    df.loc[restricted, "name"] += " " + df.loc[restricted, "restriction"]
    df["opening_hours"] = points.apply_rows(
        df,
        lambda row: opening_hours.parse_mobile_hours(row["fecha"], row["horario"]),
    )
    df["url"] = df["province"].apply(comunidad_valenciana.province_url)
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
        "cita_previa",
        "region",
    ]
    return df[output_cols + ["latitude", "longitude"]]
