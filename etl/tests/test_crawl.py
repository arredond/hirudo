"""Tests for utils/crawl/crawl.py — logic shared across region crawl modules."""

from utils.crawl.crawl import gmaps_url_from_coords


def test_gmaps_url_from_coords():
    class FakeRow:
        latitude = 40.32246
        longitude = -3.76751

    url = gmaps_url_from_coords(FakeRow())
    assert "40.32246" in url
    assert "-3.76751" in url
    assert url.startswith("https://www.google.com/maps")
