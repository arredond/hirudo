"""Cataluña: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/cataluna.py.
"""

import pandas as pd
from utils import geocode, opening_hours, points
from utils.crawl import cataluna, crawl

REGION = "Cataluña"

PLACES_BOUNDS = (40.5, 0.15, 42.9, 3.35)


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape and geocode Cataluña's fixed donation points (hospitals).

    Geocoded from the street address plus a Places search for the
    hospital's name (see geocode.geocode_points). Their "Cómo llegar" links do carry
    coordinates, but the site truncates some of them mid-number, so they
    aren't relied on. Opening hours come from the hand-built
    opening_hours_fijos.json lookup, keyed by name.
    """
    df = cataluna.scrape_fixed_points()
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
    df["place_name"] = df.apply(
        lambda row: geocode.place_candidate(
            row["place_query"],
            row["localidad"],
            geocoding_cache,
            PLACES_BOUNDS,
        ),
        axis=1,
    )
    df = geocode.geocode_points(
        df, geocoding_cache, ["address_direccion", "place_name"]
    )
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df.drop(columns=["address_direccion", "place_query", "place_name"])


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and geocode Cataluña's mobile donation points.

    Each stop has a town, a venue and a street address. Two candidates are
    tried and the best-scoring one kept (see geocode.geocode_points): the street
    address via the Geocoding API, and the venue name via a Places search
    (checked to be in the region and town, see geocode.place_candidate) — except
    for donation-bus stops ("Unidad móvil"), whose street address is the
    actual spot and whose venue text isn't a place Places could find.

    The few stops none of this gets right — mostly villages inside a
    multi-village municipality, where Google's address names the village
    rather than the "Población" (e.g. Ordal, in Subirats) — are pinned by
    hand (see points.apply_location_overrides).

    Donation types come straight from each stop's booking buttons: most
    take blood, many also plasma, and a few are plasma-only (sangre:
    False). Plasma-only stops have no published hours, so their
    opening_hours stays None (see cataluna.scrape_mobile_points).
    """
    df = cataluna.scrape_mobile_points()
    df["address_direccion"] = df.apply(
        lambda row: geocode.build_full_address(
            row["direccion"] if pd.notna(row["direccion"]) else row["venue"],
            row["localidad"],
            REGION,
        ),
        axis=1,
    )
    searchable = ~df["venue"].apply(cataluna.is_mobile_unit)
    df["place_query"] = (df["venue"] + ", " + df["localidad"]).where(searchable)
    geocoding_cache = geocode.refresh_places_cache(
        set(df["place_query"].dropna()),
        geocode.load_geocoding_cache(),
        PLACES_BOUNDS,
    )
    df["place_venue"] = df.apply(
        lambda row: (
            geocode.place_candidate(
                row["place_query"],
                row["localidad"],
                geocoding_cache,
                PLACES_BOUNDS,
            )
            if pd.notna(row["place_query"])
            else None
        ),
        axis=1,
    )
    df = geocode.geocode_points(
        df, geocoding_cache, ["address_direccion", "place_venue"]
    )
    # Pinned by "venue, town" for a fixed venue, or "street, town" where the
    # street is what identifies the stop (a donation bus's square, or a
    # venue that isn't on Google Maps at all).
    df["venue_key"] = df["venue"] + ", " + df["localidad"]
    df["address_key"] = df["direccion"] + ", " + df["localidad"]
    df = points.apply_location_overrides(
        df,
        pd.read_json("utils/cataluna_mobile_locations.json"),
        ["venue_key", "address_key"],
    )

    df["name"] = "Equipo móvil en " + df["venue"]
    df["opening_hours"] = df.apply(
        lambda row: (
            opening_hours.parse_mobile_hours(row["fecha"], row["horario"])
            if pd.notna(row["horario"])
            else None
        ),
        axis=1,
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
        "plasma",
        "sangre",
        "medula",
        "region",
    ]
    return df[output_cols + ["latitude", "longitude"]]
