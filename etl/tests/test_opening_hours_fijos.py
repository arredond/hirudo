"""Tests for the hand-built fixed-point opening_hours lookup table.

opening_hours_fijos.json is maintained by hand in an active session rather
than parsed automatically, since fixed points rarely change. This guards
against typos: every value must be a syntactically valid OSM opening_hours
string.
"""

import json
from pathlib import Path

import pandas as pd
from opening_hours import OpeningHours, ParserError

import main

LOOKUP_PATH = Path(__file__).parent.parent / "utils" / "opening_hours_fijos.json"
with open(LOOKUP_PATH, encoding="utf-8") as f:
    OPENING_HOURS_FIJOS = json.load(f)


def test_all_lookup_entries_are_valid_opening_hours_strings():
    invalid = {}
    for key, value in OPENING_HOURS_FIJOS.items():
        try:
            OpeningHours(value)
        except ParserError as e:
            invalid[key] = str(e)

    assert not invalid, f"Invalid opening_hours strings: {invalid}"


def test_opening_hours_for_fixed_point_matches_by_center_id():
    row = pd.Series({"center_id": "2544", "name": "Some Hospital"})
    lookup = {"2544": "Mo-Fr 09:00-14:00"}
    assert main.opening_hours_for_fixed_point(row, lookup) == "Mo-Fr 09:00-14:00"


def test_opening_hours_for_fixed_point_falls_back_to_name():
    row = pd.Series({"center_id": None, "name": "Manual Center"})
    lookup = {"Manual Center": "Mo-Fr 09:00-14:00"}
    assert main.opening_hours_for_fixed_point(row, lookup) == "Mo-Fr 09:00-14:00"


def test_opening_hours_for_fixed_point_missing_entry_returns_none(mocker):
    mock_log = mocker.patch("main.log")
    row = pd.Series({"center_id": "9999", "name": "Unknown Center"})

    assert main.opening_hours_for_fixed_point(row, {}) is None
    mock_log.warning.assert_called_once()
