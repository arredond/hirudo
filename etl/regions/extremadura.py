"""Extremadura: its fixed donation points for the ETL, entered by hand.

The Banco de Sangre's site (saludextremadura.ses.es/bancodesangre/) is a
client-rendered SPA with no data endpoint found yet (see
docs/ccaa-sources.md), so there is nothing to scrape. Until it can be, the
two main fixed points live in utils/extremadura_fijos.json with their
coordinates, so there is no crawl module and nothing is geocoded.
"""

import pandas as pd
from utils import points
from utils.crawl import crawl

REGION = "Extremadura"


def load_fixed_points() -> pd.DataFrame:
    """Load the hand-maintained fixed points (relative to etl/, the job's cwd)."""
    return pd.read_json("utils/extremadura_fijos.json", dtype={"telefono": str})


def scrape_fixed_points() -> pd.DataFrame:
    """Return Extremadura's hand-maintained fixed donation points.

    Hours come from the hand-built opening_hours_fijos.json lookup, keyed by
    name, like every other region's fixed points.
    """
    df = load_fixed_points()
    df["gmaps_url"] = df.apply(crawl.gmaps_url_from_coords, axis=1)
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df
