"""Castilla-La Mancha: scrape, enrich and geocode its donation points for the ETL.

Raw page parsing lives in utils/crawl/castilla_la_mancha.py.
"""

import pandas as pd
from utils import db, geocode, opening_hours, points
from utils.crawl import castilla_la_mancha

REGION = "Castilla-La Mancha"


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape Castilla-La Mancha's fixed donation points.

    Unlike Castilla y León, there's no Google Maps link on the source page at
    all, so every point goes through the regular geocoding cache (see
    geocode.geocode_points) rather than a free coordinate shortcut.
    """
    df = castilla_la_mancha.scrape_fixed_points()
    df.columns = df.columns.map(db.format_column)
    df["full_address"] = df.apply(
        lambda row: geocode.build_full_address(
            row["direccion"] or row["localidad"], row["localidad"], REGION
        ),
        axis=1,
    )
    df = geocode.geocode_points(df, geocode.load_geocoding_cache(), "full_address")
    df = points.add_opening_hours(df)
    df["region"] = REGION
    return df


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and geocode Castilla-La Mancha's mobile donation points.

    There's no street address at all here — only a locality and a venue
    label ("Lugar de la Colecta", e.g. "Centro de Salud") — so that pair is
    the only geocoding candidate; no lugar-vs-direccion choice to make (see
    geocode.geocode_points with a single column).
    """
    df = castilla_la_mancha.scrape_mobile_points()
    df.columns = df.columns.map(db.format_column)
    df = df.rename(
        columns={"lugar_de_la_colecta": "lugar", "tipo_de_donacion": "tipo_donacion"}
    )
    df["fecha"] = df["dia"].apply(castilla_la_mancha.parse_clm_date)
    df["localidad"] = df["localidad"].apply(castilla_la_mancha.clean_locality)
    df["full_address"] = df.apply(
        lambda row: geocode.build_full_address(row["lugar"], row["localidad"], REGION),
        axis=1,
    )

    df = geocode.geocode_points(df, geocode.load_geocoding_cache(), "full_address")

    df["name"] = "Equipo móvil en " + df["lugar"] + ", " + df["localidad"]
    df["direccion"] = df["lugar"]
    df["opening_hours"] = points.apply_rows(
        df,
        lambda row: (
            opening_hours.parse_mobile_hours(row["fecha"], row["horario"])
            if pd.notna(row["fecha"])
            else None
        ),
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
