"""Blood donation points ETL — runs as a single Cloud Run job

To run locally, make sure you have a valid .env file. Then:

from dotenv import load_dotenv
load_dotenv()

import main
main.run_etl()
"""

import json
import logging
import re

import pandas as pd
from utils.crawl import (
    aragon,
    cantabria,
    castilla_la_mancha,
    castilla_y_leon,
    cataluna,
    comunidad_valenciana,
    crawl,
    galicia,
    madrid,
    pais_vasco,
)
from utils.db import format_column, from_db, gdf_from_df, to_db
from utils.geocode import (
    PLACE_SCORE,
    build_full_address,
    find_place,
    geocode_address,
    place_matches,
)
from utils.opening_hours import parse_mobile_hours, parse_scheduled_hours

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Every output table this ETL writes carries a region column (Comunidad
# Autónoma), stamped by each region's own scrape_*_<region> function below so
# a table can hold rows from several regions at once (the app filters by
# it). The geocoding_cache is shared across all regions and keyed by full
# address strings that already name the region, so it is left unstamped.
REGION_MADRID = "Comunidad de Madrid"
REGION_CYL = "Castilla y León"
REGION_CLM = "Castilla-La Mancha"
REGION_ARAGON = "Aragón"
REGION_VALENCIA = "Comunidad Valenciana"
REGION_CATALUNA = "Cataluña"
REGION_GALICIA = "Galicia"
REGION_PAIS_VASCO = "País Vasco"
REGION_CANTABRIA = "Cantabria"

# Fixed points carry a handful of concepts every region has, under whatever
# name that region's own source happens to spell them with. Renaming them to
# one shared name per concept here — rather than in the frontend — keeps the
# app itself region-agnostic: it always reads "direccion"/"localidad"/
# "horario" regardless of which region a point came from. Region-specific
# extras with no equivalent elsewhere (e.g. Madrid's "observaciones") are left
# as-is; the frontend just treats them as absent for other regions.
MADRID_FIXED_POINT_COLUMN_ALIASES = {
    "direccion_postal": "direccion",
    "municipio": "localidad",
    "horario_de_donaciones": "horario",
}
CYL_LOCATION_COLUMN_ALIASES = {"province": "localidad"}

# Places ("Find Place") results share the geocoding_cache table with
# geocoding results; this prefix on their cache key keeps a free-text query
# from colliding with the same text geocoded as an address.
PLACE_CACHE_PREFIX = "place: "

# (south, west, north, east) box around Aragón, used both to bias Places
# searches and to reject results outside it. Deliberately a loose box rather
# than Aragón's real border: the Banco also runs stops in the Rincón de
# Ademuz, a Valencian exclave between Teruel and Cuenca.
ARAGON_PLACES_BOUNDS = (39.8, -2.3, 42.95, 0.8)
VALENCIA_PLACES_BOUNDS = (37.8, -1.6, 40.85, 0.75)
CATALUNA_PLACES_BOUNDS = (40.5, 0.15, 42.9, 3.35)
GALICIA_PLACES_BOUNDS = (41.8, -9.35, 43.8, -6.7)

# Galician mobile stops' "Lugar de colecta" decorations that aren't part of
# the place's name: a neighbourhood or housing-estate marker ("Bº NOVO
# MESOIRO", "URB. LA BARCALA") and a parenthesized town ("(A CORUÑA)").
GALICIA_LUGAR_NOISE_RE = re.compile(r"^(?:Bº|URB\.)\s*|\s*\([^)]*\)")

# Galician particles that str.title() wrongly capitalizes mid-name ("O Barco
# De Valdeorras" -> "O Barco de Valdeorras").
GALICIA_NAME_PARTICLE_RE = re.compile(r"(?<=\s)(?:De|Do|Da|Dos|Das|E)(?=\s)")


def opening_hours_for_fixed_point(row, lookup):
    """Look up a fixed point's hand-built OSM opening_hours string.

    Keyed by center_id where available, else by name (for the manual
    non-hospital entries, which have no center_id). Logs a warning and
    returns None for anything missing from the lookup, so it surfaces for a
    manual update rather than silently going unset.
    """
    hours = lookup.get(row.get("center_id")) or lookup.get(row["name"])
    if hours is None:
        log.warning("No opening_hours lookup entry for fixed point: %s", row["name"])
    return hours


def load_opening_hours_fijos() -> dict:
    """Load the hand-built OSM opening_hours lookup for fixed points.

    Shared by every region's fixed points (see opening_hours_for_fixed_point) —
    it's one file keyed by center_id where available, else by name.
    """
    with open("utils/opening_hours_fijos.json", encoding="utf-8") as f:
        return json.load(f)


def scrape_fixed_points_madrid() -> pd.DataFrame:
    """Scrape and enrich Comunidad de Madrid's fixed donation points."""
    manual_points = pd.read_json("utils/puntos_fijos_no_hospitales.json")
    other_donations = pd.read_json("utils/puntos_fijos_otras_donaciones.json")
    opening_hours_lookup = load_opening_hours_fijos()

    df = madrid.scrape_fixed_points()
    df.columns = df.columns.map(format_column)
    df = pd.concat([manual_points, df], ignore_index=True)
    df = df.rename(columns=MADRID_FIXED_POINT_COLUMN_ALIASES)
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df["opening_hours"] = df.apply(
        opening_hours_for_fixed_point, lookup=opening_hours_lookup, axis=1
    )

    other_donations.columns = other_donations.columns.map(format_column)
    df = pd.merge(df, other_donations, on="name", how="left")
    df["region"] = REGION_MADRID
    return df


def scrape_fixed_points_cyl() -> pd.DataFrame:
    """Scrape Castilla y León's fixed donation points.

    Each point's Google Maps short link already carries its coordinates (in
    its first redirect, no consent-page follow needed), so no geocoding API
    call is required — and that same short link is kept as gmaps_url so the
    app can link straight to it instead of a composed one.
    """
    df = castilla_y_leon.scrape_fixed_points()
    df.columns = df.columns.map(format_column)
    df = df.rename(columns=CYL_LOCATION_COLUMN_ALIASES)
    df["localidad"] = df["localidad"].str.title()
    opening_hours_lookup = load_opening_hours_fijos()
    df["opening_hours"] = df.apply(
        opening_hours_for_fixed_point, lookup=opening_hours_lookup, axis=1
    )
    df["region"] = REGION_CYL
    return df


def refresh_geocoding_cache(
    addresses: set[str], geocoding_cache: pd.DataFrame
) -> pd.DataFrame:
    """Geocode any addresses missing from the cache and persist the update.

    Returns geocoding_cache, extended with newly geocoded addresses when
    there were any missing (and left untouched, with no DB write, when the
    cache already covered every address).
    """
    cached_addresses = set(geocoding_cache["address"])
    new_rows = []
    for address in addresses - cached_addresses:
        log.info("Geocoding: %s", address)
        lng, lat, location_type, score = geocode_address(address)
        new_rows.append(
            {
                "address": address,
                "longitude": lng,
                "latitude": lat,
                "location_type": location_type,
                "score": score,
            }
        )

    if new_rows:
        geocoding_cache = pd.concat(
            [geocoding_cache, pd.DataFrame(new_rows)], ignore_index=True
        )
        geocoding_cache = geocoding_cache.drop_duplicates(subset=["address"])
        to_db(geocoding_cache, "geocoding_cache")

    return geocoding_cache


def refresh_places_cache(
    queries: set[str], geocoding_cache: pd.DataFrame, bounds: tuple
) -> pd.DataFrame:
    """Run a Places search for any query missing from the cache and persist it.

    Same contract as refresh_geocoding_cache, but keyed by
    PLACE_CACHE_PREFIX + query and keeping the matched place's name and
    address too, so place_candidate can check the match later without
    another API call. Not-found queries are cached as well (with no
    coordinates), so they aren't retried every run.
    """
    south, west, north, east = bounds
    location_bias = f"rectangle:{south},{west}|{north},{east}"
    cached_addresses = set(geocoding_cache["address"])
    new_rows = []
    for query in queries:
        key = PLACE_CACHE_PREFIX + query
        if key in cached_addresses:
            continue
        log.info("Place search: %s", query)
        lng, lat, name, address = find_place(query, location_bias)
        new_rows.append(
            {
                "address": key,
                "longitude": lng,
                "latitude": lat,
                "location_type": "PLACE",
                "score": PLACE_SCORE if lng is not None else None,
                "place_name": name,
                "place_address": address,
            }
        )

    if new_rows:
        geocoding_cache = pd.concat(
            [geocoding_cache, pd.DataFrame(new_rows)], ignore_index=True
        )
        geocoding_cache = geocoding_cache.drop_duplicates(subset=["address"])
        to_db(geocoding_cache, "geocoding_cache")

    return geocoding_cache


def place_candidate(
    query: str, expected: str, geocoding_cache: pd.DataFrame, bounds: tuple
) -> str | None:
    """Return a query's Places cache key if its result is trustworthy, else None.

    The result must fall inside bounds and mention the expected town or
    organization name (see place_matches) — Places otherwise happily returns
    a same-named place in another region (or country). The key returned can
    be passed to geocode_points as one more candidate column.
    """
    key = PLACE_CACHE_PREFIX + query
    cached = geocoding_cache.loc[geocoding_cache["address"] == key]
    if cached.empty or pd.isna(cached["latitude"].iloc[0]):
        return None
    place = cached.iloc[0]
    south, west, north, east = bounds
    in_bounds = (
        south <= place["latitude"] <= north and west <= place["longitude"] <= east
    )
    if in_bounds and place_matches(
        expected, place["place_name"], place["place_address"]
    ):
        return key
    return None


def geocode_mobile_points(
    df: pd.DataFrame, geocoding_cache: pd.DataFrame
) -> pd.DataFrame:
    """Geocode Comunidad de Madrid mobile points, using and updating the cache.

    Collects all unique addresses across both 'lugar' and 'direccion' fields,
    geocodes only addresses missing from the cache (one API call each), then
    picks the better-scored coordinate for each row.
    """
    all_addresses: set[str] = set()
    for field in ["lugar", "direccion"]:
        all_addresses.update(
            df.apply(
                lambda row, field=field: build_full_address(
                    row[field], row.localidad, REGION_MADRID
                ),
                axis=1,
            ).unique()
        )

    geocoding_cache = refresh_geocoding_cache(all_addresses, geocoding_cache)

    def best_coords(row):
        addr_lugar = build_full_address(row["lugar"], row.localidad, REGION_MADRID)
        addr_dir = build_full_address(row["direccion"], row.localidad, REGION_MADRID)
        score_lugar = geocoding_cache.loc[
            geocoding_cache.address == addr_lugar, "score"
        ].iloc[0]
        score_dir = geocoding_cache.loc[
            geocoding_cache.address == addr_dir, "score"
        ].iloc[0]
        # Fall back to lugar when scores are equal or either is missing
        if pd.notna(score_dir) and pd.notna(score_lugar) and score_dir > score_lugar:
            row_data = geocoding_cache.loc[geocoding_cache.address == addr_dir].iloc[0]
        else:
            row_data = geocoding_cache.loc[geocoding_cache.address == addr_lugar].iloc[
                0
            ]
        return row_data["longitude"], row_data["latitude"]

    df[["longitude", "latitude"]] = pd.DataFrame(
        df.apply(best_coords, axis=1).tolist(),
        index=df.index,
        columns=["longitude", "latitude"],
    )
    return df


def geocode_points(
    df: pd.DataFrame, geocoding_cache: pd.DataFrame, address_columns: str | list[str]
) -> pd.DataFrame:
    """Geocode points from one or more pre-built full-address columns.

    With a single column this is a plain cache-backed geocode. With several,
    every candidate is geocoded and the best-scoring one is kept per row —
    e.g. a POI-name-based address alongside a raw street-address one: the
    POI-name candidate tends to resolve precisely (ROOFTOP/point_of_interest)
    exactly where the street text is too messy for Google to parse a house
    number out of, but a row without a usable POI name (NaN in that column)
    just falls back to the street-address candidate. Ties fall back to the
    first listed column, mirroring geocode_mobile_points' lugar-first rule.
    """
    if isinstance(address_columns, str):
        address_columns = [address_columns]

    all_addresses = {
        address for column in address_columns for address in df[column].dropna()
    }
    geocoding_cache = refresh_geocoding_cache(all_addresses, geocoding_cache)
    scored = geocoding_cache.set_index("address")

    def best_candidate(row) -> pd.Series:
        best_column, best_score = address_columns[0], -1
        for column in address_columns:
            address = row[column]
            if pd.isna(address) or address not in scored.index:
                continue
            score = scored.loc[address, "score"]
            if pd.notna(score) and score > best_score:
                best_column, best_score = column, score

        address = row[best_column]
        if pd.isna(address) or address not in scored.index:
            return pd.Series({"longitude": None, "latitude": None})
        return scored.loc[address, ["longitude", "latitude"]]

    coords = df.apply(best_candidate, axis=1)
    return pd.concat([df, coords], axis=1)


def load_geocoding_cache() -> pd.DataFrame:
    """Load the shared geocoding cache, or an empty one on first run."""
    try:
        return from_db("geocoding_cache")
    except pd.errors.DatabaseError:  # table may not exist yet on first run
        return pd.DataFrame(
            columns=[
                "address",
                "longitude",
                "latitude",
                "location_type",
                "score",
                "place_name",
                "place_address",
            ]
        )


def scrape_fixed_points_clm() -> pd.DataFrame:
    """Scrape Castilla-La Mancha's fixed donation points.

    Unlike Castilla y León, there's no Google Maps link on the source page at
    all, so every point goes through the regular geocoding cache (see
    geocode_points) rather than a free coordinate shortcut.
    """
    df = castilla_la_mancha.scrape_fixed_points()
    df.columns = df.columns.map(format_column)
    df["full_address"] = df.apply(
        lambda row: build_full_address(
            row["direccion"] or row["localidad"], row["localidad"], REGION_CLM
        ),
        axis=1,
    )
    df = geocode_points(df, load_geocoding_cache(), "full_address")
    opening_hours_lookup = load_opening_hours_fijos()
    df["opening_hours"] = df.apply(
        opening_hours_for_fixed_point, lookup=opening_hours_lookup, axis=1
    )
    df["region"] = REGION_CLM
    return df


def scrape_fixed_points_aragon() -> pd.DataFrame:
    """Scrape and geocode Aragón's fixed donation points.

    The scraped address text carries extra notes (e.g. the Banco's "esquina
    Duquesa Villahermosa. Parking gratuito"), so the center's own name plus
    its city is geocoded alongside it and the better-scoring one is kept
    (see geocode_points) — every one of these is a well-known hospital/POI.
    Only the Banco itself takes plasma (by appointment); that flag comes from
    the crawler.
    """
    df = aragon.scrape_fixed_points()
    df["address_direccion"] = df.apply(
        lambda row: build_full_address(
            row["direccion"], row["localidad"], REGION_ARAGON
        ),
        axis=1,
    )
    df["address_name"] = df.apply(
        lambda row: build_full_address(row["name"], row["localidad"], REGION_ARAGON),
        axis=1,
    )
    df = geocode_points(
        df, load_geocoding_cache(), ["address_name", "address_direccion"]
    )
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    opening_hours_lookup = load_opening_hours_fijos()
    df["opening_hours"] = df.apply(
        opening_hours_for_fixed_point, lookup=opening_hours_lookup, axis=1
    )
    df["region"] = REGION_ARAGON
    return df.drop(columns=["address_direccion", "address_name"])


def scrape_fixed_points_valencia() -> pd.DataFrame:
    """Scrape and geocode Comunidad Valenciana's fixed donation points.

    Their hours aren't a weekly pattern but a day-by-day schedule published
    alongside the mobile stops (see comunidad_valenciana.py), so
    opening_hours is built from that schedule each run (one dated rule per
    day, see parse_scheduled_hours) rather than read from the hand-built
    opening_hours_fijos.json lookup. Geocoded from the street address plus a
    Places search for the center's name (see geocode_points).
    """
    df = comunidad_valenciana.scrape_fixed_points()
    df["opening_hours"] = df["schedule"].apply(parse_scheduled_hours)
    df["address_direccion"] = df.apply(
        lambda row: build_full_address(
            row["direccion"], row["localidad"], REGION_VALENCIA
        ),
        axis=1,
    )
    df["place_query"] = df["name"] + ", " + df["localidad"]
    geocoding_cache = refresh_places_cache(
        set(df["place_query"]), load_geocoding_cache(), VALENCIA_PLACES_BOUNDS
    )
    df["place_name"] = df.apply(
        lambda row: place_candidate(
            row["place_query"],
            row["localidad"],
            geocoding_cache,
            VALENCIA_PLACES_BOUNDS,
        ),
        axis=1,
    )
    df = geocode_points(df, geocoding_cache, ["address_direccion", "place_name"])
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df["region"] = REGION_VALENCIA
    return df.drop(
        columns=["schedule", "address_direccion", "place_query", "place_name"]
    )


def scrape_fixed_points_cataluna() -> pd.DataFrame:
    """Scrape and geocode Cataluña's fixed donation points (hospitals).

    Geocoded from the street address plus a Places search for the
    hospital's name (see geocode_points). Their "Cómo llegar" links do carry
    coordinates, but the site truncates some of them mid-number, so they
    aren't relied on. Opening hours come from the hand-built
    opening_hours_fijos.json lookup, keyed by name.
    """
    df = cataluna.scrape_fixed_points()
    df["address_direccion"] = df.apply(
        lambda row: build_full_address(
            row["direccion"], row["localidad"], REGION_CATALUNA
        ),
        axis=1,
    )
    df["place_query"] = df["name"] + ", " + df["localidad"]
    geocoding_cache = refresh_places_cache(
        set(df["place_query"]), load_geocoding_cache(), CATALUNA_PLACES_BOUNDS
    )
    df["place_name"] = df.apply(
        lambda row: place_candidate(
            row["place_query"],
            row["localidad"],
            geocoding_cache,
            CATALUNA_PLACES_BOUNDS,
        ),
        axis=1,
    )
    df = geocode_points(df, geocoding_cache, ["address_direccion", "place_name"])
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    opening_hours_lookup = load_opening_hours_fijos()
    df["opening_hours"] = df.apply(
        opening_hours_for_fixed_point, lookup=opening_hours_lookup, axis=1
    )
    df["region"] = REGION_CATALUNA
    return df.drop(columns=["address_direccion", "place_query", "place_name"])


def scrape_fixed_points_galicia() -> pd.DataFrame:
    """Scrape Galicia's fixed donation points ("Locais de doazón").

    Most carry GPS coordinates on the page, used as-is; the rest are
    geocoded from their first address line. Opening hours come from the
    hand-built opening_hours_fijos.json lookup, keyed by name.
    """
    df = galicia.scrape_fixed_points()
    missing = df["latitude"].isna()
    df["address_venue"] = df.apply(
        lambda row: build_full_address(
            row["venue"].split(". ")[0], row["localidad"], REGION_GALICIA
        ),
        axis=1,
    ).where(missing)
    page_coords = df[["longitude", "latitude"]]
    df = geocode_points(
        df.drop(columns=["longitude", "latitude"]),
        load_geocoding_cache(),
        "address_venue",
    )
    df[["longitude", "latitude"]] = page_coords.fillna(df[["longitude", "latitude"]])
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    opening_hours_lookup = load_opening_hours_fijos()
    df["opening_hours"] = df.apply(
        opening_hours_for_fixed_point, lookup=opening_hours_lookup, axis=1
    )
    df["region"] = REGION_GALICIA
    return df.drop(columns=["venue", "address_venue"])


def scrape_fixed_points_pais_vasco() -> pd.DataFrame:
    """Scrape País Vasco's fixed donation points (the permanent centres).

    Like Comunidad Valenciana's, their hours are a day-by-day schedule from
    the same listings as the mobile stops (see pais_vasco.py), so
    opening_hours is built from it each run (see parse_scheduled_hours).
    Every listing links to the spot's coordinates, so nothing is geocoded.
    Plasma-only ones get sangre: False; the rest leave both flags unset (the
    source doesn't say which centres take plasma, only to book it by phone).
    """
    df = pais_vasco.scrape_fixed_points()
    df["opening_hours"] = df["schedule"].apply(parse_scheduled_hours)
    df["plasma"] = df["plasma_only"].where(df["plasma_only"])
    df["sangre"] = (~df["plasma_only"]).where(df["plasma_only"])
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df["region"] = REGION_PAIS_VASCO
    return df.drop(columns=["schedule", "plasma_only"])


def scrape_fixed_points_cantabria() -> pd.DataFrame:
    """Scrape Cantabria's fixed donation spot (the Valdecilla hospital's Banco de Sangre).

    It's the only fixed point the region's source lists. Its Google Maps
    short link carries the coordinates (see cantabria.py), so nothing is
    geocoded; the hours are a hand-built opening_hours_fijos.json lookup
    keyed by name.
    """
    df = cantabria.scrape_fixed_points()
    opening_hours_lookup = load_opening_hours_fijos()
    df["opening_hours"] = df.apply(
        opening_hours_for_fixed_point, lookup=opening_hours_lookup, axis=1
    )
    df["region"] = REGION_CANTABRIA
    return df


def process_fixed_points():
    """Scrape, enrich, and upload fixed donation points for every region."""
    df = pd.concat(
        [
            scrape_fixed_points_madrid(),
            scrape_fixed_points_cyl(),
            scrape_fixed_points_clm(),
            scrape_fixed_points_aragon(),
            scrape_fixed_points_valencia(),
            scrape_fixed_points_cataluna(),
            scrape_fixed_points_galicia(),
            scrape_fixed_points_pais_vasco(),
            scrape_fixed_points_cantabria(),
        ],
        ignore_index=True,
    )
    to_db(gdf_from_df(df), "puntos_fijos")
    log.info("Fixed points: uploaded %d rows", len(df))


def scrape_mobile_points_madrid() -> pd.DataFrame:
    """Scrape and geocode Comunidad de Madrid's mobile donation points."""
    df = madrid.scrape_mobile_points()
    df.columns = df.columns.map(format_column)

    # Strip location-type prefixes from the address field
    for prefix in ["Equipo móvil en ", "E Móvil en ", "Equipo Móvil detrás "]:
        df["direccion"] = df["direccion"].str.replace(prefix, "", regex=False)

    # Hardcoded fix for a recurring typo on the source site: "13.a45" instead
    # of "13:45", which otherwise fails opening_hours parsing.
    df["horario"] = df["horario"].str.replace("13.a45", "13:45", regex=False)

    df = geocode_mobile_points(df, load_geocoding_cache())

    df["name"] = "Equipo móvil en " + df["lugar"]
    df["opening_hours"] = df.apply(
        lambda row: parse_mobile_hours(row["fecha"], row["horario"]), axis=1
    )
    df["url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df["region"] = REGION_MADRID

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


def scrape_mobile_points_cyl() -> pd.DataFrame:
    """Scrape and geocode Castilla y León's mobile donation points.

    Unlike fixed points, mobile points only link to a Google Maps *search*
    (not a specific place), so there's no shortcut around geocoding here.

    The raw "direccion" text often runs the street address, locality, and
    province together with no punctuation (e.g. "El Cabildo, s/n Valladolid
    (VALLADOLID)"), which makes Google drop the house number and geocode the
    street's midpoint instead of the actual point. When "campana" names a
    recognizable place (a shop, a landmark) rather than a generic org/town
    name, geocoding that name plus the locality directly resolves the actual
    point instead — so both candidates are geocoded and the better-scoring
    one is kept (see geocode_points).
    """
    df = castilla_y_leon.scrape_mobile_points()
    if df.empty:
        # The source page can drop its mobile-points table entirely (see
        # castilla_y_leon.is_mobile_points_table) — upload the other regions
        # rather than failing the whole run.
        return pd.DataFrame(
            columns=[
                "name",
                "localidad",
                "direccion",
                "fecha",
                "horario",
                "opening_hours",
                "url",
                "region",
                "latitude",
                "longitude",
            ]
        )
    df.columns = df.columns.map(format_column)
    df["address_direccion"] = df["direccion"].apply(
        lambda direccion: build_full_address(direccion, REGION_CYL)
    )
    df["address_campana"] = df.apply(
        lambda row: (
            build_full_address(row["campana"], row["province"].title(), REGION_CYL)
            if pd.notna(row["campana"])
            else None
        ),
        axis=1,
    )

    df = geocode_points(
        df, load_geocoding_cache(), ["address_direccion", "address_campana"]
    )

    df["name"] = "Equipo móvil en " + df["campana"].fillna(df["ubicacion"])
    df["opening_hours"] = df.apply(
        lambda row: (
            parse_mobile_hours(row["fecha"], row["horario"])
            if pd.notna(row["fecha"])
            else None
        ),
        axis=1,
    )
    df["url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df["region"] = REGION_CYL
    df = df.rename(columns=CYL_LOCATION_COLUMN_ALIASES)
    df["localidad"] = df["localidad"].str.title()

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


def scrape_mobile_points_clm() -> pd.DataFrame:
    """Scrape and geocode Castilla-La Mancha's mobile donation points.

    There's no street address at all here — only a locality and a venue
    label ("Lugar de la Colecta", e.g. "Centro de Salud") — so that pair is
    the only geocoding candidate; no lugar-vs-direccion choice to make (see
    geocode_points with a single column).
    """
    df = castilla_la_mancha.scrape_mobile_points()
    df.columns = df.columns.map(format_column)
    df = df.rename(
        columns={"lugar_de_la_colecta": "lugar", "tipo_de_donacion": "tipo_donacion"}
    )
    df["fecha"] = df["dia"].apply(castilla_la_mancha.parse_clm_date)
    df["localidad"] = df["localidad"].apply(castilla_la_mancha.clean_locality)
    df["full_address"] = df.apply(
        lambda row: build_full_address(row["lugar"], row["localidad"], REGION_CLM),
        axis=1,
    )

    df = geocode_points(df, load_geocoding_cache(), "full_address")

    df["name"] = "Equipo móvil en " + df["lugar"] + ", " + df["localidad"]
    df["direccion"] = df["lugar"]
    df["opening_hours"] = df.apply(
        lambda row: (
            parse_mobile_hours(row["fecha"], row["horario"])
            if pd.notna(row["fecha"])
            else None
        ),
        axis=1,
    )
    df["url"] = df["province"].apply(castilla_la_mancha.province_url)
    # "Tipo de donación" is either SANGRE or PLASMA — a "(SÓLO PLASMA)" stop
    # genuinely doesn't take whole blood, unlike every other scraped point
    # (which always does), so sangre is set explicitly false there rather
    # than left absent (see the App.jsx sangre-filter comment for why that
    # distinction matters). Médula is never offered at a mobile point in any
    # region; set explicitly for schema consistency across regions.
    df["plasma"] = df["tipo_donacion"] == "PLASMA"
    df["sangre"] = df["tipo_donacion"] != "PLASMA"
    df["medula"] = False
    df["region"] = REGION_CLM

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


def apply_location_overrides(
    df: pd.DataFrame, overrides: pd.DataFrame, key_columns: list[str]
) -> pd.DataFrame:
    """Overwrite coordinates for points no automatic candidate gets right.

    Each override's "match" is compared against every column in
    key_columns, in order, so a later column's match wins over an earlier
    one's — e.g. Aragón matches its title's town/organization part ("who")
    then the full title, so a recurring organization's stop stays covered
    when its room changes but a specific title can still be pinned on its
    own. Overrides are hand-picked (see utils/*_mobile_locations.json) and
    win over every geocoded candidate.
    """
    if overrides.empty:
        return df
    coords = overrides.set_index("match")[["longitude", "latitude"]]
    for key_column in key_columns:
        matched = df[key_column].isin(coords.index)
        df.loc[matched, ["longitude", "latitude"]] = coords.loc[
            df.loc[matched, key_column]
        ].to_numpy()
    return df


def scrape_mobile_points_aragon() -> pd.DataFrame:
    """Scrape and geocode Aragón's mobile donation points.

    The source carries no address or locality at all — only an event title
    like "Sariñena, en el Centro de Salud" or "Ibercaja, en el Hall del Salón
    Aragón" (a town or an organization, then the venue inside it). Three
    candidates are tried and the best-scoring one kept (see geocode_points):
    the raw title and "venue + town/organization" through the Geocoding API,
    and the raw title as a Places free-text search — which, like Google
    Maps' own search box, resolves most of these venue descriptions where
    geocoding only manages a town's or the whole region's center. The
    Places result only counts when it passes place_candidate's checks, and
    the few points none of this gets right are pinned by hand (see
    apply_location_overrides).
    "localidad" is left unset, since the part before ", en" is as often an
    organization as a town.
    """
    df = aragon.scrape_mobile_points()
    df["address_title"] = df["title"].apply(
        lambda title: build_full_address(title, REGION_ARAGON)
    )
    df["address_venue"] = df.apply(
        lambda row: (
            build_full_address(f"{row['venue']} {row['who']}", REGION_ARAGON)
            if pd.notna(row["venue"])
            else None
        ),
        axis=1,
    )

    geocoding_cache = refresh_places_cache(
        set(df["title"]), load_geocoding_cache(), ARAGON_PLACES_BOUNDS
    )
    df["place_title"] = df.apply(
        lambda row: place_candidate(
            row["title"], row["who"], geocoding_cache, ARAGON_PLACES_BOUNDS
        ),
        axis=1,
    )

    df = geocode_points(
        df, geocoding_cache, ["address_title", "address_venue", "place_title"]
    )
    df = apply_location_overrides(
        df, pd.read_json("utils/aragon_mobile_locations.json"), ["who", "title"]
    )

    df["name"] = "Equipo móvil en " + df["title"]
    df["localidad"] = None
    df["direccion"] = None
    df["opening_hours"] = df.apply(
        lambda row: parse_mobile_hours(row["fecha"], row["horario"]), axis=1
    )
    df["region"] = REGION_ARAGON

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


def scrape_mobile_points_valencia() -> pd.DataFrame:
    """Scrape and geocode Comunidad Valenciana's mobile donation points.

    Each stop has a town ("Población") and a venue + street address
    ("Ubicación"), split apart by the crawler. Two candidates are tried and
    the best-scoring one kept (see geocode_points): the street address via
    the Geocoding API, and the venue name via a Places search (checked to be
    in the region and in the right town, see place_candidate).

    Stops restricted to a group (e.g. "(SOLO EMPLEADOS)") are kept, with
    the note appended to the name so it's always visible. Plasma-only stops
    ("SOLO DONACIÓN DE PLASMA CON CITA PREVIA") get sangre: False, like
    Castilla-La Mancha's.
    """
    df = comunidad_valenciana.scrape_mobile_points()
    df["localidad"] = df["poblacion"].str.title()
    df["address_direccion"] = df.apply(
        lambda row: build_full_address(
            row["direccion"] if pd.notna(row["direccion"]) else row["venue"],
            row["localidad"],
            REGION_VALENCIA,
        ),
        axis=1,
    )
    df["place_query"] = df["venue"] + ", " + df["localidad"]
    geocoding_cache = refresh_places_cache(
        set(df["place_query"]), load_geocoding_cache(), VALENCIA_PLACES_BOUNDS
    )
    df["place_venue"] = df.apply(
        lambda row: place_candidate(
            row["place_query"],
            row["poblacion"],
            geocoding_cache,
            VALENCIA_PLACES_BOUNDS,
        ),
        axis=1,
    )
    df = geocode_points(df, geocoding_cache, ["address_direccion", "place_venue"])

    df["name"] = "Equipo móvil en " + df["venue"]
    restricted = df["restriction"].notna()
    df.loc[restricted, "name"] += " " + df.loc[restricted, "restriction"]
    df["opening_hours"] = df.apply(
        lambda row: parse_mobile_hours(row["fecha"], row["horario"]), axis=1
    )
    df["url"] = df["province"].apply(comunidad_valenciana.province_url)
    df["plasma"] = df["plasma_only"]
    df["sangre"] = ~df["plasma_only"]
    df["medula"] = False
    df["region"] = REGION_VALENCIA

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


def scrape_mobile_points_cataluna() -> pd.DataFrame:
    """Scrape and geocode Cataluña's mobile donation points.

    Each stop has a town, a venue and a street address. Two candidates are
    tried and the best-scoring one kept (see geocode_points): the street
    address via the Geocoding API, and the venue name via a Places search
    (checked to be in the region and town, see place_candidate) — except
    for donation-bus stops ("Unidad móvil"), whose street address is the
    actual spot and whose venue text isn't a place Places could find.

    The few stops none of this gets right — mostly villages inside a
    multi-village municipality, where Google's address names the village
    rather than the "Población" (e.g. Ordal, in Subirats) — are pinned by
    hand (see apply_location_overrides).

    Donation types come straight from each stop's booking buttons: most
    take blood, many also plasma, and a few are plasma-only (sangre:
    False). Plasma-only stops have no published hours, so their
    opening_hours stays None (see cataluna.scrape_mobile_points).
    """
    df = cataluna.scrape_mobile_points()
    df["address_direccion"] = df.apply(
        lambda row: build_full_address(
            row["direccion"] if pd.notna(row["direccion"]) else row["venue"],
            row["localidad"],
            REGION_CATALUNA,
        ),
        axis=1,
    )
    searchable = ~df["venue"].apply(cataluna.is_mobile_unit)
    df["place_query"] = (df["venue"] + ", " + df["localidad"]).where(searchable)
    geocoding_cache = refresh_places_cache(
        set(df["place_query"].dropna()),
        load_geocoding_cache(),
        CATALUNA_PLACES_BOUNDS,
    )
    df["place_venue"] = df.apply(
        lambda row: (
            place_candidate(
                row["place_query"],
                row["localidad"],
                geocoding_cache,
                CATALUNA_PLACES_BOUNDS,
            )
            if pd.notna(row["place_query"])
            else None
        ),
        axis=1,
    )
    df = geocode_points(df, geocoding_cache, ["address_direccion", "place_venue"])
    # Pinned by "venue, town" for a fixed venue, or "street, town" where the
    # street is what identifies the stop (a donation bus's square, or a
    # venue that isn't on Google Maps at all).
    df["venue_key"] = df["venue"] + ", " + df["localidad"]
    df["address_key"] = df["direccion"] + ", " + df["localidad"]
    df = apply_location_overrides(
        df,
        pd.read_json("utils/cataluna_mobile_locations.json"),
        ["venue_key", "address_key"],
    )

    df["name"] = "Equipo móvil en " + df["venue"]
    df["opening_hours"] = df.apply(
        lambda row: (
            parse_mobile_hours(row["fecha"], row["horario"])
            if pd.notna(row["horario"])
            else None
        ),
        axis=1,
    )
    df["medula"] = False
    df["region"] = REGION_CATALUNA

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


def clean_galicia_lugar(lugar: str) -> str:
    """Strip a Galician "Lugar de colecta"'s decorations (GALICIA_LUGAR_NOISE_RE)."""
    return GALICIA_LUGAR_NOISE_RE.sub("", lugar).strip()


def title_galicia_name(text: str) -> str:
    """Title-case an all-caps Galician name, keeping its particles lowercase."""
    return GALICIA_NAME_PARTICLE_RE.sub(
        lambda match: match.group().lower(), text.title()
    )


def scrape_mobile_points_galicia() -> pd.DataFrame:
    """Scrape and geocode Galicia's mobile donation points.

    Every stop is a donation bus parked at a described spot ("UNIDADE MÓBIL
    DIANTE DA CASA DA XUVENTUDE") in a collection place ("Lugar de colecta":
    a town, parish, neighbourhood or campus) within a concello. The spot
    description (minus the bus lead-in) plus place and concello is searched
    with Places, and the result used whenever it's in the region and in the
    place or concello (see place_candidate); the Geocoding API's result for
    the same text is only the fallback. Unlike other regions, the two aren't
    compared by score: these descriptions ("CENTRO DE SAUDE, Cambados") are
    no postal address, and geocoding them often returns a ROOFTOP match at
    some other building. Spots neither gets right are pinned by hand (see
    apply_location_overrides), matched by "description, concello".

    Stops marked "Provisional" are kept, with the note in the name.
    """
    df = galicia.scrape_mobile_points()
    df["lugar_clean"] = df["lugar"].apply(clean_galicia_lugar)
    df["place_query"] = df.apply(
        lambda row: ", ".join(
            dict.fromkeys(
                [row["place_text"], row["lugar_clean"].title(), row["concello"]]
            )
        ),
        axis=1,
    )
    df["address_place"] = df.apply(
        lambda row: build_full_address(row["place_query"], REGION_GALICIA), axis=1
    )
    geocoding_cache = refresh_places_cache(
        set(df["place_query"]), load_geocoding_cache(), GALICIA_PLACES_BOUNDS
    )
    df["place_venue"] = df.apply(
        lambda row: place_candidate(
            row["place_query"],
            f"{row['lugar_clean']}/{row['concello']}",
            geocoding_cache,
            GALICIA_PLACES_BOUNDS,
        ),
        axis=1,
    )
    df["best_query"] = df["place_venue"].fillna(df["address_place"])
    df = geocode_points(df, geocoding_cache, "best_query")
    df["location_key"] = df["place_text"] + ", " + df["concello"]
    df = apply_location_overrides(
        df, pd.read_json("utils/galicia_mobile_locations.json"), ["location_key"]
    )

    df["name"] = "Equipo móvil en " + df["lugar"].apply(title_galicia_name)
    df.loc[df["provisional"], "name"] += " (provisional)"
    df["localidad"] = df["concello"]
    df["opening_hours"] = df.apply(
        lambda row: parse_mobile_hours(row["fecha"], row["horario"]), axis=1
    )
    df["medula"] = False
    df["region"] = REGION_GALICIA

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


def scrape_mobile_points_pais_vasco() -> pd.DataFrame:
    """Scrape País Vasco's mobile donation points.

    Every stop links to its exact coordinates on Google Maps, so nothing is
    geocoded. Plasma-only stops ("Solo Plasma/Cita") get sangre: False, like
    Castilla-La Mancha's; company/school-only ones ("(colecta privada)")
    keep that note in their name, as the source shows it.
    """
    df = pais_vasco.scrape_mobile_points()
    df["name"] = "Equipo móvil en " + df["lugar"]
    df["opening_hours"] = df.apply(
        lambda row: parse_mobile_hours(row["fecha"], row["horario"]), axis=1
    )
    df["plasma"] = df["plasma_only"]
    df["sangre"] = ~df["plasma_only"]
    df["medula"] = False
    df["region"] = REGION_PAIS_VASCO

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


def process_mobile_points():
    """Scrape, geocode, and upload mobile donation points for every region."""
    df = pd.concat(
        [
            scrape_mobile_points_madrid(),
            scrape_mobile_points_cyl(),
            scrape_mobile_points_clm(),
            scrape_mobile_points_aragon(),
            scrape_mobile_points_valencia(),
            scrape_mobile_points_cataluna(),
            scrape_mobile_points_galicia(),
            scrape_mobile_points_pais_vasco(),
        ],
        ignore_index=True,
    )
    to_db(gdf_from_df(df), "puntos_moviles")
    log.info("Mobile points: uploaded %d rows", len(df))


def scrape_blood_levels_madrid() -> pd.DataFrame:
    """Scrape Comunidad de Madrid's blood-reserve levels ("semáforo de necesidades")."""
    df = madrid.scrape_blood_levels()
    df["region"] = REGION_MADRID
    df["source"] = "donarsangre.org"
    return df


def scrape_blood_levels_cyl() -> pd.DataFrame:
    """Scrape Castilla y León's blood-reserve levels ("niveles de sangre actuales")."""
    df = castilla_y_leon.scrape_blood_levels()
    df["region"] = REGION_CYL
    df["source"] = "centrodehemoterapiacyl.es"
    return df


def scrape_blood_levels_galicia() -> pd.DataFrame:
    """Scrape Galicia's blood-reserve levels ("Semáforo", read off an image)."""
    df = galicia.scrape_blood_levels()
    df["region"] = REGION_GALICIA
    df["source"] = "ados.sergas.gal"
    return df


def scrape_blood_levels_pais_vasco() -> pd.DataFrame:
    """Scrape País Vasco's blood-reserve levels ("niveles de sangre actuales")."""
    df = pais_vasco.scrape_blood_levels()
    df["region"] = REGION_PAIS_VASCO
    df["source"] = "donantesdesangre.eus"
    return df


def process_blood_levels():
    """Scrape and append blood-reserve levels for every region that has one.

    Castilla-La Mancha, Aragón, Comunidad Valenciana, Cataluña and Cantabria
    have no such source at all (no scrape_blood_levels_clm/_aragon/_valencia/
    _cataluna/_cantabria exists), so they're simply left out
    here — the frontend shows a "no data for this region" placeholder
    instead of blank/stale badges for them.

    Unlike the other tables, blood_levels is append-only to keep a history of
    reserve levels over time. Create the table manually first with
    sql/create_blood_levels_table.sql.
    """
    df = pd.concat(
        [
            scrape_blood_levels_madrid(),
            scrape_blood_levels_cyl(),
            scrape_blood_levels_galicia(),
            scrape_blood_levels_pais_vasco(),
        ],
        ignore_index=True,
    )
    df["updated_at"] = pd.Timestamp.now(tz="UTC")

    to_db(df, "blood_levels", if_exists="append")
    log.info("Blood levels: appended %d rows", len(df))


def run_etl():
    """Run the full ETL pipeline: scrape, geocode, and upload to the database."""
    log.info("Starting ETL")
    process_fixed_points()
    log.info("Fixed points done")
    process_mobile_points()
    log.info("Mobile points done")
    process_blood_levels()
    log.info("Blood levels done")
    log.info("ETL complete")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    run_etl()
