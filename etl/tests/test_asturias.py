"""Tests for utils/crawl/asturias.py and regions/asturias.py.

The gauge tests draw synthetic dials with Pillow (a blue hub, three rim bands,
a red needle), so they don't depend on the live site's images.
"""

import datetime
import io
import json
import math
import re
from pathlib import Path

import pandas as pd
import pytest
import responses
from bs4 import BeautifulSoup
from PIL import Image
from regions import asturias as regions_asturias
from utils.crawl import asturias

from tests.conftest import (
    ASTURIAS_EVENTS_JSON,
    ASTURIAS_FIXED_POINTS_HTML,
    ASTURIAS_HOME_HTML,
)

TODAY = datetime.date(2026, 10, 28)
EVENTS = json.loads(ASTURIAS_EVENTS_JSON)["events"]
OPENING_HOURS_LOOKUP = (
    Path(__file__).parent.parent / "utils" / "opening_hours_fijos.json"
)

# ---------------------------------------------------------------------------
# fixed points
# ---------------------------------------------------------------------------


def fixed_points_df() -> pd.DataFrame:
    soup = BeautifulSoup(ASTURIAS_FIXED_POINTS_HTML, features="lxml")
    return pd.DataFrame(asturias.parse_fixed_points(soup)).set_index("name")


def test_parse_fixed_points_finds_every_centre():
    assert list(fixed_points_df().index) == [
        "H.U.C.A. – Centro Comunitario de Sangre y Tejidos de Asturias",
        "Centro de Salud Puerta de la Villa",
        "Cruz Roja de Gijón",
        "Asociación de Donantes de Sangre de Avilés",
    ]


def test_parse_fixed_points_reads_address_postcode_and_hours():
    df = fixed_points_df()

    huca = df.loc["H.U.C.A. – Centro Comunitario de Sangre y Tejidos de Asturias"]
    assert huca["localidad"] == "Oviedo"
    assert huca["codigo_postal"] == "33011"
    assert huca["direccion"] == (
        "H.U.C.A. Hospitalización – Planta 0. Av. Roma, S/N, 33011, Oviedo, Asturias"
    )
    assert (
        huca["horario"] == "Lunes a viernes: 08.30-20.30 h. | Sábados: 10.00-14.00 h."
    )

    cruz_roja = df.loc["Cruz Roja de Gijón"]
    assert cruz_roja["direccion"] == "C/ Uría nº 37, 33202 Gijón, Asturias"
    assert cruz_roja["localidad"] == "Gijón"


def test_parse_fixed_points_joins_multi_line_hours():
    aviles = fixed_points_df().loc["Asociación de Donantes de Sangre de Avilés"]
    assert aviles["horario"] == (
        "Martes y jueves: 16.00-21.00 h. / "
        "Primer jueves laborable de cada mes: 9.00-14.00 y 16.00-21.00 h."
    )


def test_parse_fixed_points_takes_coordinates_from_map_embeds():
    df = fixed_points_df()

    # HUCA's embed carries its marker as "!2d<lng>!3d<lat>".
    huca = df.loc["H.U.C.A. – Centro Comunitario de Sangre y Tejidos de Asturias"]
    assert huca["latitude"] == pytest.approx(43.375323)
    assert huca["longitude"] == pytest.approx(-5.829514)

    # The town centres' embeds carry "ll=<lat>,<lng>".
    puerta = df.loc["Centro de Salud Puerta de la Villa"]
    assert puerta["latitude"] == pytest.approx(43.539316)
    assert puerta["longitude"] == pytest.approx(-5.664576)


def test_coordinates_from_embed_handles_both_forms_and_none():
    assert asturias.coordinates_from_embed(
        "https://maps.google.es/maps?q=x&ll=43.5,-5.6&z=14"
    ) == (43.5, -5.6)
    assert asturias.coordinates_from_embed(
        "https://www.google.com/maps/embed?pb=!1m18!2d-5.82!3d43.37!4f13"
    ) == (43.37, -5.82)
    assert asturias.coordinates_from_embed("https://www.google.com/maps") == (
        None,
        None,
    )


def test_title_name_keeps_spanish_particles_lowercase():
    assert asturias.title_name("CENTRO DE SALUD PUERTA DE LA VILLA") == (
        "Centro de Salud Puerta de la Villa"
    )
    assert asturias.title_name("ASOCIACIÓN DE DONANTES DE SANGRE DE AVILÉS") == (
        "Asociación de Donantes de Sangre de Avilés"
    )


@responses.activate
def test_scrape_fixed_points_fetches_the_page():
    responses.add(
        responses.GET, asturias.URL_FIXED_POINTS, body=ASTURIAS_FIXED_POINTS_HTML
    )

    df = asturias.scrape_fixed_points()

    assert len(df) == 4
    assert set(df["url"]) == {asturias.URL_FIXED_POINTS}


def test_fixed_point_hours_are_in_the_lookup_table():
    lookup = json.loads(OPENING_HOURS_LOOKUP.read_text(encoding="utf-8"))
    names = set(fixed_points_df().index)
    assert names <= set(lookup)


# ---------------------------------------------------------------------------
# mobile points (calendar events)
# ---------------------------------------------------------------------------


def paragraph(html: str):
    return BeautifulSoup(html, features="lxml").find("p")


def test_parse_event_makes_one_spot_per_paragraph():
    gijon = next(event for event in EVENTS if event["title"] == "Gijón")

    spots = asturias.parse_event(gijon)

    assert spots == [
        {
            "localidad": "Gijón",
            "lugar": "La Arena",
            "direccion": "La Arena. C/ Menéndez Pelayo, entre núm. 13 y 17.",
            "fecha": "01/10/2026",
            "horario": "09:00 a 14:00, 16:00 a 21:00",
            "url": "https://donasturias.org/eventos/gijon-27/",
        },
        {
            "localidad": "Gijón",
            "lugar": "Natahoyo",
            "direccion": "Natahoyo. C/ El Cortijo, delante AAVV Atalía, al lado del parque.",
            "fecha": "01/10/2026",
            "horario": "09:00 a 14:00, 16:00 a 21:00",
            "url": "https://donasturias.org/eventos/gijon-27/",
        },
    ]


def test_parse_event_splits_multi_spot_towns():
    carbayin = next(event for event in EVENTS if event["title"] == "Carbayín")

    spots = asturias.parse_event(carbayin)

    assert [(spot["lugar"], spot["horario"]) for spot in spots] == [
        ("Carbayín Bajo", "16:00 a 17:30"),
        ("Carbayín Alto", "18:00 a 21:00"),
    ]


def test_parse_spot_keeps_abbreviations_in_the_venue():
    spot = asturias.parse_spot(
        paragraph("<p>16.30-18.00 | Avda. Juan Sitges, frente Real Balneario.</p>"),
        "Salinas",
        "29/10/2026",
        "https://donasturias.org/eventos/salinas-2/",
    )

    assert spot["lugar"] == "Avda. Juan Sitges, frente Real Balneario"
    assert spot["direccion"] == "Avda. Juan Sitges, frente Real Balneario."


def test_parse_spot_ignores_paragraphs_that_are_not_spots():
    spot = asturias.parse_spot(
        paragraph("<p>Para donar plasma regístrate en www.yodonoplasma.es</p>"),
        "Gijón",
        "01/10/2026",
        "https://donasturias.org/eventos/gijon-27/",
    )

    assert spot is None


def test_is_fixed_points_event_matches_the_calendar_title():
    fixed = next(event for event in EVENTS if event["title"] == "PUNTOS FIJOS")
    assert asturias.is_fixed_points_event(fixed)
    assert not asturias.is_fixed_points_event(
        next(event for event in EVENTS if event["title"] == "Gijón")
    )


@responses.activate
def test_scrape_mobile_points_skips_fixed_centre_days_and_flattens_spots():
    responses.add(
        responses.GET,
        asturias.URL_EVENTS_API,
        json={"events": EVENTS, "next_rest_url": None},
    )

    df = asturias.scrape_mobile_points(today=TODAY)

    assert "PUNTOS FIJOS" not in set(df["localidad"])
    gijon = df[df["localidad"] == "Gijón"]
    assert list(gijon["lugar"]) == ["La Arena", "Natahoyo"]
    assert list(df.columns) == asturias.MOBILE_POINT_COLUMNS


@responses.activate
def test_scrape_mobile_points_follows_next_page():
    responses.add(
        responses.GET,
        asturias.URL_EVENTS_API,
        json={
            "events": [EVENTS[0]],
            "next_rest_url": asturias.URL_EVENTS_API + "?page=2",
        },
        match=[
            responses.matchers.query_param_matcher(
                {"per_page": "50", "start_date": "2026-10-28"}
            )
        ],
    )
    responses.add(
        responses.GET,
        asturias.URL_EVENTS_API,
        json={"events": [EVENTS[1]], "next_rest_url": None},
        match=[responses.matchers.query_param_matcher({"page": "2"})],
    )

    df = asturias.scrape_mobile_points(today=TODAY)

    assert list(df["localidad"]) == [
        "Acuartelamiento Cabo Noval",
        "Carbayín",
        "Carbayín",
    ]


def test_scrape_mobile_points_with_no_events_keeps_its_columns():
    with responses.RequestsMock() as mock:
        mock.add(
            responses.GET,
            asturias.URL_EVENTS_API,
            json={"events": [], "next_rest_url": None},
        )
        df = asturias.scrape_mobile_points(today=TODAY)

    assert df.empty
    assert list(df.columns) == asturias.MOBILE_POINT_COLUMNS


# ---------------------------------------------------------------------------
# blood levels (gauge images)
# ---------------------------------------------------------------------------

GAUGE_SIZE = (109, 108)
GREEN_BAND = (30, 150, 40)
YELLOW_BAND = (255, 160, 10)
RED_BAND = (220, 50, 20)
HUB_BLUE = (40, 90, 200)


def band_colour(angle: float):
    """The rim band a counterclockwise angle falls in, with a gap at the bottom."""
    angle %= 360
    if angle < 45 or angle >= 315:
        return GREEN_BAND
    if angle < 135:
        return YELLOW_BAND
    if angle < 225:
        return RED_BAND
    return None


def draw_gauge(needle_angle, needle_length: float = 0.9) -> Image.Image:
    """A synthetic dial: rim bands, a blue hub and a needle at needle_angle.

    The needle's tip runs into the band (as on the live gauges), so reading
    the band has to look past it.
    """
    width, height = GAUGE_SIZE
    image = Image.new("RGB", GAUGE_SIZE, (247, 247, 247))
    pixels = image.load()
    hub_x, hub_y = (width - 1) / 2, (height - 1) / 2
    rim = min(width, height) / 2 * asturias.GAUGE_RIM_FRACTION

    for half_degree in range(720):
        angle = half_degree / 2
        colour = band_colour(angle)
        if colour is None:
            continue
        theta = math.radians(angle)
        for radius in range(34, 47):
            x = round(hub_x + radius * math.cos(theta))
            y = round(hub_y - radius * math.sin(theta))
            pixels[x, y] = colour

    for y in range(height):
        for x in range(width):
            if (x - hub_x) ** 2 + (y - hub_y) ** 2 <= 9:
                pixels[x, y] = HUB_BLUE

    if needle_angle is not None:
        theta = math.radians(needle_angle)
        radius = 3.5
        while radius <= needle_length * rim:
            x = round(hub_x + radius * math.cos(theta))
            y = round(hub_y - radius * math.sin(theta))
            pixels[x, y] = RED_BAND
            radius += 0.25
    return image


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.parametrize(
    ("needle_angle", "expected_status", "expected_level"),
    [
        (10, "green", 3),
        (90, "yellow", 2),
        (200, "red", 1),
        # The needle's tip runs into the yellow band; the band is still read.
        (52, "yellow", 2),
    ],
)
def test_gauge_level_reads_the_band_under_the_needle(
    needle_angle, expected_status, expected_level
):
    status, level, _ = asturias.gauge_level(draw_gauge(needle_angle))

    assert status == expected_status
    assert level == expected_level


def test_gauge_level_without_a_needle_is_none():
    assert asturias.gauge_level(draw_gauge(None)) is None


def test_gauge_blood_type_reads_the_filename():
    cases = {
        "omas230-1.jpg": "0+",
        "o-90.jpg": "0-",
        "Amas140.jpg": "A+",
        "A-45.jpg": "A-",
        "Bmas60.jpg": "B+",
        "B-9.jpg": "B-",
        "ABmas40.jpg": "AB+",
        "ab-1.jpg": "AB-",
    }
    for filename, blood_type in cases.items():
        assert asturias.gauge_blood_type(filename) == blood_type
    assert asturias.gauge_blood_type("DONAASTURIAS-Slider-Dona-Sangre.png") is None
    assert asturias.gauge_blood_type("logo2.png") is None


def test_parse_gauge_images_skips_unreadable_gauges():
    blank = Image.new("RGB", GAUGE_SIZE, (255, 255, 255))

    blood_levels = asturias.parse_gauge_images([("0+", draw_gauge(10)), ("A+", blank)])

    assert blood_levels == [
        {"blood_type": "0+", "status": "green", "level": 3, "label": "Nivel verde"}
    ]


@responses.activate
def test_scrape_blood_levels_reads_every_gauge_on_the_homepage():
    needles = {
        "omas230-1.jpg": 10,
        "o-90.jpg": 90,
        "Amas140.jpg": 200,
        "A-45.jpg": 10,
        "Bmas60.jpg": 52,
        "B-9.jpg": 52,
        "ABmas40.jpg": 90,
        "ab-1.jpg": 200,
    }
    responses.add(responses.GET, asturias.URL_BASE, body=ASTURIAS_HOME_HTML)
    for filename, needle in needles.items():
        url = re.search(
            r'https://donasturias\.org/wp-content/uploads/[^"]*/' + re.escape(filename),
            ASTURIAS_HOME_HTML,
        ).group(0)
        responses.add(
            responses.GET,
            url,
            body=png_bytes(draw_gauge(needle)),
            content_type="image/png",
        )

    df = asturias.scrape_blood_levels()

    assert list(df["blood_type"]) == ["0+", "0-", "A+", "A-", "B+", "B-", "AB+", "AB-"]
    assert list(df["status"]) == [
        "green",
        "yellow",
        "red",
        "green",
        "yellow",
        "yellow",
        "yellow",
        "red",
    ]
    assert list(df.columns) == ["blood_type", "status", "level", "label"]


# ---------------------------------------------------------------------------
# regions/asturias.py
# ---------------------------------------------------------------------------


def fixed_points_frame() -> pd.DataFrame:
    soup = BeautifulSoup(ASTURIAS_FIXED_POINTS_HTML, features="lxml")
    df = pd.DataFrame(
        asturias.parse_fixed_points(soup), columns=asturias.FIXED_POINT_COLUMNS
    )
    df["url"] = asturias.URL_FIXED_POINTS
    return df


def test_scrape_fixed_points_asturias_uses_page_coordinates_without_geocoding(
    mocker,
):
    mocker.patch(
        "utils.crawl.asturias.scrape_fixed_points", return_value=fixed_points_frame()
    )
    mocker.patch(
        "utils.points.load_opening_hours_fijos",
        return_value=json.loads(OPENING_HOURS_LOOKUP.read_text(encoding="utf-8")),
    )
    empty_cache = pd.DataFrame(columns=["address", "longitude", "latitude", "score"])
    mocker.patch("utils.geocode.load_geocoding_cache", return_value=empty_cache)
    mock_refresh = mocker.patch(
        "utils.geocode.refresh_geocoding_cache", return_value=empty_cache
    )

    df = regions_asturias.scrape_fixed_points()

    # Every centre has coordinates on its page, so nothing is sent to the API.
    mock_refresh.assert_called_once()
    assert mock_refresh.call_args.args[0] == set()
    assert df["region"].eq(regions_asturias.REGION).all()
    assert df["latitude"].notna().all()
    assert df["opening_hours"].notna().all()
    assert df["gmaps_url"].str.startswith("https://www.google.com/maps").all()


def test_scrape_mobile_points_asturias_one_row_per_spot(mocker):
    gijon = next(event for event in EVENTS if event["title"] == "Gijón")
    spots = pd.DataFrame(
        asturias.parse_event(gijon), columns=asturias.MOBILE_POINT_COLUMNS
    )
    mocker.patch("utils.crawl.asturias.scrape_mobile_points", return_value=spots)
    mocker.patch("utils.geocode.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("utils.geocode.refresh_places_cache", return_value=pd.DataFrame())
    mocker.patch("utils.geocode.place_candidate", return_value=None)

    def fake_geocode_points(df, geocoding_cache, address_columns):
        df["longitude"] = -5.66
        df["latitude"] = 43.54
        return df

    mocker.patch("utils.geocode.geocode_points", side_effect=fake_geocode_points)

    df = regions_asturias.scrape_mobile_points()

    assert list(df["name"]) == ["Equipo móvil en La Arena", "Equipo móvil en Natahoyo"]
    assert set(df["region"]) == {regions_asturias.REGION}
    assert df["opening_hours"].notna().all()
    assert df["medula"].eq(False).all()
