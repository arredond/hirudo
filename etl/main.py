"""Full process for running in a Google Cloud Function"""
import json

import pandas as pd

from utils.db import format_column, from_db, gdf_from_df, to_db
from utils.geocode import google_geocode_address, get_full_address
from utils.crawl import extraer_puntos_fijos, extraer_puntos_moviles, get_gmaps_url


def process_fixed_points():
    """Process fixed points"""
    with open("utils/puntos_fijos_no_hospitales.json", "rt", encoding="utf-8") as fp:
        puntos_fijos_no_hospitales = json.load(fp)
    df_fijos = extraer_puntos_fijos()
    df_fijos_keys = pd.DataFrame(
        {"original": df_fijos.columns, "db": df_fijos.columns.map(format_column)}
    )
    df_fijos.columns = df_fijos.columns.map(format_column)
    df_fijos = pd.concat(
        [pd.DataFrame(puntos_fijos_no_hospitales), df_fijos], ignore_index=True
    )
    df_fijos["gmaps_url"] = df_fijos.apply(get_gmaps_url, axis=1)
    gdf_fijos = gdf_from_df(df_fijos)
    to_db(gdf_fijos, "puntos_fijos")
    to_db(df_fijos_keys, "puntos_fijos_keys")


def process_mobile_points():
    """Must be geocoded"""
    df_moviles = extraer_puntos_moviles()
    df_moviles.columns = df_moviles.columns.map(format_column)
    for text in ["Equipo móvil en ", "E Móvil en ", "Equipo Móvil detrás "]:
        df_moviles["direccion"] = df_moviles["direccion"].map(
            lambda d: d.replace(text, "")
        )
    try:
        geocoding_cache = from_db("geocoding_cache")
    except Exception:  # pylint: disable=broad-except
        geocoding_cache = pd.DataFrame(
            columns=["address", "longitude", "latitude", "location_type", "score"]
        )
    new_geocoding_list = []
    for address_field in ["lugar", "direccion"]:
        full_addresses = df_moviles.apply(
            get_full_address, axis=1, address_field=address_field
        )
        for full_address in full_addresses.drop_duplicates():
            # Try to find address in cache
            gc_row = geocoding_cache.loc[geocoding_cache.address == full_address]
            if not gc_row.empty:
                continue

            # Address not found. Must geocode
            print(f'"{full_address}" not found in cache. Geocoding...')
            lng, lat, location_type, score = google_geocode_address(full_address)
            new_geocoding_list.append(
                {
                    "address": full_address,
                    "longitude": lng,
                    "latitude": lat,
                    "location_type": location_type,
                    "score": score,
                }
            )
    new_geocoding_df = pd.DataFrame(new_geocoding_list)
    geocoding_cache = pd.concat([geocoding_cache, new_geocoding_df])
    geocoding_cache = geocoding_cache.drop_duplicates()
    to_db(geocoding_cache, "geocoding_cache")
    # Geocoding candidates based on "lugar"
    df_ubicacion = df_moviles[["lugar", "localidad"]].copy()
    df_ubicacion["address"] = df_ubicacion.apply(
        get_full_address, axis=1, address_field="lugar"
    )
    df_ubicacion = pd.merge(df_ubicacion, geocoding_cache, on="address")

    # Geocoding candidates based on "direccion"
    df_direccion = df_moviles[["direccion", "localidad"]].copy()
    df_direccion["address"] = df_direccion.apply(
        get_full_address, axis=1, address_field="direccion"
    )
    df_direccion = pd.merge(df_direccion, geocoding_cache, on="address")

    assert len(df_moviles) == len(df_ubicacion) == len(df_direccion)
    df_moviles["latitude"] = None
    df_moviles["longitude"] = None
    for idx, row in df_moviles.iterrows():
        score_ubicacion = df_ubicacion.loc[idx, "score"]
        score_direccion = df_direccion.loc[idx, "score"]
        if score_direccion > score_ubicacion:
            lng = df_direccion.loc[idx, "longitude"]
            lat = df_direccion.loc[idx, "latitude"]
        else:
            lng = df_ubicacion.loc[idx, "longitude"]
            lat = df_ubicacion.loc[idx, "latitude"]

        df_moviles.loc[idx, "longitude"] = lng
        df_moviles.loc[idx, "latitude"] = lat

    db_fields = ["nombre", "localidad", "direccion", "fecha", "horario"]
    nice_fields = ["Nombre", "Localidad", "Dirección", "Fecha", "Horario"]
    df_moviles_keys = pd.DataFrame({"original": nice_fields, "db": db_fields})

    df_moviles["url"] = df_moviles.apply(get_gmaps_url, axis=1)
    gdf_moviles = gdf_from_df(df_moviles)
    gdf_moviles = gdf_moviles.drop(columns=["lugar"])
    gdf_moviles["nombre"] = "Equipo móvil en " + df_moviles["lugar"]
    gdf_moviles = gdf_moviles[db_fields + ["url", "geometry"]]
    to_db(gdf_moviles, "puntos_moviles")
    to_db(df_moviles_keys, "puntos_moviles_keys")


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    process_fixed_points()
    print("Fixed points done!")
    process_mobile_points()
    print("Mobile points done!")
