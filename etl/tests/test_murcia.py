"""Tests for utils/crawl/murcia.py and regions/murcia.py."""

import datetime
import json
import pathlib

import pytest
from opening_hours import OpeningHours
from regions import murcia as regions_murcia
from utils.crawl import murcia

from tests.conftest import MURCIA_CALENDAR_HTML, MURCIA_HOME_HTML

TODAY = datetime.date(2026, 10, 29)

OPENING_HOURS_FIJOS = (
    pathlib.Path(__file__).resolve().parent.parent
    / "utils"
    / "opening_hours_fijos.json"
)
FIXED_POINT_NAMES = [
    "Centro Regional de Hemodonación",
    "Hospital Santa María del Rosell",
]


@pytest.fixture(autouse=True)
def _clear_page_cache():
    murcia.PAGES.clear()
    murcia.LAST_REQUEST["at"] = None
    yield
    murcia.PAGES.clear()
    murcia.LAST_REQUEST["at"] = None


def _mock_pages(mocker, pages: dict[str, str | None]):
    return mocker.patch.object(murcia, "fetch_page", side_effect=pages.get)


def test_parse_fixed_points_reads_title_hours_and_embed_coordinates():
    points = murcia.parse_fixed_points(MURCIA_HOME_HTML)

    # Yecla's spot is skipped: the calendar already lists its days.
    assert [point["name"] for point in points] == [
        "Centro Regional de Hemodonación",
        "Hospital Santa María del Rosell",
    ]
    crh, cartagena = points
    assert crh["localidad"] == "Murcia"
    assert crh["telefono"] == "968 341 990"
    assert crh["horario"].startswith("Lunes a viernes de 8:30 a 20:30 horas.")
    assert crh["plasma"] is True
    assert crh["observaciones"] is None
    assert crh["latitude"] == pytest.approx(37.983067)
    assert crh["longitude"] == pytest.approx(-1.121929)
    assert cartagena["localidad"] == "Cartagena"
    assert cartagena["plasma"] is False
    assert cartagena["observaciones"] == "Parking en la puerta"
    assert cartagena["latitude"] == pytest.approx(37.607575)
    assert cartagena["longitude"] == pytest.approx(-0.97662)


def test_parse_blood_levels_maps_image_filename_and_skips_unknown():
    levels = murcia.parse_blood_levels(MURCIA_HOME_HTML)

    assert levels == [
        {
            "blood_type": "0+",
            "status": "green",
            "level": 3,
            "label": "Dona de manera habitual",
        },
        {
            "blood_type": "A-",
            "status": "orange",
            "level": 2,
            "label": "Donación en 2/3 días",
        },
    ]


def test_parse_calendar_keeps_stops_from_today_on():
    stops = murcia.parse_calendar(MURCIA_CALENDAR_HTML, TODAY)

    assert len(stops) == 2
    assert stops[0] == {
        "lugar": "El Mosca by Logista (Edificio Oficinas Centrales)",
        "localidad": "Molina de Segura",
        "direccion": "Carr de Madrid, Km 381",
        "fecha": "29/10/2026",
        "horario": "09:30-14:00",
        "latitude": pytest.approx(38.0971333),
        "longitude": pytest.approx(-1.2273591),
        "url": murcia.URL_CALENDAR,
    }


def test_parse_calendar_title_cases_towns_and_tolerates_missing_coordinates():
    stop = murcia.parse_calendar(MURCIA_CALENDAR_HTML, TODAY)[1]

    assert stop["lugar"] == "CEIP Pasico Campillo (Colegio)"
    assert stop["localidad"] == "Campillo - Lorca"
    assert stop["horario"] == "17:00-21:00"
    assert stop["latitude"] is None
    assert stop["longitude"] is None


def test_fetch_page_returns_none_on_captcha_and_caches(mocker):
    get = mocker.patch.object(
        murcia.SESSION,
        "get",
        return_value=mocker.Mock(
            text="<title>Radware Captcha Page</title>",
            raise_for_status=lambda: None,
        ),
    )

    assert murcia.fetch_page(murcia.URL_BASE) is None
    assert murcia.fetch_page(murcia.URL_BASE) is None
    get.assert_called_once()


def test_fetch_page_waits_out_the_crawl_delay(mocker):
    mocker.patch.object(
        murcia.SESSION,
        "get",
        return_value=mocker.Mock(text="<html></html>", raise_for_status=lambda: None),
    )
    sleep = mocker.patch.object(murcia.time, "sleep")

    murcia.fetch_page(murcia.URL_BASE)
    sleep.assert_not_called()
    murcia.fetch_page(murcia.URL_CALENDAR)

    (delay,) = sleep.call_args.args
    assert 9 < delay <= murcia.CRAWL_DELAY_SECONDS


def test_region_scrapes_every_table(mocker):
    _mock_pages(
        mocker,
        {murcia.URL_BASE: MURCIA_HOME_HTML, murcia.URL_CALENDAR: MURCIA_CALENDAR_HTML},
    )
    mocker.patch.object(murcia.comunidad_valenciana, "madrid_today", return_value=TODAY)
    mocker.patch(
        "utils.points.load_opening_hours_fijos",
        return_value={
            "Centro Regional de Hemodonación": (
                "Mo-Fr 08:30-20:30; Aug Mo-Fr 08:30-14:30; PH off"
            )
        },
    )

    fixed = regions_murcia.scrape_fixed_points()
    mobile = regions_murcia.scrape_mobile_points()
    levels = regions_murcia.scrape_blood_levels()

    assert (fixed["region"] == "Región de Murcia").all()
    assert fixed.loc[0, "opening_hours"] == (
        "Mo-Fr 08:30-20:30; Aug Mo-Fr 08:30-14:30; PH off"
    )
    assert str(fixed.loc[0, "gmaps_url"]).startswith(
        "https://www.google.com/maps?q=37.98"
    )
    assert mobile["name"].tolist() == [
        "Equipo móvil en El Mosca by Logista (Edificio Oficinas Centrales)",
        "Equipo móvil en CEIP Pasico Campillo (Colegio)",
    ]
    assert mobile.loc[0, "opening_hours"] == "2026 Oct 29 09:30-14:00"
    assert levels["source"].tolist() == ["murciasalud.es"] * 2


def test_region_returns_empty_tables_when_blocked(mocker):
    _mock_pages(mocker, {})

    fixed = regions_murcia.scrape_fixed_points()
    mobile = regions_murcia.scrape_mobile_points()
    levels = regions_murcia.scrape_blood_levels()

    assert fixed.empty and "region" in fixed.columns
    assert mobile.empty and "latitude" in mobile.columns
    assert levels.empty and "source" in levels.columns


def test_every_fixed_point_has_valid_hand_built_hours():
    lookup = json.loads(OPENING_HOURS_FIJOS.read_text(encoding="utf-8"))

    for name in FIXED_POINT_NAMES:
        OpeningHours(lookup[name])
