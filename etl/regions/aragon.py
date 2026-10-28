"""Aragón: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/aragon.py.
"""

import pandas as pd
from utils import geocode, opening_hours, points
from utils.crawl import aragon, crawl

REGION = "Aragón"

# (south, west, north, east) box around Aragón, used both to bias Places
# searches and to reject results outside it. Deliberately a loose box rather
# than Aragón's real border: the Banco also runs stops in the Rincón de
# Ademuz, a Valencian exclave between Teruel and Cuenca.
PLACES_BOUNDS = (39.8, -2.3, 42.95, 0.8)


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape and geocode Aragón's fixed donation points.

    The scraped address text carries extra notes (e.g. the Banco's "esquina
    Duquesa Villahermosa. Parking gratuito"), so the center's own name plus
    its city is geocoded alongside it and the better-scoring one is kept
    (see geocode.geocode_points) — every one of these is a well-known hospital/POI.
    Only the Banco itself takes plasma (by appointment); that flag comes from
    the crawler.
    """
    df = aragon.scrape_fixed_points()
    df["address_direccion"] = df.apply(
        lambda row: geocode.build_full_address(
            row["direccion"], row["localidad"], REGION
        ),
        axis=1,
    )
    df["address_name"] = df.apply(
        lambda row: geocode.build_full_address(row["name"], row["localidad"], REGION),
        axis=1,
    )
    df = geocode.geocode_points(
        df, geocode.load_geocoding_cache(), ["address_name", "address_direccion"]
    )
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df.drop(columns=["address_direccion", "address_name"])


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and geocode Aragón's mobile donation points.

    The source carries no address or locality at all — only an event title
    like "Sariñena, en el Centro de Salud" or "Ibercaja, en el Hall del Salón
    Aragón" (a town or an organization, then the venue inside it). Three
    candidates are tried and the best-scoring one kept (see geocode.geocode_points):
    the raw title and "venue + town/organization" through the Geocoding API,
    and the raw title as a Places free-text search — which, like Google
    Maps' own search box, resolves most of these venue descriptions where
    geocoding only manages a town's or the whole region's center. The
    Places result only counts when it passes geocode.place_candidate's checks, and
    the few points none of this gets right are pinned by hand (see
    points.apply_location_overrides).
    "localidad" is left unset, since the part before ", en" is as often an
    organization as a town.
    """
    df = aragon.scrape_mobile_points()
    df["address_title"] = df["title"].apply(
        lambda title: geocode.build_full_address(title, REGION)
    )
    df["address_venue"] = df.apply(
        lambda row: (
            geocode.build_full_address(f"{row['venue']} {row['who']}", REGION)
            if pd.notna(row["venue"])
            else None
        ),
        axis=1,
    )

    geocoding_cache = geocode.refresh_places_cache(
        set(df["title"]), geocode.load_geocoding_cache(), PLACES_BOUNDS
    )
    df["place_title"] = df.apply(
        lambda row: geocode.place_candidate(
            row["title"], row["who"], geocoding_cache, PLACES_BOUNDS
        ),
        axis=1,
    )

    df = geocode.geocode_points(
        df, geocoding_cache, ["address_title", "address_venue", "place_title"]
    )
    df = points.apply_location_overrides(
        df, pd.read_json("utils/aragon_mobile_locations.json"), ["who", "title"]
    )

    df["name"] = "Equipo móvil en " + df["title"]
    df["localidad"] = None
    df["direccion"] = None
    df["opening_hours"] = df.apply(
        lambda row: opening_hours.parse_mobile_hours(row["fecha"], row["horario"]),
        axis=1,
    )
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
