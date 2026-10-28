"""Galicia: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/galicia.py.
"""

import re

import pandas as pd
from utils import geocode, opening_hours, points
from utils.crawl import crawl, galicia

REGION = "Galicia"

PLACES_BOUNDS = (41.8, -9.35, 43.8, -6.7)

# Galician mobile stops' "Lugar de colecta" decorations that aren't part of
# the place's name: a neighbourhood or housing-estate marker ("Bº NOVO
# MESOIRO", "URB. LA BARCALA") and a parenthesized town ("(A CORUÑA)").
LUGAR_NOISE_RE = re.compile(r"^(?:Bº|URB\.)\s*|\s*\([^)]*\)")

# Galician particles that str.title() wrongly capitalizes mid-name ("O Barco
# De Valdeorras" -> "O Barco de Valdeorras").
NAME_PARTICLE_RE = re.compile(r"(?<=\s)(?:De|Do|Da|Dos|Das|E)(?=\s)")


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape Galicia's fixed donation points ("Locais de doazón").

    Most carry GPS coordinates on the page, used as-is; the rest are
    geocoded from their first address line. Opening hours come from the
    hand-built opening_hours_fijos.json lookup, keyed by name.
    """
    df = galicia.scrape_fixed_points()
    missing = df["latitude"].isna()
    df["address_venue"] = df.apply(
        lambda row: geocode.build_full_address(
            row["venue"].split(". ")[0], row["localidad"], REGION
        ),
        axis=1,
    ).where(missing)
    df = geocode.geocode_missing_coords(df, "address_venue")
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df.drop(columns=["venue", "address_venue"])


def clean_lugar(lugar: str) -> str:
    """Strip a Galician "Lugar de colecta"'s decorations (LUGAR_NOISE_RE)."""
    return LUGAR_NOISE_RE.sub("", lugar).strip()


def title_name(text: str) -> str:
    """Title-case an all-caps Galician name, keeping its particles lowercase."""
    return NAME_PARTICLE_RE.sub(lambda match: match.group().lower(), text.title())


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and geocode Galicia's mobile donation points.

    Every stop is a donation bus parked at a described spot ("UNIDADE MÓBIL
    DIANTE DA CASA DA XUVENTUDE") in a collection place ("Lugar de colecta":
    a town, parish, neighbourhood or campus) within a concello. The spot
    description (minus the bus lead-in) plus place and concello is searched
    with Places, and the result used whenever it's in the region and in the
    place or concello (see geocode.place_candidate); the Geocoding API's result for
    the same text is only the fallback. Unlike other regions, the two aren't
    compared by score: these descriptions ("CENTRO DE SAUDE, Cambados") are
    no postal address, and geocoding them often returns a ROOFTOP match at
    some other building. Spots neither gets right are pinned by hand (see
    points.apply_location_overrides), matched by "description, concello".

    Stops marked "Provisional" are kept, with the note in the name.
    """
    df = galicia.scrape_mobile_points()
    df["lugar_clean"] = df["lugar"].apply(clean_lugar)
    df["place_query"] = df.apply(
        lambda row: ", ".join(
            dict.fromkeys(
                [row["place_text"], row["lugar_clean"].title(), row["concello"]]
            )
        ),
        axis=1,
    )
    df["address_place"] = df.apply(
        lambda row: geocode.build_full_address(row["place_query"], REGION), axis=1
    )
    geocoding_cache = geocode.refresh_places_cache(
        set(df["place_query"]), geocode.load_geocoding_cache(), PLACES_BOUNDS
    )
    df["place_venue"] = df.apply(
        lambda row: geocode.place_candidate(
            row["place_query"],
            f"{row['lugar_clean']}/{row['concello']}",
            geocoding_cache,
            PLACES_BOUNDS,
        ),
        axis=1,
    )
    df["best_query"] = df["place_venue"].fillna(df["address_place"])
    df = geocode.geocode_points(df, geocoding_cache, "best_query")
    df["location_key"] = df["place_text"] + ", " + df["concello"]
    df = points.apply_location_overrides(
        df, pd.read_json("utils/galicia_mobile_locations.json"), ["location_key"]
    )

    df["name"] = "Equipo móvil en " + df["lugar"].apply(title_name)
    df.loc[df["provisional"], "name"] += " (provisional)"
    df["localidad"] = df["concello"]
    df["opening_hours"] = df.apply(
        lambda row: opening_hours.parse_mobile_hours(row["fecha"], row["horario"]),
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
        "medula",
        "region",
    ]
    return df[output_cols + ["latitude", "longitude"]]


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape Galicia's blood-reserve levels ("Semáforo", read off an image)."""
    df = galicia.scrape_blood_levels()
    df["region"] = REGION
    df["source"] = "ados.sergas.gal"
    return df
