# Climate Charts Plan

Data-availability audit of `output/vizmerleg.db` plus prioritised chart plan for climate-change effects on Lake Velence.

Status: plan only. Nothing implemented. Audit complete — no need to re-audit DB before resuming.

## Data availability

Audited against `output/vizmerleg.db`.

| Source | Coverage | Notes |
|---|---|---|
| `monthly_balance` | 1994–2024, monthly rows + `month=0` annual row | `_raw`/`_adj` columns complete all 31 years. Final Table-9 columns (`csapadek`, `parologas`, …) populated 1999+ only, plus 1996. Use `COALESCE(final, adj, raw)`. |
| `historical_monthly` `vizhaztartas_*` | 1971–1996, annual only (`month=0`) | 12 variables, complete (corrected + extended 2026-08-25, see `EXTRACTION_GUIDE.md` §14/§15): `vizhaztartas_csapadek`, `_hozzafolyas` (total), `_parologas`, `_vizpotlas`, `_leer_vk`, `_vizgyujto`, `_tarozo`, `_leeresztes`, `_vizkivetel`, `_negativ`, `_pozitiv`, `_keszletvaltozas`. Extends water balance back 25 years; `_keszletvaltozas` gives measured storage change without deriving it from the other terms. |
| `historical_monthly` met/level | `leghom_celsius` 1930–1996, `csapadek_mm` 1931–1996, `vizallas_cm` 1931–1996, `szel_ms` 1929–1996, `vizhom_celsius` 1951–1996, `paranyomas_hpa` 1957–1996 | `station_id` NULL for all rows. `year=0` rows hold long-term normals. |
| `monthly_station_obs` | 1993/1994–2024 | Main lake/meteo series carry `station_id` NULL (`atlag_cm`, `max_cm`, `min_cm`, `leghomerseklet`, `szel_ms`, `napsutes_h`, `paranyomas_hPa`, `a_kad_parologas_mm`, `vizhom_celsius`). Per-station rows exist for precipitation and tributary discharge. |
| `daily_obs` | 2002–2024, 84134 rows | `agard_vizallas` 8404 rows, `agard_vizhomerseklet`, `patkai_tarozo_vizallas`, `zamolyi_tarozo_vizallas`, 7 discharge stations. |
| `annual_climate_summary` | 1994–2024, 30 rows (2004 missing) | Ice days, ice max thickness, heat days, air temp extremes, precip vs long-term normal, evaporation vs normal, closing error. |
| `expedition_flows` | 2010–2024, 1811 points | 209 rows `is_dry=1`, 19 rows `is_estimate=1`. |
| `release_events` | 1993–2025, 1138 rows | 186 rows carry `release_volume_tomm`. |

### Splice validation

`historical_monthly.leghom_celsius` and `monthly_station_obs.leghomerseklet` agree exactly on overlap year 1995 (Jan -0.5, Jul 23.4). Air-temperature series safe to splice at 1996.

### Measured climate signals

Verified by query.

- Evaporation (`parologas`, tómm): 801 (1996) → 1049 (2024). 861 in 1971.
- Catchment inflow (`hozzafolyas`, tómm): 430 (1971), ~500 (1990s) → 128–160 (2019–2022).
- Precipitation (`csapadek`, tómm): flat, high variance. Range 297 (2011) – 1002 (2010).
- Mean water level Agárd: 156.4 cm (2006) → 78.6 cm (2022). Record low daily value 53 cm (2022).
- Max ice thickness: 28 cm (1996) → 4–8 cm (2022–2024).
- Heat days: 36 (2021) → 53 (2024).
- Outflow (`lefolyas`): zero in most years since 2011, except 2010 (1336) and 2016 (169).
- Withdrawal (`vizkivetel`): cut to 0 by 2022–2024.

## Chart plan — Tier 1 (headline)

### 1. Annual water balance, diverging bars, 1971–2024

Inflows above axis: precipitation, catchment inflow, reservoir replenishment. Losses below: evaporation, withdrawal, outflow. Measured storage change overlaid as line.

Source: `historical_monthly` `vizhaztartas_*` 1971–1995 + `monthly_balance` `month=0` 1996–2024.

Rationale: whole story in one frame. Loss side fixed while inflow side collapses. Shows deficit structural, not run of bad years.

### 2. Evaporation vs precipitation with shaded gap, 1971–2024

Two lines + 10-year rolling means. Gap shaded.

Rationale: cleanest climate fingerprint. Precipitation flat and noisy, evaporation monotone rising. Widening gap = mechanism. Readable without hydrology background.

### 3. Daily water level 2002–2024 with operational band

Full daily line, target band shaded. Annotate record low 53 cm (2022) and 2021–2023 trough. Companion bar chart: days per year below operational minimum.

Source: `daily_obs` `station_id='agard_vizallas'`.

## Chart plan — Tier 2 (mechanism and trend)

### 4. Catchment inflow collapse, 1971–2024

Annual `hozzafolyas` bars + trend. Stacked breakdown by tributary from `monthly_station_obs.kozepes_m3s` (`csakvar_vizhozam`, `korakaspuszta_vizhozam`, `patka_vizhozam`, `zamoly_vizhozam`, `kapolnasnyekvizhozam`, `kisfalud_vizhozam`), 1994–2024.

Rationale: inflow fell ~70%, far more than precipitation fell. Non-linearity indicates drier soils and higher upstream evapotranspiration consuming runoff before it reaches lake.

### 5. Month × year anomaly heatmaps vs 1971–2000 normal

Separate panels for precipitation, evaporation, water level.

Rationale: annual totals hide seasonal redistribution. Shows whether spring recharge weakens and summer deficit deepens, which determines annual recovery.

### 6. Warming stripes + annual mean air temperature, 1930–2024

Rationale: near-century local record. Makes causal claim locally instead of by reference to global averages. Splice validated at 1996.

### 7. Thermal regime and ice, dual panel

Panel A: water temperature 1951–2024 plus days >25 °C from `daily_obs.agard_vizhomerseklet` 2002–2024. Panel B: ice days and max ice thickness from `annual_climate_summary` 1994–2024.

Rationale: ice loss most intuitive climate indicator. 28 cm → 4–8 cm needs no explanation. Warmer water feeds back into evaporation, ties to chart 2.

## Chart plan — Tier 3 (impact and adaptation)

### 8. "Lake no longer spills"

Annual `lefolyas` and `vizkivetel` bars, 1971–2024.

Rationale: regime shift from managing surplus to managing scarcity.

### 9. Tributary drying

Share of expedition measurement points dry per year 2010–2024 from `expedition_flows.is_dry`. Per-stream small multiples.

Rationale: direct ecological evidence, independent of balance model.

### 10. Reservoir release dependence

Annual release volumes (tómm) from Pátka/Zámoly, 1993–2025, from `release_events`.

Rationale: quantifies how much of lake survival artificial. Strong closing chart.

### 11. Evaporation driver decomposition

From `evaporation_inputs`: `t_celsius`, `u_ms`, `e_act_mb` vs computed `P_mm`.

Rationale: pre-empts objection that wind, not warming, drives evaporation. Attribution rather than correlation.

Limitation: `t_celsius` populated for only 155 of 372 rows. Check whether gap fillable from `monthly_station_obs.leghomerseklet`.

### 12. Cumulative storage deficit since 1971

Running sum of storage change.

Rationale: converts year-to-year noise into single debt curve. Effective as summary stat tile beside chart 1.

## Blocking data-quality items

### Column-mapping mismatch across 1996 — resolved 2026-08-25

Root cause: tbl16 extraction skipped row 6 (`hozzáfolyás`, catchment inflow), shifting rows 6–9's labels one position early. Fixed via `openspec/changes/fix-vizhaztartas-column-shift` B1: `vizhaztartas_tarozo`→`vizhaztartas_vizgyujto`, `vizhaztartas_leeresztes`→`vizhaztartas_tarozo`, `vizhaztartas_vizkivetel`→`vizhaztartas_leeresztes`. Details in `EXTRACTION_GUIDE.md` §14.

Charts 1, 4, 8, 12 unblocked — variable names now match the source table and `monthly_balance` across the 1996 splice, and `vizhaztartas_keszletvaltozas` (measured storage change, needed by chart 12) has been extracted for all 26 years (B2, `openspec/changes/fix-vizhaztartas-column-shift`).

### `daily_obs` NULL padding

Stores 31 rows per month regardless of month length. 2021–2024 show 372 rows/year for `agard_vizallas`. Filter `value IS NOT NULL` before any daily aggregate.

### `annual_climate_summary` sparse columns

- `ice_total_days` 11 of 30 rows.
- `heat_days_count` 4 of 30.
- `evap_longterm_avg_tomm` 1 of 30.
- `air_temp_max_celsius` 18 of 30.

Chart 7 must handle gaps or backfill from PDFs.

## Next step

Start with charts 1, 2, 3 — carry most of argument. Charts 2 and 3 need no cross-source splicing.

Output medium: decided. All 12 charts ship as a static Hungarian site (`generate_site.py` → `output/site/`,
deployed via GitHub Pages), not standalone per-chart HTML. `generate_site.py` lives in `scripts/`. See openspec change `add-static-site`.
