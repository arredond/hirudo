"""Tests for utils/crawl/galicia.py — scraping and parsing logic."""

import io

import pandas as pd
import pytest
import responses
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw
from utils.crawl import galicia

from tests.conftest import (
    GALICIA_FIXED_POINTS_HTML,
    GALICIA_MOBILE_POINTS_HTML,
    GALICIA_SEMAFORO_HTML,
)

# ---------------------------------------------------------------------------
# fixed points
# ---------------------------------------------------------------------------


def test_parse_gps_handles_both_notations():
    latitude, longitude = galicia.parse_gps(
        "Coordenadas GPS: 43°30'37.0\"N 8°12'58.2\"W."
    )
    assert latitude == pytest.approx(43.510278, abs=1e-6)
    assert longitude == pytest.approx(-8.216167, abs=1e-6)
    latitude, longitude = galicia.parse_gps(
        "Coordenadas GPS: 42º 52' 8.7''N 8º 33' 55.1''WOs."
    )
    assert latitude == pytest.approx(42.869083, abs=1e-6)
    assert longitude == pytest.approx(-8.565306, abs=1e-6)


def test_parse_gps_missing_returns_none():
    assert galicia.parse_gps("Coordenadas GPS: pendente") == (None, None)


@responses.activate
def test_scrape_fixed_points():
    responses.add(
        responses.GET, galicia.URL_FIXED_POINTS, body=GALICIA_FIXED_POINTS_HTML
    )

    df = galicia.scrape_fixed_points().set_index("name")

    ferrol = df.loc["Local de doazón de Ferrol"]
    assert ferrol["venue"] == "Hospital Arquitecto Marcide. Andar cero"
    assert ferrol["direccion"] == (
        "Hospital Arquitecto Marcide. Andar cero · Estrada de San Pedro de Leixa, "
        "s/n · 15405 Ferrol"
    )
    assert ferrol["localidad"] == "Ferrol"
    assert ferrol["codigo_postal"] == "15405"
    assert ferrol["horario"] == (
        "Luns de 15:00 a 22:00 / Martes, mércores e xoves de 8:00 a 15:00"
    )
    assert ferrol["latitude"] == pytest.approx(43.510278, abs=1e-6)
    assert bool(ferrol["plasma"])

    ourense = df.loc["Local de doazón de Ourense"]
    assert ourense["venue"] == (
        'Plaza Paz Novoa nº3. Aparcamento gratuíto "parking Orense"'
    )
    assert ourense["horario"] == (
        "Horario de inverno (de outubro a maio) / Luns e venres de 15:00 a 22:00"
    )
    assert pd.isna(ourense["latitude"])

    # No postcode line: the locality comes from the name
    assert df.loc["Local de doazón de Santiago", "localidad"] == "Santiago"


# ---------------------------------------------------------------------------
# mobile points
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("UNIDADE MÓBIL DIANTE DA CASA DA XUVENTUDE", "CASA DA XUVENTUDE"),
        ("UNIDADE MOBIL na Praza do Concello", "Praza do Concello"),
        (
            "UNIDADE MOVIL NA PARADA DO BUS (NA CARBALLEIRA)",
            "PARADA DO BUS (NA CARBALLEIRA)",
        ),
        (
            "UM no aparcadoiro da Facultade de Informática",
            "aparcadoiro da Facultade de Informática",
        ),
        ("UNIDADE MÓBIL AO CARÓN DO CENTRO DE SAÚDE", "CENTRO DE SAÚDE"),
        ("NA PRAZA PÚBLICA", "PRAZA PÚBLICA"),
        ("EN LA CALLE JESUS VALVERDE", "CALLE JESUS VALVERDE"),
        ("PRAZA CONDE FONTAO", "PRAZA CONDE FONTAO"),
        ("NOIA CONCELLO", "NOIA CONCELLO"),
    ],
)
def test_strip_mobile_unit_prefix(location, expected):
    assert galicia.strip_mobile_unit_prefix(location) == expected


def test_parse_mobile_points():
    soup = BeautifulSoup(GALICIA_MOBILE_POINTS_HTML, "lxml")
    stops = galicia.parse_mobile_points(soup)

    assert stops[0] == {
        "area": "ÁREA SANITARIA A CORUÑA E CEE",
        "fecha": "23/10/2026",
        "concello": "Sada",
        "lugar": "SADA",
        "direccion": "UNIDADE MÓBIL DIANTE DA CASA DA XUVENTUDE",
        "place_text": "CASA DA XUVENTUDE",
        "horario": "09:45 a 14:30 e 15:45 a 21:00",
        "provisional": False,
    }
    # The "Localización 2" placeholder is dropped
    foz = [stop for stop in stops if stop["concello"] == "Foz"]
    assert len(foz) == 1
    assert foz[0]["provisional"]
    assert foz[0]["direccion"] == "PRAZA CONDE FONTAO NO PEIRAO (AO CARON DA FUNCIONAL)"
    # One row, two parishes: each location item names its own place
    melon = [
        (stop["lugar"], stop["place_text"])
        for stop in stops
        if stop["concello"] == "Melón"
    ]
    assert melon == [("QUINS", "CENTRO DE SAÚDE"), ("MELON", "PARQUE DE MELON")]


# ---------------------------------------------------------------------------
# blood levels
# ---------------------------------------------------------------------------

RED, ORANGE, YELLOW, GREEN = (
    (220, 30, 30),
    (240, 140, 40),
    (240, 220, 40),
    (60, 180, 60),
)


def _semaforo(lit: list[tuple[int, int, int] | None]) -> Image.Image:
    """Draw a 4x2 grid of grey four-light cards, lighting one per card."""
    image = Image.new("RGB", (536, 468), "white")
    draw = ImageDraw.Draw(image)
    for index, colour in enumerate(lit):
        row, column = divmod(index, 4)
        x, y = column * 134 + 90, row * 234 + 40
        for light in range(4):
            box = (x - 16, y + light * 44 - 16, x + 16, y + light * 44 + 16)
            draw.ellipse(box, fill=(200, 200, 200))
        if colour is not None:
            light = [RED, ORANGE, YELLOW, GREEN].index(colour)
            draw.ellipse(
                (x - 16, y + light * 44 - 16, x + 16, y + light * 44 + 16), fill=colour
            )
    return image


def test_parse_blood_levels_image_reads_each_cards_colour():
    image = _semaforo([ORANGE, GREEN, YELLOW, RED, ORANGE, GREEN, GREEN, None])

    levels = {row["blood_type"]: row for row in galicia.parse_blood_levels_image(image)}

    assert levels["A+"]["status"] == "orange"
    assert levels["A+"]["label"] == "Nivel naranja"
    assert levels["A-"]["status"] == "green"
    assert levels["A-"]["level"] == 4
    assert levels["B+"]["status"] == "yellow"
    assert levels["B+"]["level"] == 3
    assert levels["B-"] == {
        "blood_type": "B-",
        "status": "red",
        "level": 1,
        "label": "Nivel rojo",
    }
    # No lit light: left out rather than guessed
    assert "AB-" not in levels


@responses.activate
def test_scrape_blood_levels_fetches_current_image():
    image_url = (
        "https://ados.sergas.gal/cartafol/PublishingImages/148/Semaforo_2026-10-20.png"
    )
    png = io.BytesIO()
    _semaforo([GREEN] * 8).save(png, format="PNG")
    responses.add(responses.GET, galicia.URL_BLOOD_LEVELS, body=GALICIA_SEMAFORO_HTML)
    responses.add(responses.GET, image_url, body=png.getvalue())

    df = galicia.scrape_blood_levels()

    assert df["blood_type"].tolist() == galicia.BLOOD_LEVEL_IMAGE_TYPES
    assert set(df["status"]) == {"green"}
