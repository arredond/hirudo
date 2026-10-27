"""Tests for the Places ("Find Place") candidate: utils/geocode.py's
find_place/place_matches and main.py's refresh_places_cache/place_candidate."""

import pandas as pd
import pytest
from utils import geocode

import main

CACHE_COLS = [
    "address",
    "longitude",
    "latitude",
    "location_type",
    "score",
    "place_name",
    "place_address",
]
BOUNDS = main.ARAGON_PLACES_BOUNDS


def _cache_with_place(query, lat, lng, name, address):
    return pd.DataFrame(
        [
            {
                "address": main.PLACE_CACHE_PREFIX + query,
                "longitude": lng,
                "latitude": lat,
                "location_type": "PLACE",
                "score": geocode.PLACE_SCORE,
                "place_name": name,
                "place_address": address,
            }
        ],
        columns=CACHE_COLS,
    )


# ---------------------------------------------------------------------------
# place_matches
# ---------------------------------------------------------------------------


def test_place_matches_town_in_address():
    assert geocode.place_matches(
        "Hecho", "Centro Salud Hecho", "Ctra. de Oza, 22720 Hecho, Huesca, España"
    )


def test_place_matches_is_accent_and_case_insensitive():
    assert geocode.place_matches(
        "Facultad Economía y Empresa",
        "Facultad de Economia y Empresa de la Universidad de Zaragoza",
        "Paseo Gran Vía, 2, 50005 Zaragoza",
    )


def test_place_matches_rejects_same_kind_of_place_elsewhere():
    # "Zuera, en el Centro de Día" -> a day center in Zaragoza city
    assert not geocode.place_matches(
        "Zuera", "Centro de Día S.E.D. Estrella", "Av. de la Jota, 61, 50014 Zaragoza"
    )


def test_place_matches_requires_every_significant_word():
    assert not geocode.place_matches(
        "Unidad Militar de Emergencia",
        "URBE Emergencias Mallén",
        "C. Delicias, 50550 Mallén, Zaragoza",
    )


def test_place_matches_no_result():
    assert not geocode.place_matches("Hecho", None, None)


# ---------------------------------------------------------------------------
# find_place
# ---------------------------------------------------------------------------


def test_find_place_returns_first_candidate(mocker, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    client = mocker.Mock()
    client.find_place.return_value = {
        "candidates": [
            {
                "name": "Ademuz Centro de Salud",
                "formatted_address": "Av. Valencia, 68, 46140 Ademuz, Valencia",
                "geometry": {"location": {"lat": 40.066, "lng": -1.283}},
            }
        ]
    }
    mocker.patch("googlemaps.Client", return_value=client)

    result = geocode.find_place("Ademuz, en el Centro de Salud", "rectangle:1,2|3,4")

    assert result == (
        -1.283,
        40.066,
        "Ademuz Centro de Salud",
        "Av. Valencia, 68, 46140 Ademuz, Valencia",
    )
    assert client.find_place.call_args.kwargs["location_bias"] == "rectangle:1,2|3,4"


def test_find_place_no_candidates(mocker, monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "test-key")
    client = mocker.Mock()
    client.find_place.return_value = {"candidates": [], "status": "ZERO_RESULTS"}
    mocker.patch("googlemaps.Client", return_value=client)

    assert geocode.find_place("nowhere", "rectangle:1,2|3,4") == (None,) * 4


# ---------------------------------------------------------------------------
# refresh_places_cache
# ---------------------------------------------------------------------------


def test_refresh_places_cache_skips_cached_queries(mocker):
    cache = _cache_with_place("Hecho, en el Centro de Salud", 42.7, -0.75, "x", "y")
    mock_find = mocker.patch("main.find_place")
    mock_to_db = mocker.patch("main.to_db")

    result = main.refresh_places_cache({"Hecho, en el Centro de Salud"}, cache, BOUNDS)

    mock_find.assert_not_called()
    mock_to_db.assert_not_called()
    assert len(result) == 1


def test_refresh_places_cache_stores_new_and_not_found_queries(mocker):
    cache = pd.DataFrame(columns=CACHE_COLS)
    mocker.patch(
        "main.find_place",
        side_effect=lambda query, bias: (
            (-1.28, 40.07, "Ademuz Centro de Salud", "46140 Ademuz, Valencia")
            if query.startswith("Ademuz")
            else (None, None, None, None)
        ),
    )
    mock_to_db = mocker.patch("main.to_db")

    result = main.refresh_places_cache(
        {"Ademuz, en el Centro de Salud", "Nowhere"}, cache, BOUNDS
    ).set_index("address")

    mock_to_db.assert_called_once()
    ademuz = result.loc["place: Ademuz, en el Centro de Salud"]
    assert ademuz["score"] == geocode.PLACE_SCORE
    assert ademuz["place_name"] == "Ademuz Centro de Salud"
    # Not-found is cached too, so it isn't retried, but never scores
    assert pd.isna(result.loc["place: Nowhere", "score"])


# ---------------------------------------------------------------------------
# place_candidate
# ---------------------------------------------------------------------------


def test_place_candidate_accepts_matching_place_in_bounds():
    # Ademuz is a Valencian exclave — outside Aragón proper, inside the box
    query = "Ademuz, en el Centro de Salud"
    cache = _cache_with_place(
        query, 40.066, -1.283, "Ademuz Centro de Salud", "46140 Ademuz, Valencia"
    )
    assert main.place_candidate(query, "Ademuz", cache, BOUNDS) == (
        "place: Ademuz, en el Centro de Salud"
    )


def test_place_candidate_rejects_out_of_bounds_match():
    query = "Orihuela, en el Centro de Salud"
    cache = _cache_with_place(
        query, 38.08, -0.94, "Centro de Salud de Orihuela", "03300 Orihuela, Alicante"
    )
    assert main.place_candidate(query, "Orihuela", cache, BOUNDS) is None


def test_place_candidate_rejects_non_matching_place():
    query = "Zuera, en el Centro de Día"
    cache = _cache_with_place(
        query, 41.65, -0.89, "Centro de Día S.E.D. Estrella", "50014 Zaragoza"
    )
    assert main.place_candidate(query, "Zuera", cache, BOUNDS) is None


def test_place_candidate_not_cached_or_not_found():
    cache = pd.DataFrame(columns=CACHE_COLS)
    assert main.place_candidate("x", "x", cache, BOUNDS) is None


@pytest.mark.parametrize(
    ("expected", "address"),
    [
        ("Burjassot", "C. Cementerio, 1, 46100 Burjasot, Valencia"),
        ("Alzira", "Ctra. Corbera, km 1, 46600 Alcira, Valencia"),
        ("Moncada", "CV-315, 7, 46113 Montcada, Valencia"),
        ("Elche", "Av. Altabix, 55, 03207 Elx, Alicante"),
    ],
)
def test_place_matches_tolerates_valencian_castilian_spellings(expected, address):
    assert geocode.place_matches(expected, "Some Place", address)


def test_place_matches_any_alternative_of_bilingual_town():
    assert geocode.place_matches(
        "ALMASSORA/ALMAZORA", "Neolith HQ", "C/Ibers 31, 12550 Almassora, Castelló"
    )
    assert geocode.place_matches(
        "CASTELLÓ DE LA PLANA, EL GRAO",
        "C.S.I. Grao Centre de Salut",
        "12100 Grao de Castellón, Castellón",
    )


def test_place_matches_still_rejects_other_town():
    # "Santa Pola, Club del Jubilado Casa del Mar" -> a club in Tarragona
    assert not geocode.place_matches(
        "SANTA POLA",
        "Club de Pensionistes de la Casa del Mar",
        "Arenal, 0, 43540 La Ràpita, Tarragona",
    )


def test_place_matches_rejects_words_merely_sharing_letters():
    # "PORT HOTELS-MIRAI", Finestrat -> a "Fiesta" hotel in Benidorm
    assert not geocode.place_matches(
        "Finestrat", "Hotel Port Fiesta Park", "Av. Foietes, 4, 03502 Benidorm"
    )
