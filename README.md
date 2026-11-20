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
from chicago_crime import monthly_counts, annual_counts, period_counts, list_descriptions

# Carjacking is filed under primary_type "ROBBERY", not its own category.
# Find the exact description labels first:
list_descriptions("ROBBERY")
# -> {"ARMED - HANDGUN": 12345, "VEHICULAR HIJACKING": 7472,
#     "AGGRAVATED VEHICULAR HIJACKING": 15610, ...}

# Carjackings by year, full history:
annual_counts(description_in=["VEHICULAR HIJACKING", "AGGRAVATED VEHICULAR HIJACKING"])

# Robberies by month, a specific window:
monthly_counts(primary_type="ROBBERY", start="2023-01-01", end="2023-12-31")

# Arbitrary, non-calendar windows - e.g. comparing "the year before an
# official took office" to each year since, instead of calendar years that
# don't line up with the inauguration date:
period_counts(
    [
        ("before", "2022-05-15", "2023-05-15"),
        ("year_1", "2023-05-15", "2024-05-15"),
        ("year_2", "2024-05-15", "2025-05-15"),
    ],
    description_in=["VEHICULAR HIJACKING", "AGGRAVATED VEHICULAR HIJACKING"],
)
```

Run `python chicago_crime.py` for a worked example (annual carjacking counts,
2001–present).

## Do you need an API key?

**No, not for this tool.** The Chicago Data Portal publishes this dataset on
two API versions:

- **SODA2** (`/resource/{id}.json`) — what this module uses. **No
  authentication required** for normal use; confirmed by the portal's own
  "Export → API endpoint" panel and by every query this tool makes.
- **SODA3** (the newer API) — requires an account/authentication. This
  module does not use it.

**When you might still want a free token:** Socrata throttles unauthenticated
requests more aggressively under heavy or concurrent use (the portal's UI
warns about this directly). For occasional/interactive use — the kind this
tool is built for — you won't hit that. If you're going to run this a lot
(many requests per minute, a scheduled job, etc.), get a free app token:

1. Create a free account at [data.cityofchicago.org](https://data.cityofchicago.org/signup).
2. Go to **[your developer settings](https://data.cityofchicago.org/profile/edit/developer_settings)** → "Create New App Token."
3. Pass it to any function here as `app_token="..."`, or set it as the
   `X-App-Token` header yourself if you're querying the API directly.

No token is ever required to just *read* this (or any other) open dataset —
it only raises your personal rate limit.

**Row limit, separately:** the API returns at most 1,000 rows per request by
default (raise it with `$limit`, and paginate with `$offset` for true bulk
pulls). This doesn't affect `monthly_counts`/`annual_counts` here, since
grouped/aggregated queries return one row per month or year — always far
under 1,000 — regardless of how many underlying incidents they summarize.

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

### What the dataset's own documentation says (read this before citing numbers)

Straight from the portal's "About this dataset" page, as of this writing:

- **Excludes the most recent 7 days.** The dataset description states it
  covers "2001 to present, minus the most recent seven days." Any pull that
  includes very recent dates will show an artificially low last-week/month —
  that's missing data, not a real drop.
- **Murders are handled separately** ("with the exception of murders where
  data exists for each victim") — don't expect this dataset alone to cover
  homicide counts cleanly.
- **Data are preliminary.** Per CPD: "crimes may be based upon preliminary
  information... preliminary crime classifications may be changed at a later
  date based upon additional investigation." Recent-month figures can shift
  after the fact.
- **The data owner's own disclaimer explicitly warns against exactly the
  kind of comparison this tool is built to make**: *"the information should
  not be used for comparison purposes over time."* That's CPD's standard
  boilerplate on this dataset, not a claim that any specific analysis here is
  wrong — but it's worth knowing the data owner says this, and worth citing
  it alongside any comparison you publish.
- **Updated daily.** 8.68M+ rows, 22 columns, source system is CPD's CLEAR
  (Citizen Law Enforcement Analysis and Reporting).
- IUCR code reference (what `primary_type`/`description` values exist):
  https://data.cityofchicago.org/Public-Safety/Chicago-Police-Department-Illinois-Uniform-Crime-R/c7ck-438e

### Cross-checking against CPD's own published numbers

CPD separately publishes its own monthly/annual "in review" press releases
(e.g. `chicagopolice.org/wp-content/uploads/2024-in-Review.pdf`) with
official YoY percentages. Querying this dataset independently reproduces
those officially published figures closely (within ~1 percentage point in
every case checked: e.g. CPD's "-17%" robbery/2023→2024 vs. this tool's
-17.5%; CPD's "957 vehicular hijackings... down 26%" vs. this tool's 951).
Useful as a sanity check on any analysis you build with this tool. Worth
noting: those official releases always compare to the *immediately preceding*
year — not to a year further back, which can make an improvement look larger
or smaller depending on which base year gets picked.

## License

MIT — see [LICENSE](LICENSE).
