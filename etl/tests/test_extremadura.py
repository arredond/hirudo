"""Tests for regions/extremadura.py — its hand-maintained fixed points."""

import json
import pathlib

from opening_hours import OpeningHours
from regions import extremadura

ETL_DIR = pathlib.Path(__file__).resolve().parent.parent


def test_scrape_fixed_points_loads_hand_maintained_points(mocker, monkeypatch):
    monkeypatch.chdir(ETL_DIR)
    mocker.patch("utils.points.load_opening_hours_fijos", return_value={})

    df = extremadura.scrape_fixed_points()

    assert df["name"].tolist() == [
        "Banco de Sangre de Extremadura",
        "Hospital de Mérida",
    ]
    assert (df["region"] == "Extremadura").all()
    assert df["telefono"].tolist() == ["924 314 686", "924 370 703"]
    assert df[["latitude", "longitude"]].notna().all().all()
    assert df.loc[0, "gmaps_url"] == (
        "https://www.google.com/maps?q=38.921607+-6.306349"
    )


def test_every_fixed_point_has_valid_hand_built_hours():
    lookup = json.loads(
        (ETL_DIR / "utils" / "opening_hours_fijos.json").read_text(encoding="utf-8")
    )

    for name in ["Banco de Sangre de Extremadura", "Hospital de Mérida"]:
        OpeningHours(lookup[name])
