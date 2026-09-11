"""Tests for opening_hours.py — building OSM opening_hours strings for mobile points."""

from utils.opening_hours import parse_mobile_hours


def test_parse_mobile_hours_single_range():
    assert (
        parse_mobile_hours("10/09/2026", "17:00 a 20:45") == "2026 Sep 10 17:00-20:45"
    )


def test_parse_mobile_hours_dot_separator():
    # Some rows use "." instead of ":" between hours and minutes
    assert (
        parse_mobile_hours("15/09/2026", "10.00 a 14.00") == "2026 Sep 15 10:00-14:00"
    )


def test_parse_mobile_hours_split_shift():
    # Some rows describe a morning and afternoon range on the same day
    result = parse_mobile_hours("14/09/2026", "10:00 a 14:00 17:00 a 21:00")
    assert result == "2026 Sep 14 10:00-14:00,17:00-21:00"


def test_parse_mobile_hours_unparseable_horario_returns_none():
    assert parse_mobile_hours("14/09/2026", "Cancelado") is None


def test_parse_mobile_hours_unparseable_fecha_returns_none():
    assert parse_mobile_hours("not-a-date", "17:00 a 20:45") is None
