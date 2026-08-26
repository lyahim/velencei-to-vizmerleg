# vizhaztartas-integrity Specification

## Purpose
TBD - created by archiving change fix-vizhaztartas-column-shift. Update Purpose after archive.
## Requirements
### Requirement: Variable names match the source table

Each `vizhaztartas_*` variable in `historical_monthly` SHALL carry the name of the tbl16 source row whose values it stores.

#### Scenario: Catchment inflow is named for the catchment

- **WHEN** querying `historical_monthly` for `variable='vizhaztartas_vizgyujto'`, `year=1996`, `month=0`
- **THEN** the value is `498`, matching source row 6 (`hozzáfolyás`) and `monthly_balance.hozzafolyas` for 1996

#### Scenario: Reservoir inflow is named for the reservoir

- **WHEN** querying `variable='vizhaztartas_tarozo'`, `year=1996`, `month=0`
- **THEN** the value is `12`, matching source row 7 (`hozzáfolyás tározóból`) and `monthly_balance.hozzafolyas_tarozo` for 1996

#### Scenario: Lake release is named as release

- **WHEN** querying `variable='vizhaztartas_leeresztes'`, `year=1996`, `month=0`
- **THEN** the value is `228`, matching source row 8 (`leeresztés`) and `monthly_balance.lefolyas` for 1996

#### Scenario: Withdrawal holds withdrawal, not release

- **WHEN** querying `variable='vizhaztartas_vizkivetel'`, `year=1996`, `month=0`
- **THEN** the value is `20`, matching source row 9 (`vízkivétel`) and `monthly_balance.vizkivetel` for 1996

---

### Requirement: Inflow total decomposes into its components

`vizhaztartas_hozzafolyas` SHALL be the sum of `vizhaztartas_vizgyujto` and `vizhaztartas_tarozo`, being source row 2 (`hozzáfolyás + hozzáf. tározóból`).

#### Scenario: Decomposition holds across the series

- **WHEN** comparing the three variables for every year 1971–1996
- **THEN** `hozzafolyas = vizgyujto + tarozo` in at least 25 of 26 years
- **THEN** any year that fails is recorded in `import_tracker.md` with the reason

---

### Requirement: Every printed data row is stored

`historical_monthly` SHALL contain a variable for each of the 12 data rows tbl16 prints (rows 1–9 and 11–13; row 10 is a section label, not data).

#### Scenario: Withdrawal series exists

- **WHEN** querying `variable='vizhaztartas_vizkivetel'` for `month=0`
- **THEN** rows exist for the years the source prints a value

#### Scenario: Totals block exists

- **WHEN** querying `variable IN ('vizhaztartas_negativ','vizhaztartas_pozitiv','vizhaztartas_keszletvaltozas')`
- **THEN** rows exist for the years the source prints a value, sourced from rows 11–13

#### Scenario: Storage change is available to charts

- **WHEN** building chart 1 or chart 12 of `docs/climate-charts-plan.md`
- **THEN** measured storage change is read from `vizhaztartas_keszletvaltozas`, not computed from the other balance terms

---

### Requirement: Missing values are NULL, never derived

Values absent or illegible in the source SHALL be stored as `NULL` with a note in `import_tracker.md`.

#### Scenario: Illegible cell

- **WHEN** a cell on the rotated p.26–27 scan cannot be read with confidence
- **THEN** the row is inserted with `value` `NULL`
- **THEN** `import_tracker.md` records which year and variable, and why

#### Scenario: Arithmetic is verification only

- **WHEN** `−vizhaztartas_leer_vk − vizhaztartas_leeresztes` disagrees with the extracted `vizhaztartas_vizkivetel` for a year
- **THEN** the discrepancy is recorded in `import_tracker.md`
- **THEN** the extracted value is not overwritten by the computed one

---

### Requirement: The rename migration is verifiably single-run

The B1 migration SHALL expose a post-condition distinguishing "applied once" from "applied twice".

#### Scenario: Migration applied exactly once

- **WHEN** B1 has completed and B2 has not started
- **THEN** `SELECT COUNT(*) FROM historical_monthly WHERE variable='vizhaztartas_vizkivetel'` returns `0`

#### Scenario: Per-series counts are preserved

- **WHEN** comparing per-variable row counts before and after B1
- **THEN** no series gains or loses rows; only names change

#### Scenario: Extraction refuses to run before the rename

- **WHEN** B2 extraction starts and `vizhaztartas_vizkivetel` returns a non-zero row count
- **THEN** no rows are inserted
- **THEN** the run stops and reports that B1 has not landed

---

### Requirement: The extraction guide teaches the corrected mapping

`EXTRACTION_GUIDE.md` SHALL document the tbl16 source layout and the corrected variable names, and record the historical shift as known-bad data.

#### Scenario: Mapping corrected

- **WHEN** reading `EXTRACTION_GUIDE.md` §5 for tbl16
- **THEN** the listed variable names match the source rows as verified for 1996

#### Scenario: Shift recorded

- **WHEN** reading `EXTRACTION_GUIDE.md` §13/§14
- **THEN** the column shift, its cause, and its correction are described well enough to recognise the same failure elsewhere

#### Scenario: Structure registered

- **WHEN** reading `EXTRACTION_GUIDE.md` §15
- **THEN** tbl16 has an entry recording 13 rows, the two-block layout, year columns, and the rotation
