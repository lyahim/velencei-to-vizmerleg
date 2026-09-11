# groundwater-data Specification

## Purpose

Storage, provenance, and refresh of OVF VRA földalatti (talajvíz) observation series for
lake-adjacent wells inside `output/vizmerleg.db`, kept as a source family separate from
yearbook transcriptions.

## Requirements

### Requirement: Raw observations stored as returned

`groundwater_obs` SHALL store each VRA observation value as received — no rounding, no unit
conversion, no interpolation, no gap filling. Missing observations SHALL simply be absent rows,
never NULL placeholders or derived values.

#### Scenario: Full precision preserved

- **WHEN** VRA returns a talajvízállás value of `109.41` (Balti, m.a.f.)
- **THEN** the stored value is `109.41`, not a rounded or unit-converted variant

#### Scenario: Gaps stay gaps

- **WHEN** a well has no observations for a period
- **THEN** no rows exist for that well and period after ingest

#### Scenario: Timestamps stored in UTC as received

- **WHEN** an observation point arrives with `UTCTime` `2020-05-12T22:00:00Z`
- **THEN** the stored timestamp is that UTC instant, and local-date interpretation happens only
  at export time using the `Europe/Budapest` timezone

---

### Requirement: Two value modes per well

For each observation the table SHALL carry the value mode it was fetched under: `Relativ`
(depth below surface, cm) or `Balti` (elevation above Baltic sea level, m.a.f.). Both modes
SHALL be ingested for every well where VRA provides them.

#### Scenario: Both modes present for a well

- **WHEN** Pákozd (törzsszám 825) has both Relativ and Balti data on a date
- **THEN** both observations are stored, each tagged with its mode

#### Scenario: Mode unavailable for a well

- **WHEN** VRA returns no Balti series for a well
- **THEN** that well has Relativ rows only, and the ingest completes without error

---

### Requirement: Fixed well registry

Ingest SHALL cover exactly the seven lake-adjacent talajvíz wells, identified by VRA törzsszám:
Pákozd 825, Agárd 826, Agárd-2.új házak 143969, Agárd-3.szennyvíztelep 143970, Velence 667,
Kápolnásnyék 582, Börgönd 587. Rétegvíz wells (vmoType 13) are out of scope.

#### Scenario: Only registry wells ingested

- **WHEN** the ingest runs
- **THEN** every stored törzsszám belongs to the seven-well registry

#### Scenario: Well display names preserved

- **WHEN** a well appears in exported data
- **THEN** it carries its Hungarian name as VRA publishes it (e.g. `Agárd-2.új házak`)

---

### Requirement: VRA földalatti is its own source family

Every `groundwater_obs` row SHALL reference a `documents` entry dedicated to the VRA
földalatti ingest, distinct from all yearbook documents and from the VRA surface-water
documents. Source families SHALL never be mixed silently in one ingest.

#### Scenario: Provenance is queryable

- **WHEN** a `groundwater_obs` row is inspected
- **THEN** its source document resolves to the VRA földalatti `documents` entry

#### Scenario: Refresh extends, never overwrites other sources

- **WHEN** the ingest is re-run after new VRA data appears
- **THEN** existing yearbook and VRA surface-water rows are untouched

---

### Requirement: Fetch script emits SQL, never writes the database

`scripts/fetch_groundwater.py` SHALL authenticate against the VRA API, fetch both value modes
for the registry wells, and emit an `INSERT OR IGNORE` SQL block wrapped in `BEGIN;`/`COMMIT;`.
It SHALL NOT open or write `output/vizmerleg.db` itself; applying the block is an operator
action.

#### Scenario: Idempotent re-runs

- **WHEN** the emitted SQL block is applied twice
- **THEN** row counts do not change and no error is raised

#### Scenario: Script run leaves the database untouched

- **WHEN** `fetch_groundwater.py` completes
- **THEN** `output/vizmerleg.db` is byte-identical to before the run

#### Scenario: Token handled per run

- **WHEN** the script runs
- **THEN** it obtains its own guest token and does not require a stored credential
