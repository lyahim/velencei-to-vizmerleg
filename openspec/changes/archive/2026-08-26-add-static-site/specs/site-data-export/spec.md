## ADDED Requirements

### Requirement: Database is read only at generate time

`generate_site.py` SHALL be the only component that opens `output/vizmerleg.db`. The published site SHALL contain no database access.

#### Scenario: Script produces the site

- **WHEN** user runs `python3 generate_site.py` in the project root
- **THEN** `output/site/` is created or overwritten with pages, assets and JSON data

#### Scenario: No runtime database access

- **WHEN** any page under `output/site/` is loaded in a browser
- **THEN** no request targets `vizmerleg.db` or any database endpoint
- **THEN** all data arrives from `./data/**.json`

#### Scenario: Database is not modified

- **WHEN** `generate_site.py` completes
- **THEN** `output/vizmerleg.db` is byte-identical to before the run

---

### Requirement: Two-tier JSON export

Chart data SHALL be pre-aggregated to exactly what each chart plots. Table data SHALL be exported per DB table and fetched only on demand.

#### Scenario: Chart files are small

- **WHEN** `data/charts/` is written
- **THEN** one file exists per chart id
- **THEN** each file is under 100 KB

#### Scenario: Narrative pages stay light

- **WHEN** `index.html` finishes loading
- **THEN** only the JSON for the charts it displays has been requested

#### Scenario: Large tables load on demand

- **WHEN** `adattar.html` is opened but the `daily_obs` tab is not selected
- **THEN** `data/tables/daily_obs.json` is not requested

---

### Requirement: Query rules are applied at export

Known data-shape rules SHALL be applied in the export query, not in the browser.

#### Scenario: Balance columns fall back

- **WHEN** exporting any `monthly_balance` series
- **THEN** values resolve as `COALESCE(final, adj, raw)`

#### Scenario: Padded daily rows excluded

- **WHEN** aggregating `daily_obs`
- **THEN** rows with `value IS NULL` are excluded before aggregation

---

### Requirement: Coverage matrix reflects processing state, not just presence

`data/coverage.json` SHALL merge per-table/per-year row counts from the database with per-row status from `import_tracker.md`.

#### Scenario: Backlog distinguished from absence

- **WHEN** a year has no rows for a table because its tracker row is `pending`
- **THEN** the matrix marks it as pending, not as absent

#### Scenario: Intentional skips distinguished

- **WHEN** a tracker row is `skip`
- **THEN** the matrix marks that year/table as intentionally not extracted

#### Scenario: Unverified data flagged

- **WHEN** a tracker row is `verify` or `error`
- **THEN** the matrix marks that year/table as unconfirmed

#### Scenario: Tracker parsing is defensive

- **WHEN** a row of `import_tracker.md` cannot be parsed
- **THEN** it is recorded as `unknown`
- **THEN** the export completes without error and without dropping the row

---

### Requirement: Known issues are joined to charts

`generate_site.py` SHALL read `docs/known-issues.md` and attach each row's `display_hu` text to every chart id listed in its `charts` column.

#### Scenario: Chart carries its caveats

- **WHEN** a chart id appears in a registry row's `charts` column
- **THEN** that row's `display_hu` text is available to the page for that chart

#### Scenario: Suppressed notes

- **WHEN** a registry row's `display_hu` is `—`
- **THEN** no note is emitted for that row

---

### Requirement: Output is versioned

Every generated JSON file and page SHALL carry the generate timestamp.

#### Scenario: Data version present

- **WHEN** any file under `data/` is read
- **THEN** it carries a `DATA_VERSION` equal to the generate timestamp

#### Scenario: Pages state their age

- **WHEN** any page is viewed
- **THEN** the generate timestamp is displayed

---

### Requirement: Generated output is not version-controlled

`output/site/` SHALL be excluded from git.

#### Scenario: Clean tree after generate

- **WHEN** `generate_site.py` has run
- **THEN** `git status --short output/` reports no new or modified files
