"""Utility functions to interact with a PostGIS enabled Postgres database"""

import os

import geopandas as gpd
import pandas as pd

from dotenv import load_dotenv
from googlemaps import Client
from sqlalchemy import create_engine
from unidecode import unidecode

load_dotenv()


def get_pg_engine():
    connection_string = 'postgresql://{user}:{password}@{host}:{port}/{db}'.format(
        user=os.environ['PG_USER'],
        password=os.environ['PG_PASSWORD'],
        host=os.environ['PG_HOST'],
        port=os.environ['PG_PORT'],
        db=os.environ['PG_DATABASE']
    )
    
    return create_engine(connection_string)


PG_ENGINE = get_pg_engine()


def run_query(sql_query):
    conn = PG_ENGINE.connect()
    conn.execute(sql_query)
    conn.close()


def to_db(df, table_name):
    if isinstance(df, gpd.GeoDataFrame):
        df.to_postgis(table_name, PG_ENGINE, if_exists='replace', index=False)
    elif isinstance(df, pd.DataFrame):
        df.to_sql(table_name, PG_ENGINE, if_exists='replace', index=False)
    else:
        raise ValueError(f'"df" must be a DataFrame or GeoDataFrame, received "{type(df)}" instead')


def from_db(table_or_query):
    return pd.read_sql(table_or_query, PG_ENGINE)


def format_column(column_name):
    """Format a column name to be a valid PG identifier"""
    chars_to_remove = "¿?(),."
    chars_to_replace = {"/": "_", " ": "_", "%": "pct"}
    for char in chars_to_remove:
        column_name = column_name.replace(char, "")
    for original_char, new_char in chars_to_replace.items():
        column_name = column_name.replace(original_char, new_char)
        
    # Multiple underscores into a single one
    column_name = '_'.join([part for part in column_name.split('_') if part != ''])

    column_name = unidecode(column_name.lower())
    return column_name


def gdf_from_df(df):
    """Construct a GeoDataFrame from a Pandas' DataFrame
    
    Assume the original DataFrame contains point information
    in fields `latitude` and `longitude`"""
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['longitude'], df['latitude']))
    gdf = gdf.drop(columns=['latitude', 'longitude'])
    gdf = gdf.set_crs(epsg=4326)
    
    return gdf
