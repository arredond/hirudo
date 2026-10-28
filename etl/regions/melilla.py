"""Melilla: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/melilla.py.
"""

import pandas as pd
from utils import geocode, points
from utils.crawl import crawl, melilla

REGION = "Melilla"


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape and geocode Melilla's fixed donation spot (the Centro de Transfusión).

    The page gives only a street address, no map link, so the spot goes
    through the geocoding cache (see geocode.geocode_points). Hours come from the
    hand-built opening_hours_fijos.json lookup, keyed by name.
    """
    df = melilla.scrape_fixed_points()
    df["full_address"] = df.apply(
        lambda row: geocode.build_full_address(row["direccion"], row["localidad"]),
        axis=1,
    )
    df = geocode.geocode_points(df, geocode.load_geocoding_cache(), "full_address")
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df.drop(columns=["full_address"])
