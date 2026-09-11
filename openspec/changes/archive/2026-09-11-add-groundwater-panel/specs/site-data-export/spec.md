## ADDED Requirements

### Requirement: Groundwater export is pre-aggregated monthly

`generate_site.py` SHALL read `groundwater_obs` and write pre-aggregated monthly-mean series
per well and value mode for the groundwater charts. The database SHALL remain read-only and
byte-identical at generate time.

#### Scenario: Monthly means, no stored derivatives

- **WHEN** the groundwater export is written
- **THEN** each exported point is the arithmetic mean of that well/mode/month's stored
  observations
- **THEN** no aggregated value is written back to the database

#### Scenario: Both modes exported where present

- **WHEN** a well has Relativ and Balti observations
- **THEN** the export contains both series, each tagged with its mode

#### Scenario: Months with no observations export as gaps

- **WHEN** a well/mode has zero stored observations in a month
- **THEN** that month carries no point rather than a carried-forward or interpolated value

#### Scenario: Local month bucketing

- **WHEN** observations are bucketed into months
- **THEN** each UTC timestamp is interpreted in the `Europe/Budapest` timezone first, so
  `22:00Z`/`23:00Z` day boundaries land on the correct local day in both CET and CEST

#### Scenario: Lake series shares the groundwater chart's datum

- **WHEN** the groundwater overlay chart's lake-level series is exported
- **THEN** it is expressed in Baltic datum (m.a.f.) using the documented Agárd gauge datum, or
  — if that datum is not available — as an anomaly series relative to its own reference
  period, and the chosen variant is recorded in `docs/known-issues.md`
