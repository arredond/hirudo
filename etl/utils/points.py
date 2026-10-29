"""Fixed/mobile point enrichment shared across regions: hand-maintained
lookups (opening hours, appointment and plasma lists) and location overrides.

These lookups live in utils/*.json and are loaded relative to etl/, the Cloud
Run job's working directory.
"""

import json
import logging
from collections.abc import Callable
from collections.abc import Set as AbstractSet
from typing import Any

import pandas as pd
from utils.crawl import crawl

log = logging.getLogger(__name__)


def apply_rows(df: pd.DataFrame, func: Callable[[pd.Series], Any]) -> pd.Series:
    """Row-wise `df.apply(func, axis=1)` for functions that may return None.

    pandas' type hints reject row functions returning None (e.g. `str | None`),
    which most address/place/hours builders do. Same rows and resulting dtype
    as `apply`, and always a Series (even for an empty DataFrame).
    """
    return pd.Series([func(row) for _, row in df.iterrows()], index=df.index)


def opening_hours_for_fixed_point(row, lookup):
    """Look up a fixed point's hand-built OSM opening_hours string.

    Keyed by center_id where available, else by name (for the manual
    non-hospital entries, which have no center_id). Logs a warning and
    returns None for anything missing from the lookup, so it surfaces for a
    manual update rather than silently going unset.
    """
    hours = lookup.get(row.get("center_id")) or lookup.get(row["name"])
    if hours is None:
        log.warning("No opening_hours lookup entry for fixed point: %s", row["name"])
    return hours


def load_opening_hours_fijos() -> dict:
    """Load the hand-built OSM opening_hours lookup for fixed points.

    Shared by every region's fixed points (see opening_hours_for_fixed_point) —
    it's one file keyed by center_id where available, else by name.
    """
    with open("utils/opening_hours_fijos.json", encoding="utf-8") as f:
        return json.load(f)


def add_opening_hours(df: pd.DataFrame) -> pd.DataFrame:
    """Set fixed points' "opening_hours" from the hand-built lookup.

    See load_opening_hours_fijos and opening_hours_for_fixed_point.
    """
    lookup = load_opening_hours_fijos()
    df["opening_hours"] = df.apply(opening_hours_for_fixed_point, lookup=lookup, axis=1)
    return df


def load_cita_previa_fijos() -> set:
    """Load the hand-maintained names of fixed points that need an appointment.

    For sources that don't say so in any scraped text (see flag_appointments).
    """
    with open("utils/cita_previa_fijos.json", encoding="utf-8") as f:
        return set(json.load(f))


def load_plasma_fijos() -> dict:
    """Load the hand-maintained fixed points that take plasma, name -> source URL.

    For regions whose scraped pages don't say which fixed points take plasma,
    but whose official plasma page does (each entry names its source).
    """
    with open("utils/plasma_fijos.json", encoding="utf-8") as f:
        return json.load(f)


def flag_appointments(
    df: pd.DataFrame, names: AbstractSet[str] = frozenset()
) -> pd.DataFrame:
    """Set "cita_previa": whether a point only takes donors by appointment.

    True when a region's scraper already flagged it, when its name is in
    `names`, or when any of its text fields says so (crawl.APPOINTMENT_RE).
    """
    text_cols = [
        col
        for col in ["name", "horario", "observaciones", "informacion_al_donante"]
        if col in df.columns
    ]
    flagged = (
        df[text_cols]
        .apply(lambda col: col.apply(crawl.requires_appointment))
        .any(axis=1)
    )
    flagged |= df["name"].isin(names)
    if "cita_previa" in df.columns:
        flagged |= df["cita_previa"].fillna(False).astype(bool)
    df["cita_previa"] = flagged
    return df


def apply_location_overrides(
    df: pd.DataFrame, overrides: pd.DataFrame, key_columns: list[str]
) -> pd.DataFrame:
    """Overwrite coordinates for points no automatic candidate gets right.

    Each override's "match" is compared against every column in
    key_columns, in order, so a later column's match wins over an earlier
    one's — e.g. Aragón matches its title's town/organization part ("who")
    then the full title, so a recurring organization's stop stays covered
    when its room changes but a specific title can still be pinned on its
    own. Overrides are hand-picked (see utils/*_mobile_locations.json) and
    win over every geocoded candidate.
    """
    if overrides.empty:
        return df
    coords = overrides.set_index("match")[["longitude", "latitude"]]
    for key_column in key_columns:
        matched = df[key_column].isin(coords.index)
        df.loc[matched, ["longitude", "latitude"]] = coords.loc[
            df.loc[matched, key_column]
        ].to_numpy()
    return df
