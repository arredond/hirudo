"""Cantabria: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/cantabria.py.
"""

import pandas as pd
from utils import points
from utils.crawl import cantabria

REGION = "Cantabria"


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape Cantabria's fixed donation spot (the Valdecilla hospital's Banco de Sangre).

    It's the only fixed point the region's source lists. Its Google Maps
    short link carries the coordinates (see cantabria.py), so nothing is
    geocoded; the hours are a hand-built opening_hours_fijos.json lookup
    keyed by name.
    """
    df = cantabria.scrape_fixed_points()
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df
