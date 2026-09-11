## Context

The DB is the product; the site generator is its only reader. VRA access patterns are
documented in `docs/vra-api.md` (guest token, `TS/TsShortList`, multi-station requests).
Schema conventions: `daily_obs` uses integer Y/M/D + `station_id` + `source_doc_id`;
`stations.type` has a CHECK constraint limited to
`vizallas/vizhomerseklet/vizhozam/csapadek`; provenance convention established by the VRA
surface-water ingest (doc_id 42/43). Agárd gauge datum is available per year in
`station_metadata_history.nullpont_mBf` (102.62 mBf, 2021–2025 rows verified).

## Goals / Non-Goals

**Goals:**

- Groundwater observations land in `vizmerleg.db` with per-batch provenance and zero
  transformation.
- Charts A (Balti-datum overlay, klima) and B (depth small multiples, adattár) render from
  pre-aggregated monthly JSON.
- Fetch is an operator action; nothing in CI talks to VRA.

**Non-Goals:**

- Rétegvíz wells (code 70), hóvízegyenérték (76), talajnedvesség/talajhő (299/303).
- Extending the lake series beyond the DB (2025 lake data via VRA 818) — the overlay chart
  honestly ends the lake line where DB coverage ends.
- Any stored aggregates — monthly means live only in exported JSON.

## Decisions

### D1 — New tables, not `daily_obs`/`stations` reuse

`groundwater_wells` (registry: `tsz` PK, `name`, `telepules`, `lat`, `lon`, `uzem`) and
`groundwater_obs` (`ts_utc` TEXT ISO-8601 UTC, `well_tsz` FK, `mode` TEXT CHECK
`relativ|balti`, `value` REAL, `source_doc_id` FK, UNIQUE(`ts_utc`,`well_tsz`,`mode`)).

Why not reuse: `stations.type` CHECK blocks a `talajviz` type (SQLite cannot ALTER a CHECK);
`daily_obs` UNIQUE(year,month,day,station_id) cannot hold two value modes per day; well
observations are event-timestamped (irregular pre-2018), not calendar-day gridded like
yearbook dailies.

### D2 — One `documents` row per fetch run

`filename = 'VRA földalatti <fetch-date>'` (UNIQUE per run), `source_type='digital'`,
`year` = fetch year. Each ingest batch is attributed to its own fetch. Alternative — one
permanent row reused across refreshes — rejected: `processed_at` would lie about later
batches, and per-batch provenance is the established convention (doc 42 vs 43).

### D3 — Both value modes stored, never converted

Relativ (cm) and Balti (m.a.f.) both ingested where VRA provides them. Converting between
them would need a per-well reference elevation we do not reliably have (the `Relativ`
reference point semantics per well is unverified) — and the no-derivation rule forbids it
anyway.

### D4 — UTC in, Budapest at export

Observations stored at the exact UTC instant VRA returns. Calendar-month bucketing happens
in `generate_site.py` using `Europe/Budapest` (CEST/`22:00Z` vs CET/`23:00Z` day boundaries
already verified in `docs/vra-api.md`).

### D5 — Chart A lake series via `nullpont_mBf`

Lake level (m.a.f.) = `nullpont_mBf` + vízállás(cm)/100, per-year datum from
`station_metadata_history` (`COALESCE(nullpont_mBf, 102.62)`). Series: `monthly_station_obs`
main-lake monthly mean (`atlag_cm`, station NULL) 1994–2024. Anomaly fallback documented in
the spec is contingency only — datum exists, so not expected to trigger.

### D6 — Fetch script: stdlib-only, 2 API calls, SQL to stdout

`scripts/fetch_groundwater.py`: `urllib` (no new dependency), own guest token, one
`TsShortList` POST per value mode (all 7 `torzsszamList` in one request), raw window
1990-01-01 → today, no `aggregateFilters`. Points without `Adat` skipped. Emits
`INSERT OR IGNORE` block wrapped in `BEGIN;`/`COMMIT;` to stdout (`/tmp` file optional
argv). Operator applies via the established `sqlite3` flow. ~35k–110k rows per mode batch
— single transaction is fine.

### D7 — Two chart ids, two pre-aggregated JSON files

Follows the existing one-file-per-chart pattern: overlay chart (klima) and depth panel
(adattár) each get a monthly-mean JSON with per-well/mode series and the lake series
embedded in the overlay file. Exact ids chosen at implementation to match
`generate_site.py`'s existing naming.

## Risks / Trade-offs

- [Balti mode availability unverified for all wells/full range (only Pákozd+Agárd
  2024–2025 probed)] → fetch task reports per-well/mode point counts; chart A uses wells
  with Balti data; missing wells noted in caption, not silently dropped.
- [`Relativ` reference point per well may be kútfej, not ground] → chart B caption and a
  `docs/known-issues.md` display note state the reference ambiguity; cross-well depth
  comparison discouraged in prose.
- [2018 telemetry switchover changes observation density] → monthly means make the switch
  visually neutral; a display note marks the switchover year on chart B.
- [Agárd-3.szennyvíztelep well monitors a local facility] → kept in the panel (registry is
  fixed and public data), display note flags potential local influence.
- [Token TTL 900 s] → 2 sequential calls per run, no re-fetch logic needed.
- [Refresh drift: wells renamed/moved in VRA] → registry is fixed by `groundwater_wells`;
  fetch fails loudly on unknown törzsszám rather than silently ingesting others.

## Migration Plan

Additive only: two new tables, one `documents` row per fetch, no changes to existing tables.
Rollback: `DROP TABLE groundwater_obs; DROP TABLE groundwater_wells;` + delete the fetch's
`documents` rows; revert generator/template changes and regenerate. Site before ingest of
new fetches simply renders the older coverage.

## Open Questions

- Exact chart-id naming once `generate_site.py`'s existing id scheme is seen at
  implementation time.
- Whether the adattár depth panel also gets the year-range control the klima charts have,
  or stays fixed — decide when wiring `site.js`, does not affect the data layer.
