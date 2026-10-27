"""Geocoding utilities using the Google Maps API."""

import difflib
import os
import re

import unidecode

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

    gmaps = Client(os.environ["GOOGLE_MAPS_API_KEY"])

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

    gmaps = Client(os.environ["GOOGLE_MAPS_API_KEY"])
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
