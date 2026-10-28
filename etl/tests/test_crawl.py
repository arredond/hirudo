"""Tests for utils/crawl/crawl.py — logic shared across region crawl modules."""

import pathlib

import certifi
import pytest
import responses
from utils.crawl import crawl
from utils.crawl.crawl import gmaps_url_from_coords, title_name


def test_gmaps_url_from_coords():
    class FakeRow:
        latitude = 40.32246
        longitude = -3.76751

    url = gmaps_url_from_coords(FakeRow())
    assert "40.32246" in url
    assert "-3.76751" in url
    assert url.startswith("https://www.google.com/maps")


# ---------------------------------------------------------------------------
# resolve_gmaps_coords
# ---------------------------------------------------------------------------


@responses.activate
def test_resolve_gmaps_coords_prefers_precise_pin():
    url = "https://maps.app.goo.gl/hRDcjSERk7mN4TSaA"
    responses.add(
        responses.GET,
        url,
        status=302,
        headers={
            "Location": "https://www.google.es/maps/place/X/@40.65,-4.69,17z/"
            "data=!3m2!4b1!8m2!3d40.6503096!4d-4.6924824"
        },
    )

    lat, lon = crawl.resolve_gmaps_coords(url)

    assert lat == pytest.approx(40.6503096)
    assert lon == pytest.approx(-4.6924824)


@responses.activate
def test_resolve_gmaps_coords_falls_back_to_viewport():
    url = "https://maps.app.goo.gl/example"
    responses.add(
        responses.GET,
        url,
        status=302,
        headers={"Location": "https://www.google.es/maps/place/X/@40.65,-4.69,17z"},
    )

    lat, lon = crawl.resolve_gmaps_coords(url)

    assert lat == pytest.approx(40.65)
    assert lon == pytest.approx(-4.69)


@responses.activate
def test_resolve_gmaps_coords_raises_when_unparseable():
    url = "https://maps.app.goo.gl/example"
    responses.add(
        responses.GET, url, status=302, headers={"Location": "https://google.es/maps"}
    )

    with pytest.raises(ValueError):
        crawl.resolve_gmaps_coords(url)


def test_ca_bundle_with_appends_extra_cert_to_certifi_roots():
    path = crawl.ca_bundle_with("sectigo_public_server_authentication_ca_dv_r36.pem")
    bundle = pathlib.Path(path).read_text()
    assert bundle.startswith(pathlib.Path(certifi.where()).read_text())
    assert bundle.count("BEGIN CERTIFICATE") == (
        pathlib.Path(certifi.where()).read_text().count("BEGIN CERTIFICATE") + 1
    )


def test_title_name_keeps_spanish_particles_lowercase():
    assert title_name("ALCALÁ DE GUADAÍRA") == "Alcalá de Guadaíra"
    assert title_name("PUEBLA DEL RÍO") == "Puebla del Río"
    assert title_name("JEREZ DE LA FRONTERA") == "Jerez de la Frontera"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Con cita previa telefónica 928 730 362. Viernes de 08:00 a 14:00h.", True),
        ("ELCHE-SOLO DONACIÓN DE PLASMA CON CITA PREVIA-ELCHE HOSPITAL", True),
        ("Bilbao Bombero Etxaniz - Solo Plasma/Cita", True),
        ("Donación previa cita en el teléfono 900", True),
        ("¿Te has apuntado pero no podrás venir? Cancela la cita", False),
        ("Hospital Universitari de Tortosa Verge de la Cinta", False),
        ("De lunes a viernes de 9 a 20 h.", False),
        (None, False),
    ],
)
def test_requires_appointment(text, expected):
    assert crawl.requires_appointment(text) is expected
