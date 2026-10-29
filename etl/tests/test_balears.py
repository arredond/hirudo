"""Tests for utils/crawl/balears.py — scraping and parsing logic."""

import datetime

import pandas as pd
import responses
from utils.crawl import balears

from tests.conftest import (
    BALEARS_CALENDAR_HTML,
    BALEARS_FIXED_POINTS_HTML,
    BALEARS_HOME_HTML,
    balears_detail_html,
)

TODAY = datetime.date(2026, 10, 28)
DETAIL_PREFIX = "https://www.donasang.org/on-puc-donar/es_calendari/"
FIXED_PREFIX = "https://www.donasang.org/on-puc-donar/es_punts-fixes/"

# The page-1 calendar's entries (28-30 Oct 2026): 17 stops at 15 distinct
# spots. The Banc de Sang repeats on each day under a new id, and so does
# the Manacor venue for its aféresis session.
PAGE_1_DETAIL_URLS = [
    DETAIL_PREFIX + "46968/palma",
    DETAIL_PREFIX + "46970/palma",
    DETAIL_PREFIX + "46973/sant-jordi",
    DETAIL_PREFIX + "46971/algaida",
    DETAIL_PREFIX + "46969/consell",
    DETAIL_PREFIX + "46972/sant-climent",
    DETAIL_PREFIX + "46974/palma",
    DETAIL_PREFIX + "46975/palma",
    DETAIL_PREFIX + "46979/eivissa",
    DETAIL_PREFIX + "46977/manacor",
    DETAIL_PREFIX + "46976/porto-cristo",
    DETAIL_PREFIX + "46978/manacor",
    DETAIL_PREFIX + "46980/palma",
    DETAIL_PREFIX + "46983/sa-pobla",
    DETAIL_PREFIX + "46984/sa-pobla",
    DETAIL_PREFIX + "46981/sineu",
    DETAIL_PREFIX + "46982/son-servera",
]

# A page past the window (2 Dec 2026, beyond the end of November): it stops
# the paging, so page 3 is never requested.
PAGE_2_BEYOND_WINDOW_HTML = """<html><body>
<div id="colPunts" class="clearfix">
<ul id="dies">
<li>
<h2>Miercoles,&nbsp;2&nbsp;de Diciembre&nbsp;de&nbsp;2026</h2>
<ul class="llistatPobles clearfix"><li><h3><a href="/on-puc-donar/es_calendari/47100/palma">Palma</a></h3><p><strong>Banc de Sang i Teixits</strong></p><p class="subtitle">Rosselló i Caçador, 20</p><span class="hores">de&nbsp;08:00h.&nbsp;a&nbsp;20:30h.</span></li></ul>
</li>
</ul>
</div>
</body></html>
"""


def register_calendar_pages(page_1_html=BALEARS_CALENDAR_HTML):
    responses.add(
        responses.GET,
        balears.URL_CALENDAR,
        body=page_1_html,
        match=[responses.matchers.query_param_matcher({"PAGE": "1"})],
    )
    responses.add(
        responses.GET,
        balears.URL_CALENDAR,
        body=PAGE_2_BEYOND_WINDOW_HTML,
        match=[responses.matchers.query_param_matcher({"PAGE": "2"})],
    )


def register_detail_pages(urls, latitude="39.582059", longitude="2.653558"):
    for url in urls:
        responses.add(responses.GET, url, body=balears_detail_html(latitude, longitude))


@responses.activate
def test_scrape_fixed_points_reads_listing_and_detail_coordinates():
    responses.add(
        responses.GET, balears.URL_FIXED_POINTS, body=BALEARS_FIXED_POINTS_HTML
    )
    responses.add(
        responses.GET,
        FIXED_PREFIX + "1/palma-mallorca-banco-de-sangre",
        body=balears_detail_html("39.581953", "2.653389"),
    )
    responses.add(
        responses.GET,
        FIXED_PREFIX + "4/mahon-menorca-centro-de-donaciones",
        body=balears_detail_html("39.884173", "4.258349"),
    )
    responses.add(
        responses.GET,
        FIXED_PREFIX + "6/eivissa",
        body=balears_detail_html("38.916526", "1.418271"),
    )

    df = balears.scrape_fixed_points().set_index("name")

    assert df.index.tolist() == [
        "Palma (Mallorca). Banco de sangre",
        "Mahón (Menorca). Centro de Donaciones",
        "Eivissa",
    ]
    assert df["localidad"].tolist() == ["Palma", "Mahón", "Eivissa"]
    palma = df.loc["Palma (Mallorca). Banco de sangre"]
    assert palma["direccion"] == "Rosselló i Cazador, 20"
    assert (
        palma["horario"]
        == "De lunes a viernes, de 8:00 a 20:30 h Sábados, de 9:00 a 13:30 h"
    )
    assert palma["latitude"] == 39.581953
    assert palma["longitude"] == 2.653389
    # Menorca and Ibiza only say "Consultar calendario campañas".
    assert pd.isna(df.loc["Eivissa", "horario"])
    assert df.loc["Eivissa", "direccion"] == "Hospital Can Misses. Antiguas Urgencias"
    assert df.loc["Eivissa", "longitude"] == 1.418271


def test_parse_calendar_reads_each_stop_with_its_date_and_hours():
    days = balears.parse_calendar(BALEARS_CALENDAR_HTML)

    assert [date for date, _ in days] == [
        datetime.date(2026, 10, 28),
        datetime.date(2026, 10, 29),
        datetime.date(2026, 10, 30),
    ]
    first_day = days[0][1]
    assert len(first_day) == 6
    banc = first_day[0]
    assert banc["lugar"] == "Banc de Sang i Teixits"
    assert banc["localidad"] == "Palma"
    assert banc["direccion"] == "Rosselló i Caçador, 20"
    assert banc["fecha"] == "28/10/2026"
    assert banc["horario"] == "08:00-20:30"
    assert banc["url"] == DETAIL_PREFIX + "46968/palma"
    assert banc["aferesis"] is False
    # A two-line address is joined with a space.
    assert first_day[1]["direccion"] == "BUS DAVANT RODONA CTRA. VALLDEMOSSA, KM 7,5"
    # The aféresis session on the 29th is flagged.
    aferesis = [stop for stop in days[1][1] if stop["aferesis"]]
    assert [stop["lugar"] for stop in aferesis] == ["AFERESI / AFERESIS MANACOR"]


def test_parse_spanish_date_and_hours():
    assert balears.parse_spanish_date(
        "Miercoles,\xa028\xa0de Octubre\xa0de\xa02026"
    ) == datetime.date(2026, 10, 28)
    assert balears.parse_spanish_date("sin fecha") is None
    assert balears.normalize_hours("de\xa008:00h.\xa0a\xa020:30h.") == "08:00-20:30"
    assert balears.normalize_hours("Consultar") is None


@responses.activate
def test_scrape_mobile_points_stops_at_window_end_and_fetches_each_spot_once():
    register_calendar_pages()
    register_detail_pages(PAGE_1_DETAIL_URLS)

    df = balears.scrape_mobile_points(TODAY)

    assert len(df) == 17
    assert df["fecha"].tolist()[0] == "28/10/2026"
    assert df["latitude"].notna().all()
    detail_calls = [
        call for call in responses.calls if call.request.url in PAGE_1_DETAIL_URLS
    ]
    # One detail fetch per distinct spot, not per calendar entry.
    assert len(detail_calls) == 15
    # The third call to the calendar (page 3) never happens: page 2 is past
    # the window.
    calendar_pages = [
        call.request.url
        for call in responses.calls
        if call.request.url and "punts.php" in call.request.url
    ]
    assert calendar_pages == [
        balears.URL_CALENDAR + "?PAGE=1",
        balears.URL_CALENDAR + "?PAGE=2",
    ]


@responses.activate
def test_scrape_mobile_points_drops_days_before_today():
    register_calendar_pages()
    register_detail_pages(PAGE_1_DETAIL_URLS)

    df = balears.scrape_mobile_points(datetime.date(2026, 10, 29))

    assert "28/10/2026" not in df["fecha"].tolist()
    assert len(df) == 11


@responses.activate
def test_fetch_coordinates_none_when_map_is_pinned_at_zero():
    responses.add(
        responses.GET,
        DETAIL_PREFIX + "46999/nowhere",
        body=balears_detail_html("0", "0"),
    )

    assert balears.fetch_coordinates(DETAIL_PREFIX + "46999/nowhere") == (None, None)


@responses.activate
def test_scrape_blood_levels_maps_digit_to_status():
    responses.add(responses.GET, balears.URL_HOME, body=BALEARS_HOME_HTML)

    df = balears.scrape_blood_levels().set_index("blood_type")

    assert df.index.tolist() == ["O-", "A-", "AB-", "B-", "O+", "A+", "AB+", "B+"]
    # Digit 3 is the nearly empty bag: red and most urgent.
    assert df.loc["O-", "status"] == "red"
    assert df.loc["O-", "level"] == 1
    assert df.loc["O-", "label"] == "Dona urgentemente"
    # Digit 2 is the half-full bag: orange.
    assert df.loc["A-", "status"] == "orange"
    assert df.loc["A-", "level"] == 2
    # Digit 1 is the full bag: green.
    assert df.loc["A+", "status"] == "green"
    assert df.loc["A+", "level"] == 3
    assert df.loc["A+", "label"] == "Dona en la próxima campaña"
