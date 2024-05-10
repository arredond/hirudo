"""Utility functions to interact with a PostGIS enabled Postgres database"""

import os

import geopandas as gpd
import pandas as pd


from sqlalchemy import create_engine
from unidecode import unidecode


def get_pg_engine():
    """Connect to a PG database from env variables"""
    # pylint: disable=consider-using-f-string
    connection_string = "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.environ.get("PG_USER", "postgres.rniahokoaxvcljohlabg"),
        password=os.environ["PG_PASSWORD"],
        host=os.environ.get("PG_HOST", "aws-0-eu-west-1.pooler.supabase.com"),
        port=os.environ.get("PG_PORT", 5432),
        db=os.environ.get("PG_DATABASE", "postgres"),
    )

    return create_engine(connection_string)


def to_db(dataframe: gpd.GeoDataFrame | pd.DataFrame, table_name: str):
    """Upload a (Geo)DataFrame to a table in the database, replacing contents if necessary"""
    pg_engine = get_pg_engine()
    if isinstance(dataframe, gpd.GeoDataFrame):
        dataframe.to_postgis(table_name, pg_engine, if_exists="replace", index=False)
    elif isinstance(dataframe, pd.DataFrame):
        dataframe.to_sql(table_name, pg_engine, if_exists="replace", index=False)
    else:
        raise ValueError(
            f'dataframe must be a DataFrame or GeoDataFrame, received "{type(dataframe)}" instead'
        )


def from_db(table_or_query):
    """Read a table from the database into a Pandas DataFrame"""
    pg_engine = get_pg_engine()
    return pd.read_sql(table_or_query, pg_engine)


def format_column(column_name):
    """Format a column name to be a valid PG identifier"""
    chars_to_remove = "¿?(),.:"
    chars_to_replace = {"/": "_", " ": "_", "%": "pct"}
    for char in chars_to_remove:
        column_name = column_name.replace(char, "")
    for original_char, new_char in chars_to_replace.items():
        column_name = column_name.replace(original_char, new_char)

    # Multiple underscores into a single one
    column_name = "_".join([part for part in column_name.split("_") if part != ""])

    column_name = unidecode(column_name.lower())
    return column_name


def gdf_from_df(dataframe):
    """Construct a GeoDataFrame from a Pandas' DataFrame

    Assume the original DataFrame contains point information
    in fields `latitude` and `longitude`"""
    gdf = gpd.GeoDataFrame(
        dataframe,
        geometry=gpd.points_from_xy(dataframe["longitude"], dataframe["latitude"]),
    )
    gdf = gdf.drop(columns=["latitude", "longitude"])
    gdf = gdf.set_crs(epsg=4326)

    return gdf
