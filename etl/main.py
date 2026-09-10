"""Blood donation points ETL — runs as a single Cloud Run job

To run locally, make sure you have a valid .env file. Then:

from dotenv import load_dotenv
load_dotenv()

import main
main.run_etl()
"""

import logging

import pandas as pd
from utils.crawl import (
    gmaps_url_from_coords,
    scrape_blood_levels,
    scrape_fixed_points,
    scrape_mobile_points,
)
from utils.db import format_column, from_db, gdf_from_df, to_db
from utils.geocode import build_full_address, geocode_address

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Every output table this ETL writes covers a single Comunidad Autónoma. Stamp
# the region on each row so future runs can add other regions without a schema
# change (the app filters by it). The geocoding_cache is keyed by full address
# strings that already name the region, so it is left unstamped.
REGION = "Comunidad de Madrid"


def process_fixed_points():
    """Scrape, enrich, and upload fixed donation points."""
    manual_points = pd.read_json("utils/puntos_fijos_no_hospitales.json")
    other_donations = pd.read_json("utils/puntos_fijos_otras_donaciones.json")

    df = scrape_fixed_points()
    df.columns = df.columns.map(format_column)
    df = pd.concat([manual_points, df], ignore_index=True)
    df["gmaps_url"] = df.apply(gmaps_url_from_coords, axis=1)

    other_donations.columns = other_donations.columns.map(format_column)
    df = pd.merge(df, other_donations, on="name", how="left")
    df["region"] = REGION

    to_db(gdf_from_df(df), "puntos_fijos")
    log.info("Fixed points: uploaded %d rows", len(df))


def geocode_mobile_points(
    df: pd.DataFrame, geocoding_cache: pd.DataFrame
) -> pd.DataFrame:
    """Geocode mobile points, using and updating the cache.

    Collects all unique addresses across both 'lugar' and 'direccion' fields,
    geocodes only addresses missing from the cache (one API call each), then
    picks the better-scored coordinate for each row.
    """
    # Gather every unique address across both fields in one pass to avoid
    # redundant API calls when the same address appears in both columns.
    all_addresses: set[str] = set()
    for field in ["lugar", "direccion"]:
        all_addresses.update(
            df.apply(build_full_address, axis=1, address_field=field).unique()
        )

    cached_addresses = set(geocoding_cache["address"])
    new_rows = []
    for address in all_addresses - cached_addresses:
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

    def best_coords(row):
        addr_lugar = build_full_address(row, "lugar")
        addr_dir = build_full_address(row, "direccion")
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


def process_mobile_points():
    """Scrape, geocode, and upload mobile donation points."""
    df = scrape_mobile_points()
    df.columns = df.columns.map(format_column)

    # Strip location-type prefixes from the address field
    for prefix in ["Equipo móvil en ", "E Móvil en ", "Equipo Móvil detrás "]:
        df["direccion"] = df["direccion"].str.replace(prefix, "", regex=False)

    try:
        geocoding_cache = from_db("geocoding_cache")
    except pd.errors.DatabaseError:  # table may not exist yet on first run
        geocoding_cache = pd.DataFrame(
            columns=["address", "longitude", "latitude", "location_type", "score"]
        )

    df = geocode_mobile_points(df, geocoding_cache)

    output_cols = [
        "name",
        "localidad",
        "direccion",
        "fecha",
        "horario",
        "url",
        "region",
    ]
    df["name"] = "Equipo móvil en " + df["lugar"]
    df["url"] = df.apply(gmaps_url_from_coords, axis=1)
    df["region"] = REGION
    gdf = gdf_from_df(df)[output_cols + ["geometry"]]

    to_db(gdf, "puntos_moviles")
    log.info("Mobile points: uploaded %d rows", len(gdf))


def process_blood_levels():
    """Scrape and append blood-reserve levels (the "semáforo de necesidades").

    Unlike the other tables, blood_levels is append-only so we keep a history of
    reserve levels over time. Create the table manually first with
    sql/create_blood_levels_table.sql.
    """
    df = scrape_blood_levels()
    df["region"] = REGION
    df["source"] = "donarsangre.org"
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
