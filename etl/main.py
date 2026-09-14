"""Blood donation points ETL — runs as a single Cloud Run job

To run locally, make sure you have a valid .env file. Then:

from dotenv import load_dotenv
load_dotenv()

import main
main.run_etl()
"""

import json
import logging

import pandas as pd
from utils.crawl import castilla_la_mancha, castilla_y_leon, crawl, madrid
from utils.db import format_column, from_db, gdf_from_df, to_db
from utils.geocode import build_full_address, geocode_address
from utils.opening_hours import parse_mobile_hours

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
            columns=["address", "longitude", "latitude", "location_type", "score"]
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


def process_fixed_points():
    """Scrape, enrich, and upload fixed donation points for every region."""
    df = pd.concat(
        [
            scrape_fixed_points_madrid(),
            scrape_fixed_points_cyl(),
            scrape_fixed_points_clm(),
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


def process_mobile_points():
    """Scrape, geocode, and upload mobile donation points for every region."""
    df = pd.concat(
        [
            scrape_mobile_points_madrid(),
            scrape_mobile_points_cyl(),
            scrape_mobile_points_clm(),
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


def process_blood_levels():
    """Scrape and append blood-reserve levels for every region that has one.

    Castilla-La Mancha has no such source at all (no scrape_blood_levels_clm
    exists), so it's simply left out here — the frontend shows a "no data for
    this region" placeholder instead of blank/stale badges for it.

    Unlike the other tables, blood_levels is append-only to keep a history of
    reserve levels over time. Create the table manually first with
    sql/create_blood_levels_table.sql.
    """
    df = pd.concat(
        [scrape_blood_levels_madrid(), scrape_blood_levels_cyl()], ignore_index=True
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
