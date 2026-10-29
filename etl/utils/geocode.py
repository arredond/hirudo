"""Geocoding utilities using the Google Maps API."""

import difflib
import logging
import os
import re
from typing import Any

import pandas as pd
import unidecode
from utils import db

log = logging.getLogger(__name__)

# A Places "Find Place" match has no location_type to score, so it gets a
# fixed score: above every non-ROOFTOP geocoding result (a Places hit is a
# specific establishment, while APPROXIMATE/GEOMETRIC_CENTER geocodes are
# often just a town's or the whole region's center), but below ROOFTOP.
PLACE_SCORE = 8

# Words too common to say whether a Places result is the place that was
# asked for (see place_matches).
PLACE_MATCH_STOPWORDS = {"del", "las", "los", "san", "santa"}

# How alike two words must be (difflib ratio, and length within a couple of
# letters) to count as the same name spelled differently — mostly Valencian
# vs. Castilian spellings Google mixes freely, e.g. "Burjassot"/"Burjasot",
# "Alzira"/"Alcira", "Moncada"/"Montcada", "Alaquàs"/"Alacuás". The length
# cap keeps unrelated words that merely share letters apart ("Finestrat" vs.
# a "Fiesta" hotel in the next town over).
PLACE_MATCH_SIMILARITY = 0.75
PLACE_MATCH_MAX_LENGTH_DIFFERENCE = 2

# Co-official names too different for PLACE_MATCH_SIMILARITY to pair up.
PLACE_NAME_ALIASES = {
    "elche": "elx",
    "alicante": "alacant",
    "jativa": "xativa",
    "orihuela": "oriola",
}


def geocode_address(full_address, postal_code=None, locality=None):
    """Geocode an address using the Google Maps API.

    Component filtering (postal_code, locality) narrows results when the
    address string alone is ambiguous. See:
    https://developers.google.com/maps/documentation/geocoding/requests-geocoding#component-filtering

    Returns (lng, lat, location_type, score) or (None, None, None, None) on failure.
    """
    from googlemaps import Client

    location_type_scoring = {
        "ROOFTOP": 9,
        "RANGE_INTERPOLATED": 7,
        "GEOMETRIC_CENTER": 6,
        "APPROXIMATE": 4,
    }

    # googlemaps attaches its API methods to Client at import time, which type
    # checkers can't see.
    gmaps: Any = Client(os.environ["GOOGLE_MAPS_API_KEY"])

    components = {"country": "ES"}
    if postal_code:
        components["postal_code"] = postal_code
    if locality:
        components["locality"] = locality

    results = gmaps.geocode(full_address, components=components)
    if not results:
        print(f"Geocoding failed for {full_address}. No results found")
        return (None, None, None, None)

    result = results[0]
    lng = result["geometry"]["location"]["lng"]
    lat = result["geometry"]["location"]["lat"]
    location_type = result["geometry"]["location_type"]
    score = location_type_scoring.get(location_type, 0)

    return (lng, lat, location_type, score)


def find_place(query: str, location_bias: str):
    """Look a free-text query up with the Places API's "Find Place".

    Unlike the Geocoding API (built for postal addresses), this is the same
    free-text search Google Maps' own search box runs, so it resolves venue
    descriptions like "Ademuz, en el Centro de Salud" that geocoding can't.
    location_bias is a Places bias string, e.g. "rectangle:S,W|N,E" — a bias,
    not a restriction, so far-off results still come back and need checking.

    Returns (lng, lat, name, formatted_address) or (None, None, None, None)
    when nothing is found.
    """
    from googlemaps import Client

    # googlemaps attaches its API methods to Client at import time, which type
    # checkers can't see.
    gmaps: Any = Client(os.environ["GOOGLE_MAPS_API_KEY"])
    response = gmaps.find_place(
        query,
        "textquery",
        fields=["name", "formatted_address", "geometry/location"],
        language="es",
        location_bias=location_bias,
    )
    candidates = response.get("candidates") or []
    if not candidates:
        print(f"Place search failed for {query}. No results found")
        return (None, None, None, None)

    place = candidates[0]
    location = place["geometry"]["location"]
    return (
        location["lng"],
        location["lat"],
        place.get("name"),
        place.get("formatted_address"),
    )


def significant_words(text: str) -> list[str]:
    """Lowercase, accent-free words of text, minus short/stop words."""
    return [
        word
        for word in re.findall(r"[a-z0-9]+", unidecode.unidecode(text).lower())
        if len(word) >= 3 and word not in PLACE_MATCH_STOPWORDS
    ]


def word_in_place(word: str, place_words: list[str], place_text: str) -> bool:
    """Tell whether a word (or a spelling/co-official variant) is in a place."""
    alias = PLACE_NAME_ALIASES.get(word)
    return (
        word in place_text
        or (alias is not None and alias in place_words)
        or any(
            abs(len(word) - len(place_word)) <= PLACE_MATCH_MAX_LENGTH_DIFFERENCE
            and difflib.SequenceMatcher(None, word, place_word).ratio()
            >= PLACE_MATCH_SIMILARITY
            for place_word in place_words
        )
    )


def place_matches(expected: str, name: str | None, address: str | None) -> bool:
    """Tell whether a Places result plausibly is the place that was asked for.

    Places always returns *something*, often a same-named place elsewhere
    (e.g. "Zuera, en el Centro de Día" -> a day center in Zaragoza city), so
    every significant word of the expected town/organization name must show
    up in the result's name or address (case- and accent-insensitive,
    tolerating spelling variants — see word_in_place). An expected name
    listing alternatives, like a bilingual town ("Almassora/Almazora") or a
    town plus district ("Castelló De La Plana, El Grao"), matches if any one
    of them does.
    """
    if not name and not address:
        return False
    place_text = unidecode.unidecode(f"{name or ''} {address or ''}").lower()
    place_words = re.findall(r"[a-z0-9]+", place_text)
    alternatives = [
        words for words in map(significant_words, re.split(r"[/,]", expected)) if words
    ]
    return any(
        all(word_in_place(word, place_words, place_text) for word in words)
        for words in alternatives
    )


def build_full_address(*parts: str) -> str:
    """Compose a full geocodable address string from its parts, in order.

    "Spain" is always appended, so callers only need to supply the
    region-specific parts (e.g. street, locality, region).
    """
    return ", ".join([*parts, "Spain"])


# Places ("Find Place") results share the geocoding_cache table with
# geocoding results; this prefix on their cache key keeps a free-text query
# from colliding with the same text geocoded as an address.
PLACE_CACHE_PREFIX = "place: "


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
        db.to_db(geocoding_cache, "geocoding_cache")

    return geocoding_cache


def refresh_places_cache(
    queries: set[str], geocoding_cache: pd.DataFrame, bounds: tuple
) -> pd.DataFrame:
    """Run a Places search for any query missing from the cache and persist it.

    Same contract as refresh_geocoding_cache, but keyed by
    PLACE_CACHE_PREFIX + query and keeping the matched place's name and
    address too, so place_candidate can check the match later without
    another API call. Not-found queries are cached as well (with no
    coordinates), so they aren't retried every run.
    """
    south, west, north, east = bounds
    location_bias = f"rectangle:{south},{west}|{north},{east}"
    cached_addresses = set(geocoding_cache["address"])
    new_rows = []
    for query in queries:
        key = PLACE_CACHE_PREFIX + query
        if key in cached_addresses:
            continue
        log.info("Place search: %s", query)
        lng, lat, name, address = find_place(query, location_bias)
        new_rows.append(
            {
                "address": key,
                "longitude": lng,
                "latitude": lat,
                "location_type": "PLACE",
                "score": PLACE_SCORE if lng is not None else None,
                "place_name": name,
                "place_address": address,
            }
        )

    if new_rows:
        geocoding_cache = pd.concat(
            [geocoding_cache, pd.DataFrame(new_rows)], ignore_index=True
        )
        geocoding_cache = geocoding_cache.drop_duplicates(subset=["address"])
        db.to_db(geocoding_cache, "geocoding_cache")

    return geocoding_cache


def place_candidate(
    query: str, expected: str, geocoding_cache: pd.DataFrame, bounds: tuple
) -> str | None:
    """Return a query's Places cache key if its result is trustworthy, else None.

    The result must fall inside bounds and mention the expected town or
    organization name (see place_matches) — Places otherwise happily returns
    a same-named place in another region (or country). The key returned can
    be passed to geocode_points as one more candidate column.
    """
    key = PLACE_CACHE_PREFIX + query
    cached = geocoding_cache.loc[geocoding_cache["address"] == key]
    if cached.empty or pd.isna(cached["latitude"].iloc[0]):
        return None
    place = cached.iloc[0]
    south, west, north, east = bounds
    in_bounds = (
        south <= place["latitude"] <= north and west <= place["longitude"] <= east
    )
    if in_bounds and place_matches(
        expected, place["place_name"], place["place_address"]
    ):
        return key
    return None


def geocode_mobile_points(
    df: pd.DataFrame, geocoding_cache: pd.DataFrame, region: str
) -> pd.DataFrame:
    """Geocode mobile points with both a 'lugar' and a 'direccion', using and
    updating the cache (Comunidad de Madrid's are shaped this way).

    Collects all unique addresses across both 'lugar' and 'direccion' fields,
    geocodes only addresses missing from the cache (one API call each), then
    picks the better-scored coordinate for each row.
    """
    all_addresses: set[str] = set()
    for field in ["lugar", "direccion"]:
        all_addresses.update(
            df.apply(
                lambda row, field=field: build_full_address(
                    row[field], row.localidad, region
                ),
                axis=1,
            ).unique()
        )

    geocoding_cache = refresh_geocoding_cache(all_addresses, geocoding_cache)

    def best_coords(row):
        addr_lugar = build_full_address(row["lugar"], row.localidad, region)
        addr_dir = build_full_address(row["direccion"], row.localidad, region)
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
        return pd.Series(
            {
                "longitude": scored.at[address, "longitude"],
                "latitude": scored.at[address, "latitude"],
            }
        )

    coords = df.apply(best_candidate, axis=1)
    return pd.concat([df, coords], axis=1)


def load_geocoding_cache() -> pd.DataFrame:
    """Load the shared geocoding cache, or an empty one on first run."""
    try:
        return db.from_db("geocoding_cache")
    except pd.errors.DatabaseError:  # table may not exist yet on first run
        return pd.DataFrame(
            columns=[
                "address",
                "longitude",
                "latitude",
                "location_type",
                "score",
                "place_name",
                "place_address",
            ]
        )


def geocode_missing_coords(
    df: pd.DataFrame, address_columns: str | list[str]
) -> pd.DataFrame:
    """Keep the source's own coordinates and geocode only the rows without them.

    For regions whose pages give most points' coordinates (a map link or
    embed) but not all. The address columns should be set only on rows
    missing coordinates (e.g. built with .where(df["latitude"].isna())), so
    nothing else reaches the geocoding cache or API (see geocode_points).
    """
    page_coords = df[["longitude", "latitude"]]
    df = geocode_points(
        df.drop(columns=["longitude", "latitude"]),
        load_geocoding_cache(),
        address_columns,
    )
    df[["longitude", "latitude"]] = page_coords.fillna(df[["longitude", "latitude"]])
    return df
