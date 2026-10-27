"""Tests for utils/crawl/cataluna.py — scraping and parsing logic."""

import re

import pandas as pd
import responses
from bs4 import BeautifulSoup
from utils.crawl import cataluna

from tests.conftest import (
    CATALUNA_CALENDAR_HTML,
    CATALUNA_DONDE_HTML,
    CATALUNA_HOSPITAL_INFO_HTML,
    CATALUNA_STOP_HTML,
)

# ---------------------------------------------------------------------------
# fixed points
# ---------------------------------------------------------------------------


def test_parse_hospital_ids_dedupes_in_page_order():
    soup = BeautifulSoup(CATALUNA_DONDE_HTML, "lxml")
    assert cataluna.parse_hospital_ids(soup) == ["2", "30"]


def test_parse_hospital_info():
    soup = BeautifulSoup(CATALUNA_HOSPITAL_INFO_HTML, "lxml")
    info = cataluna.parse_hospital_info(soup)

    assert info == {
        "name": "BST L’Hospitalet - Santa Eulàlia",
        "horario": (
            "De lunes a viernes de 9 a 20 h. / Sábados de 9 a 14.30 h. / El / "
            "20 de octubre / la donación estará cerrada de 15 a 16h."
        ),
        "direccion": "C/ Jacint Verdaguer, 12",
        "codigo_postal": "08902",
        "localidad": "L'Hospitalet de Llobregat",
        "telefono": "93 557 36 41",
    }


def test_clean_locality_unwinds_sorting_article():
    assert cataluna.clean_locality("Hospitalet de Llobregat, L'") == (
        "L'Hospitalet de Llobregat"
    )
    assert cataluna.clean_locality("Prat de Llobregat, El") == "El Prat de Llobregat"
    assert cataluna.clean_locality("Girona") == "Girona"


@responses.activate
def test_scrape_fixed_points_fetches_each_info_page():
    responses.add(responses.GET, cataluna.URL_FIXED_POINTS, body=CATALUNA_DONDE_HTML)
    for hospital_id in ["2", "30"]:
        responses.add(
            responses.GET,
            cataluna.hospital_info_url(hospital_id),
            body=CATALUNA_HOSPITAL_INFO_HTML,
        )

    df = cataluna.scrape_fixed_points()

    assert len(df) == 2
    assert df["plasma"].all()
    assert "center_id" not in df.columns  # looked up by name, see docstring
    assert df["url"].tolist() == [
        cataluna.hospital_info_url("2"),
        cataluna.hospital_info_url("30"),
    ]


# ---------------------------------------------------------------------------
# mobile points
# ---------------------------------------------------------------------------


def test_parse_mobile_cards_reads_donation_types_from_buttons():
    soup = BeautifulSoup(CATALUNA_CALENDAR_HTML, "lxml")
    cards = {card["localidad"]: card for card in cataluna.parse_mobile_cards(soup)}

    assert set(cards) == {"Barcelona", "Esparreguera", "Vielha e Mijaran", "Gavà"}
    assert cards["Barcelona"]["venue"] == "Escola Santa Anna"
    assert cards["Barcelona"]["direccion"] == "C. Bailèn, 53"
    assert cards["Barcelona"]["fecha"] == "27/10/2026"
    assert (cards["Barcelona"]["sangre"], cards["Barcelona"]["plasma"]) == (True, False)
    assert (cards["Esparreguera"]["sangre"], cards["Esparreguera"]["plasma"]) == (
        True,
        True,
    )
    # Plasma-only: no blood button, date taken from the plasma link instead
    vielha = cards["Vielha e Mijaran"]
    assert (vielha["sangre"], vielha["plasma"]) == (False, True)
    assert vielha["fecha"] == "27/10/2026"
    assert vielha["url"] == cataluna.URL_MOBILE_POINTS
    assert cards["Gavà"]["fecha"] == "28/10/2026"


def test_parse_stop_hours_collapses_whitespace():
    soup = BeautifulSoup(CATALUNA_STOP_HTML, "lxml")
    assert cataluna.parse_stop_hours(soup) == "De 10:00 a 14:00 i de 16:00 a 21:00"


def test_parse_stop_hours_missing():
    assert cataluna.parse_stop_hours(BeautifulSoup("<p>x</p>", "lxml")) is None


def test_is_mobile_unit():
    assert cataluna.is_mobile_unit("Unidad móvil")
    assert cataluna.is_mobile_unit("Unitat mòbil - CEM Sagnier")
    assert cataluna.is_mobile_unit("Unidad Móbil delante Ayuntamiento")
    assert not cataluna.is_mobile_unit("Centro Cívico La Sitja")
    assert not cataluna.is_mobile_unit(None)


@responses.activate
def test_scrape_mobile_points_fetches_hours_for_blood_stops_only():
    responses.add(
        responses.GET, cataluna.URL_MOBILE_POINTS, body=CATALUNA_CALENDAR_HTML
    )
    responses.add(
        responses.GET,
        re.compile(r".*/sangre/recogida/poblacion//.*"),
        body=CATALUNA_STOP_HTML,
    )

    df = cataluna.scrape_mobile_points().set_index("localidad")

    assert df.loc["Barcelona", "horario"] == "De 10:00 a 14:00 i de 16:00 a 21:00"
    assert pd.isna(df.loc["Vielha e Mijaran", "horario"])
    # calendar page + one booking page per blood stop (3), none for plasma-only
    assert len(responses.calls) == 4
