"""
chicago_crime.py

Minimal, dependency-free client for the City of Chicago's public crime dataset,
"Crimes - 2001 to Present" (Socrata dataset id ijzp-q8t2), via the SODA/SoQL API.

Why this exists: Chicago's own data-portal connectors (and most off-the-shelf
Chicago-data MCP tools) expose only pre-aggregated "watchlist" totals - one
number per dataset, with no breakdown by crime type. That's not enough to test
a claim like "carjackings are down 76%," because carjacking and robbery are
specific IUCR categories/descriptions inside the raw incident-level data, not
separate top-level metrics anyone has pre-aggregated for you.

This module queries the dataset directly with SoQL ($select/$where/$group),
so you can pull exact monthly or annual counts for any primary_type /
description combination, for any date range.

No API key is required for reasonable, non-bulk use (Socrata open-data apps
are rate-limited but not gated). Get a free app token at
https://data.cityofchicago.org/profile/edit/developer_settings if you plan to
run this a lot, and pass it as X-App-Token.

Standard library only - no pandas/requests dependency, so it runs anywhere.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from typing import Optional

DATASET_ID = "ijzp-q8t2"
BASE_URL = f"https://data.cityofchicago.org/resource/{DATASET_ID}.json"
DATASET_URL = "https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2"


def _soql_string(value: str) -> str:
    """Escape a string literal for SoQL (single quotes doubled)."""
    return "'" + value.replace("'", "''") + "'"


def _run_query(params: dict, app_token: Optional[str] = None) -> list[dict]:
    safe_chars = "(),'*="
    query_string = urllib.parse.urlencode(params, safe=safe_chars)
    url = f"{BASE_URL}?{query_string}"
    headers = {"Accept": "application/json"}
    if app_token:
        headers["X-App-Token"] = app_token
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _date_clause(start: Optional[str], end: Optional[str]) -> list[str]:
    clauses = []
    if start:
        clauses.append(f"date >= '{start}T00:00:00'")
    if end:
        clauses.append(f"date <= '{end}T23:59:59'")
    return clauses


def monthly_counts(
    primary_type: Optional[str] = None,
    description_in: Optional[list[str]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    app_token: Optional[str] = None,
) -> dict:
    """
    Monthly incident counts for a crime type, as {"YYYY-MM": count}.

    primary_type: exact IUCR primary_type, e.g. "ROBBERY".
    description_in: list of exact `description` values to match (OR'd together),
        e.g. ["VEHICULAR HIJACKING", "AGGRAVATED VEHICULAR HIJACKING"] for
        carjacking, which Chicago classifies as a type of robbery, not its own
        primary_type.
    start/end: "YYYY-MM-DD" (inclusive).
    """
    where = []
    if primary_type:
        where.append(f"primary_type = {_soql_string(primary_type)}")
    if description_in:
        desc_clause = " OR ".join(f"description = {_soql_string(d)}" for d in description_in)
        where.append(f"({desc_clause})")
    where += _date_clause(start, end)

    params = {
        "$select": "date_trunc_ym(date) as month, count(*) as cnt",
        "$group": "month",
        "$order": "month",
        "$limit": 1000,
    }
    if where:
        params["$where"] = " AND ".join(where)

    rows = _run_query(params, app_token)
    return {r["month"][:7]: int(r["cnt"]) for r in rows}


def annual_counts(
    primary_type: Optional[str] = None,
    description_in: Optional[list[str]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    app_token: Optional[str] = None,
) -> dict:
    """Same as monthly_counts, but grouped by calendar year -> {"YYYY": count}."""
    where = []
    if primary_type:
        where.append(f"primary_type = {_soql_string(primary_type)}")
    if description_in:
        desc_clause = " OR ".join(f"description = {_soql_string(d)}" for d in description_in)
        where.append(f"({desc_clause})")
    where += _date_clause(start, end)

    params = {
        "$select": "date_extract_y(date) as year, count(*) as cnt",
        "$group": "year",
        "$order": "year",
        "$limit": 1000,
    }
    if where:
        params["$where"] = " AND ".join(where)

    rows = _run_query(params, app_token)
    return {r["year"]: int(r["cnt"]) for r in rows}


def period_counts(
    periods: list[tuple[str, str, str]],
    primary_type: Optional[str] = None,
    description_in: Optional[list[str]] = None,
    app_token: Optional[str] = None,
) -> dict:
    """
    Counts for arbitrary, non-calendar date ranges in one query — e.g. to
    compare "the year before a mayor took office" against "mayoral year 1,"
    "mayoral year 2," etc., instead of being stuck with calendar years.

    periods: list of (label, start, end) tuples, each "YYYY-MM-DD", end exclusive.
        Example: [("pre", "2022-05-15", "2023-05-15"), ("yr1", "2023-05-15", "2024-05-15")]

    Returns {label: count}. Ranges should be contiguous/non-overlapping if you
    want them to partition the data cleanly, but nothing enforces that.
    """
    # Sorted by start date so an ordinary CASE WHEN chain (tested against the
    # live API) assigns each row to the first matching range.
    ordered = sorted(periods, key=lambda p: p[1])
    when_clauses = " ".join(
        f"WHEN date >= '{start}T00:00:00' AND date < '{end}T00:00:00' THEN {_soql_string(label)}"
        for label, start, end in ordered
    )
    case_expr = f"CASE {when_clauses} ELSE {_soql_string('_other')} END as period"

    where = []
    if primary_type:
        where.append(f"primary_type = {_soql_string(primary_type)}")
    if description_in:
        desc_clause = " OR ".join(f"description = {_soql_string(d)}" for d in description_in)
        where.append(f"({desc_clause})")
    earliest = min(p[1] for p in periods)
    latest = max(p[2] for p in periods)
    where.append(f"date >= '{earliest}T00:00:00' AND date < '{latest}T00:00:00'")

    params = {
        "$select": f"{case_expr}, count(*) as cnt",
        "$where": " AND ".join(where),
        "$group": "period",
        "$limit": 1000,
    }
    rows = _run_query(params, app_token)
    return {r["period"]: int(r["cnt"]) for r in rows}


def list_descriptions(primary_type: str, app_token: Optional[str] = None) -> dict:
    """All `description` values under a primary_type, with total counts. Useful
    for finding the exact label a crime sub-type is filed under (e.g. that
    'carjacking' is filed as 'VEHICULAR HIJACKING' under primary_type 'ROBBERY')."""
    params = {
        "$select": "description, count(*) as cnt",
        "$where": f"primary_type = {_soql_string(primary_type)}",
        "$group": "description",
        "$order": "cnt DESC",
        "$limit": 1000,
    }
    rows = _run_query(params, app_token)
    return {r["description"]: int(r["cnt"]) for r in rows}


if __name__ == "__main__":
    # Example: carjackings by year, 2001-present.
    carjacking = annual_counts(
        description_in=["VEHICULAR HIJACKING", "AGGRAVATED VEHICULAR HIJACKING"]
    )
    for year, count in sorted(carjacking.items()):
        print(year, count)

    # Example: arbitrary, non-calendar windows (e.g. comparing against a
    # specific date instead of Jan 1 - useful for "under administration X"
    # claims, which rarely line up with calendar years).
    print()
    print(
        period_counts(
            [
                ("pre_period", "2022-05-15", "2023-05-15"),
                ("year_1", "2023-05-15", "2024-05-15"),
                ("year_2", "2024-05-15", "2025-05-15"),
            ],
            description_in=["VEHICULAR HIJACKING", "AGGRAVATED VEHICULAR HIJACKING"],
        )
    )
