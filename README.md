# chicago-crime-data-tool

A small, dependency-free Python client for the City of Chicago's public crime
dataset, **["Crimes - 2001 to Present"](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2)**
(Socrata dataset id `ijzp-q8t2`), hosted on the
**[Chicago Data Portal](https://data.cityofchicago.org/)**.

## Why this exists

Most "Chicago crime data" connectors and MCP tools expose only pre-aggregated
totals — one "Incidents" number per dataset, with no breakdown by crime type.
That's not enough to check a claim like *"carjackings are down 76%"*, because
carjacking and robbery are specific categories inside the raw incident-level
data (IUCR `primary_type` / `description`), not separate metrics anyone has
pre-aggregated for you.

This module queries the dataset directly with [SoQL](https://dev.socrata.com/docs/queries/)
(`$select` / `$where` / `$group`), so you can pull exact monthly or annual
counts for any crime type/subtype, for any date range — no BigQuery connector,
no paid API, no dataset mirror required.

## Usage

```python
from chicago_crime import monthly_counts, annual_counts, list_descriptions

# Carjacking is filed under primary_type "ROBBERY", not its own category.
# Find the exact description labels first:
list_descriptions("ROBBERY")
# -> {"ARMED - HANDGUN": 12345, "VEHICULAR HIJACKING": 7472,
#     "AGGRAVATED VEHICULAR HIJACKING": 15610, ...}

# Carjackings by year, full history:
annual_counts(description_in=["VEHICULAR HIJACKING", "AGGRAVATED VEHICULAR HIJACKING"])

# Robberies by month, a specific window:
monthly_counts(primary_type="ROBBERY", start="2023-01-01", end="2023-12-31")
```

Run `python chicago_crime.py` for a worked example (annual carjacking counts,
2001–present).

No API key is required for ordinary use. For heavy use, get a free Socrata app
token at your [developer settings](https://data.cityofchicago.org/profile/edit/developer_settings)
and pass it as `app_token=...`.

## A note on "unable to get local issuer certificate"

If a request fails with a TLS/certificate error, that's almost always a local
Python certificate-bundle problem (common with Anaconda installs on macOS),
not Socrata blocking the request. Try a different Python install (e.g. the
`python3` that ships with macOS, or a fresh venv from python.org/Homebrew)
before concluding the API itself is unreachable.

## Data source & citation

City of Chicago Data Portal, *"Crimes – 2001 to Present"* (`ijzp-q8t2`),
https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2

This project is not affiliated with the City of Chicago. It's a thin client
over their public, open SODA API.

## License

MIT — see [LICENSE](LICENSE).
