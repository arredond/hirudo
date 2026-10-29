"""Principado de Asturias: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/asturias.py.
"""

import pandas as pd
from utils import geocode, opening_hours, points
from utils.crawl import asturias, crawl

REGION = "Principado de Asturias"

PLACES_BOUNDS = (42.8, -7.25, 43.7, -4.45)


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape and geocode Principado de Asturias' fixed donation points.

    Each centre's Google Maps embed carries its coordinates, used as-is;
    only a centre whose embed has none is geocoded from its address (see
    geocode.geocode_points). Hours come from the hand-built opening_hours_fijos.json
    lookup, keyed by name.
    """
    df = asturias.scrape_fixed_points()
    missing = df["latitude"].isna()
    df["address_direccion"] = df.apply(
        lambda row: geocode.build_full_address(row["direccion"]), axis=1
    ).where(missing)
    df = geocode.geocode_missing_coords(df, "address_direccion")
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df.drop(columns=["address_direccion"])


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and geocode Principado de Asturias' mobile donation points.

    Each calendar event is one town and day, and each spot in it (see
    asturias.py) becomes its own row. The calendar has no coordinates, so
    two candidates are tried and the best-scoring one kept (see
    geocode.geocode_points): the spot's address via the Geocoding API, and its venue
    via a Places search, checked to be in the region and the town (see
    geocode.place_candidate). Organization-titled events ("Acuartelamiento Cabo
    Noval") are checked against that name, so their Places match may be
    rejected in favour of the address.
    """
    df = asturias.scrape_mobile_points()
    df["address_place"] = df.apply(
        lambda row: geocode.build_full_address(
            row["direccion"].rstrip(". "), row["localidad"], REGION
        ),
        axis=1,
    )
    df["place_query"] = df["lugar"] + ", " + df["localidad"]
    geocoding_cache = geocode.refresh_places_cache(
        set(df["place_query"]), geocode.load_geocoding_cache(), PLACES_BOUNDS
    )
    df["place_venue"] = points.apply_rows(
        df,
        lambda row: geocode.place_candidate(
            row["place_query"],
            row["localidad"],
            geocoding_cache,
            PLACES_BOUNDS,
        ),
    )
    df = geocode.geocode_points(df, geocoding_cache, ["address_place", "place_venue"])

    df["name"] = "Equipo móvil en " + df["lugar"]
    df["opening_hours"] = points.apply_rows(
        df,
        lambda row: opening_hours.parse_mobile_hours(row["fecha"], row["horario"]),
    )
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
        "medula",
        "region",
    ]
    return df[output_cols + ["latitude", "longitude"]]


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape Principado de Asturias' blood-reserve levels (gauges, read off their needles)."""
    df = asturias.scrape_blood_levels()
    df["region"] = REGION
    df["source"] = "donasturias.org"
    return df
