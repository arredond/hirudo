"""Geocoding utilities using the Google Maps API."""

import os


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


def build_full_address(*parts: str) -> str:
    """Compose a full geocodable address string from its parts, in order.

    "Spain" is always appended, so callers only need to supply the
    region-specific parts (e.g. street, locality, region).
    """
    return ", ".join([*parts, "Spain"])
