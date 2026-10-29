"""Blood donation points ETL — runs as a single Cloud Run job

To run locally, make sure you have a valid .env file. Then:

from dotenv import load_dotenv
load_dotenv()

import main
main.run_etl()

Each region's scraping, enrichment and geocoding lives in regions/<region>.py;
this module just runs every region and uploads the combined tables.
"""

import logging

import pandas as pd
from regions import (
    andalucia,
    aragon,
    asturias,
    balears,
    canarias,
    cantabria,
    castilla_la_mancha,
    castilla_y_leon,
    cataluna,
    comunidad_valenciana,
    extremadura,
    galicia,
    la_rioja,
    madrid,
    melilla,
    murcia,
    navarra,
    pais_vasco,
)
from utils import db, points

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# Every region the ETL covers. Each module has a REGION name and
# scrape_fixed_points(); scrape_mobile_points() and scrape_blood_levels() only
# where its source publishes them. Every output table carries a region column
# (Comunidad Autónoma), stamped by each region's own scrape_* functions, so a
# table can hold rows from several regions at once (the app filters by it).
# The geocoding_cache is shared across all regions and keyed by full address
# strings that already name the region, so it is left unstamped.
REGIONS = [
    madrid,
    castilla_y_leon,
    castilla_la_mancha,
    aragon,
    comunidad_valenciana,
    cataluna,
    galicia,
    pais_vasco,
    cantabria,
    navarra,
    la_rioja,
    andalucia,
    asturias,
    melilla,
    balears,
    canarias,
    murcia,
    extremadura,
]


def process_fixed_points():
    """Scrape, enrich, and upload fixed donation points for every region."""
    df = pd.concat(
        [region.scrape_fixed_points() for region in REGIONS], ignore_index=True
    )
    df = points.flag_appointments(df, points.load_cita_previa_fijos())
    df.loc[df["name"].isin(points.load_plasma_fijos()), "plasma"] = True
    db.to_db(db.gdf_from_df(df), "puntos_fijos")
    log.info("Fixed points: uploaded %d rows", len(df))


def process_mobile_points():
    """Scrape, geocode, and upload mobile donation points for every region."""
    df = pd.concat(
        [
            region.scrape_mobile_points()
            for region in REGIONS
            if hasattr(region, "scrape_mobile_points")
        ],
        ignore_index=True,
    )
    df = points.flag_appointments(df)
    db.to_db(db.gdf_from_df(df), "puntos_moviles")
    log.info("Mobile points: uploaded %d rows", len(df))


def process_blood_levels():
    """Scrape and append blood-reserve levels for every region that has one.

    Regions whose source publishes no levels have no scrape_blood_levels()
    and are simply left out here — the frontend shows a "no data for this
    region" placeholder instead of blank/stale badges for them.

    Unlike the other tables, blood_levels is append-only to keep a history of
    reserve levels over time. Create the table manually first with
    sql/create_blood_levels_table.sql.
    """
    df = pd.concat(
        [
            region.scrape_blood_levels()
            for region in REGIONS
            if hasattr(region, "scrape_blood_levels")
        ],
        ignore_index=True,
    )
    df["updated_at"] = pd.Timestamp.now(tz="UTC")

    db.to_db(df, "blood_levels", if_exists="append")
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
