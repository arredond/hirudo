"""Tests for utils/crawl/crawl.py — logic shared across region crawl modules."""

from utils.crawl.crawl import gmaps_url_from_coords, title_name


def test_gmaps_url_from_coords():
    class FakeRow:
        latitude = 40.32246
        longitude = -3.76751

    url = gmaps_url_from_coords(FakeRow())
    assert "40.32246" in url
    assert "-3.76751" in url
    assert url.startswith("https://www.google.com/maps")


def test_title_name_keeps_spanish_particles_lowercase():
    assert title_name("ALCALÁ DE GUADAÍRA") == "Alcalá de Guadaíra"
    assert title_name("PUEBLA DEL RÍO") == "Puebla del Río"
    assert title_name("JEREZ DE LA FRONTERA") == "Jerez de la Frontera"
