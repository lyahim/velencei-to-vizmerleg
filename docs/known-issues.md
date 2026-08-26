# Known Issues

Curated registry of data-quality defects in `output/vizmerleg.db`.

Purpose: machine-readable index for chart annotation. `generate_site.py` reads this file, joins
`charts` column to chart id, renders `display_hu` under affected chart.

Not a duplicate of `EXTRACTION_GUIDE.md` §14. §14 tells extractor how to detect and repair.
This file tells consumer what caveat to show. `ref` column points back to full account.

Chart ids match `docs/climate-charts-plan.md` numbering.

`severity`:
- `blocked` — chart cannot ship correctly until resolved
- `caveat` — chart ships, needs visible note
- `gap` — data absent, chart shows hole
- `handled` — defect known, workaround in query, note optional

Verified 2026-08-25 against DB unless stated.

---

## Registry

| id | scope | years | severity | charts | issue | display_hu | ref |
|---|---|---|---|---|---|---|---|
| `vizhaztartas-1984-mismatch` | `historical_monthly` `vizhaztartas_hozzafolyas` | 1984 | caveat | 1, 4 | Total 514. Components sum 536. Gap 22. Source page not yet re-read. | 1984: a hozzáfolyás összege ellentmond az összetevőinek, forrásellenőrzés alatt. | `import_tracker.md` 1996 tbl16 |
| `vizhaztartas-negative-withdrawal` | `historical_monthly` `vizhaztartas_leer_vk` | 1972, 1985 | caveat | 1, 8 | Derived withdrawal negative. 1972 −4. 1985 −1. Rounding noise or misread. | 1972 és 1985: kerekítési ellentmondás a kivett vízmennyiségben. | `import_tracker.md` 1996 tbl16 |
| `daily-obs-skip-unverified` | `daily_obs` all stations | ≤2006 | caveat | 3, 4 | Tracker rows say `skip / already extracted`. Claim unverified. 2007 carried same claim and was wrong. Phantom day rows plus month-boundary value leaks confirmed there. | A 2007 előtti napi adatok forrásellenőrzése még nem történt meg. | §14 "do NOT trust pre-existing skip" |
| `korakaspuszta-flat-runs` | `daily_obs` `korakaspuszta_vizhozam` | 2005–2007 | blocked | 4 | 2007: ~110 of 365 days out of printed min/max range. 22 consecutive identical November values. Placeholder data, not boundary leak. Needs full re-transcription. | A Kőrakáspuszta vízhozam-sor hosszú szakaszai megbízhatatlanok, ezért kimaradnak. | §14; `import_tracker.md` line ~399, ~453 |
| `daily-obs-month-padding` | `daily_obs` all stations | 2021–2024 | handled | 3, 7 | 31 rows stored per month regardless of month length. Surplus rows NULL. 372 rows/year. Filter `value IS NOT NULL` before aggregate. | — | `docs/climate-charts-plan.md` blocking items |
| `daily-obs-invalid-calendar-day` | `daily_obs` all stations | 2010–2020 | handled | 3, 7 | 401 rows carry an impossible calendar day (Feb 30/31, Apr 31, Jun 31) with a non-NULL value duplicating the last real day of that month. Same 31-rows-per-month padding as `daily-obs-month-padding`, but here the surplus row is a duplicate, not NULL. Found 2026-08-26 building `generate_site.py`. Filter out rows failing calendar validation before any date-indexed aggregate or chart. | — | `generate_site.py` chart_3 |
| `agard-vizallas-gaps` | `daily_obs` `agard_vizallas` | 2008, 2010, 2017 | gap | 3 | 2010: 345 rows, 20 days absent. 2008: 363. 2017: 364. | 2010: 20 nap hiányzik a napi vízállás-sorból. | DB count 2026-08-25 |
| `zamoly-patka-2025-missing` | `daily_obs` `zamoly_vizhozam`, `patka_vizhozam` | 2025 | gap | 4 | 2025 PDF ships two stale 2024 pages. Vendor error. Not inserted. | 2025: a zámolyi és pátkai napi vízhozam hiányzik a forrásdokumentumból. | §14 "2025 doc ships two stale 2024 pages" |
| `kozepes-m3s-null-station` | `monthly_station_obs` `kozepes_m3s` | 2011–2013, 2019, 2022 | blocked | 4 | Rows carry `station_id` NULL. Six stations per month, identities unrecorded. Per-station breakdown impossible for these years. | Egyes években a vízhozam nem bontható állomásokra. | §14 "kozepes_m3s NULL station_id" |
| `annual-climate-sparse` | `annual_climate_summary` | 1994–2025 | gap | 7 | 33 rows. `ice_total_days` 21 NULL. `heat_days_count` 28 NULL. `air_temp_max_celsius` 14 NULL. `evap_longterm_avg_tomm` 31 NULL. `ice_max_thickness_cm` complete. | Jégnapok és hőségnapok csak az évek egy részére állnak rendelkezésre. | DB count 2026-08-25 |
| `monthly-balance-final-null` | `monthly_balance` final cols | 1992–1998 | handled | 1, 2, 8, 12 | Table-9 final columns NULL in 6 of 34 annual rows. Era B has no tbl9. Use `COALESCE(final, adj, raw)`. `_adj`/`_raw` complete. | — | `docs/climate-charts-plan.md` data availability |
| `evaporation-inputs-t-celsius` | `evaporation_inputs` `t_celsius` | 1992–2025 | gap | 11 | 408 rows. 238 NULL. Winter-formula rows only carry `t_celsius`. Backfill candidate: `monthly_station_obs.leghomerseklet`. | A párolgás hőmérséklet-bemenete az adatok kisebb részére áll rendelkezésre. | DB count 2026-08-25 |
| `evap-2025-dec-t-mismatch` | `evaporation_inputs` | 2025 | caveat | 11 | tbl5 December `t_celsius` printed 7.3. tbl4 December Léghő printed 3.5. Printed value confirmed by zoom crop. Inserted as printed per Rule B. Discrepancy unresolved. | 2025 december: a forrás két táblázata eltérő léghőmérsékletet közöl. | `import_tracker.md` 2025 tbl5 |
| `historical-monthly-station-null` | `historical_monthly` all rows | 1929–1996 | caveat | 5, 6 | `station_id` NULL throughout. Series are catchment or lake aggregates, station attribution lost. | Az 1996 előtti sorok nincsenek állomáshoz rendelve. | `docs/climate-charts-plan.md` data availability |
| `extraction-incomplete` | all tables | 1986–2025 | caveat | all | `import_tracker.md` carries ~32 rows not in `done` state. Coverage grows between site regenerations. | Az adatfeldolgozás folyamatban van, egyes évek még hiányoznak. | `import_tracker.md` |

---

## Maintenance

Add row when extraction turn surfaces defect that survives the turn. Rule D NULLs with a tracker
note do not need a row unless a chart shows the hole.

Remove row when defect resolved in DB. Do not keep resolved rows — `EXTRACTION_GUIDE.md` §13/§14
holds the history.

Update `severity` when fix lands. `blocked` → `handled` once query workaround exists.

`display_hu` renders verbatim under chart. Keep one sentence. Hungarian. No jargon, no table names,
no column names — audience is a lay reader, not an extractor. Empty (`—`) suppresses the note.
