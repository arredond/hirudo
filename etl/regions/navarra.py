"""Comunidad Foral de Navarra: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/navarra.py.
"""

import pandas as pd
from utils import geocode, opening_hours, points
from utils.crawl import crawl, navarra

REGION = "Comunidad Foral de Navarra"

PLACES_BOUNDS = (41.85, -2.3, 43.4, -0.65)


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape Navarra's fixed donation points (ADONA's Pamplona and Tudela banks).

    Each contact page's map carries the spot's coordinates, so nothing is
    geocoded. Hours are hand-translated into opening_hours_fijos.json, keyed
    by name. Both spots take plasma by aféresis (see navarra.py), so both
    get plasma and sangre set.
    """
    df = navarra.scrape_fixed_points()
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df = points.add_opening_hours(df)
    df["plasma"] = True
    df["sangre"] = True
    df["region"] = REGION
    return df


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and geocode Navarra's mobile donation points.

    The calendar gives only a town and a venue ("LUMBIER 16:45 - 21:00" with
    "Centro Cívico" underneath), so the venue plus town is both geocoded and
    searched with Places, and the better-scoring one kept (see
    geocode.geocode_points). The Places result only counts when it passes
    geocode.place_candidate's town check. Name is "Equipo móvil en <town> (<venue>)".

    Both donation types are offered on the booking page's Unidad móvil entry
    ("Dona Sangre" and "Dona aféresis"), so every stop gets plasma and sangre.
    """
    df = navarra.scrape_mobile_points()
    df["address_lugar"] = df.apply(
        lambda row: geocode.build_full_address(row["lugar"], row["localidad"], REGION),
        axis=1,
    )
    df["place_query"] = df["lugar"] + ", " + df["localidad"]
    geocoding_cache = geocode.refresh_places_cache(
        set(df["place_query"]), geocode.load_geocoding_cache(), PLACES_BOUNDS
    )
    df["place_lugar"] = df.apply(
        lambda row: geocode.place_candidate(
            row["place_query"],
            row["localidad"],
            geocoding_cache,
            PLACES_BOUNDS,
        ),
        axis=1,
    )
    df = geocode.geocode_points(df, geocoding_cache, ["address_lugar", "place_lugar"])

    df["name"] = "Equipo móvil en " + df["localidad"] + " (" + df["lugar"] + ")"
    df["direccion"] = None
    df["opening_hours"] = df.apply(
        lambda row: opening_hours.parse_mobile_hours(row["fecha"], row["horario"]),
        axis=1,
    )
    df["plasma"] = True
    df["sangre"] = True
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
