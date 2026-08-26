## Context

`historical_monthly` is a key/value table: `(year, month, variable, value, station_id, source_doc_id)`. The `vizhaztartas_*` family holds annual (`month=0`) water-balance figures for 1971–1996, all from a single source table — tbl16 of `Velencei-tó vízmérleg, 1996.pdf` (doc_id=27), a rotated scan on p.26–27. Currently marked `skip` in `import_tracker.md` ("already in DB").

The table prints 13 header rows down the left edge, years across. Row 10 is a section label (`Összesen`), not data. Rows 1–5 are aggregated terms; rows 6–9 break two of them down; rows 11–13 are totals.

Only rows 1–8 were captured, and rows 6–8 received the labels belonging to rows 7–9.

## Goals / Non-Goals

**Goals:**
- Variable names in `historical_monthly` match what the source table actually prints.
- Every data row the source prints exists in the DB.
- `EXTRACTION_GUIDE.md` §5 stops teaching the wrong mapping.
- Charts 1, 4, 8, 12 of `docs/climate-charts-plan.md` become safe to build across the 1996 boundary.

**Non-Goals:**
- Re-extracting rows 1–8 — their values are already correct and verified.
- Touching `monthly_balance` — it is correct; it was the reference used to detect the shift.
- Building any chart or site page. Separate change.
- Reconciling `historical_monthly` against source PDFs for any other variable family (`csapadek_mm`, `leghom_celsius`, …). Out of scope, though the same extraction pass may have introduced similar shifts elsewhere.

## Decisions

### Decision 1: Rename in place rather than re-extract

**Chosen:** Three chained `UPDATE`s on `variable`.

**Alternatives considered:**
- Re-extract tbl16 rows 1–8 from the PDF — half a day, and the values are already proven correct by two independent cross-checks.
- Leave the DB alone, correct only at query time in the site's export script — cheap, but the wrong names stay in "the product" and the next reader repeats the mistake.

**Rationale:** `AGENTS.md`: "the database is the product". A labelling bug in the product gets fixed in the product.

### Decision 2: Chained rename order is collision-free

**Chosen:** Execute in exactly this order, inside one transaction:

```sql
BEGIN;
UPDATE historical_monthly SET variable='vizhaztartas_vizgyujto'  WHERE variable='vizhaztartas_tarozo';
UPDATE historical_monthly SET variable='vizhaztartas_tarozo'     WHERE variable='vizhaztartas_leeresztes';
UPDATE historical_monthly SET variable='vizhaztartas_leeresztes' WHERE variable='vizhaztartas_vizkivetel';
COMMIT;
```

Each step frees the name the next step needs, so no temporary placeholder is required. Reordering these statements silently merges two series — the order is load-bearing, not stylistic.

**Rationale:** Minimum statements, no temp names, no data movement.

### Decision 3: New name for the catchment-inflow series is `vizhaztartas_vizgyujto`

**Chosen:** Row 6 prints `hozzáfolyás`, but `vizhaztartas_hozzafolyas` is already taken by row 2 (the total). Naming row 6 after what distinguishes it — inflow from the catchment, as opposed to from the reservoirs — gives `vizhaztartas_vizgyujto`.

**Alternatives considered:**
- `vizhaztartas_hozzafolyas_vizgyujto` — accurate, verbose.
- Rename row 2 to `vizhaztartas_hozzafolyas_ossz` and give row 6 the bare name — closer to the source, but touches a variable that is currently correct and already consumed elsewhere.

**Rationale:** Keeps the correct existing name untouched; the Hungarian term is the one the domain uses.

### Decision 4: Extract row 9, do not derive it

**Chosen:** Read `vízkivétel` off the page in B2.

**Alternatives considered:**
- Compute `−leer_vk − leeresztes` for all 26 years — arithmetically sound, and it is how the shift was detected.

**Rationale:** `AGENTS.md`: "Never derive, interpolate, or back-compute a missing value." The value is printed in the source; there is no reason to reach for arithmetic. Derivation stays a *verification* tool: after B2, the extracted row 9 must reproduce `−leer_vk − leeresztes` within rounding, and any year where it does not is a transcription error in one of the three.

### Decision 5: Extract rows 11–13 in the same pass

**Chosen:** Include `negatív elemek`, `pozitív elemek`, `készletváltozás`.

**Rationale:** The page is already open and the years already aligned; a second pass costs another full extraction turn. `készletváltozás` is directly required by chart 1 (measured storage change overlaid as a line) and chart 12 (cumulative deficit curve) — without it both charts would have to compute storage change from the other terms, which is exactly the derivation Rule B forbids as a verification habit. Rows 11–12 make the balance self-checking at no extra reading cost.

### Decision 6: B1 guarded by row-count assertions, on a DB copy first

**Chosen:** Before `COMMIT`, assert each rename touched the expected number of rows (26 per series, subject to per-year NULL gaps confirmed by a pre-flight count). Take `output/vizmerleg.db` copy into `scratchpad/` first.

**Rationale:** The migration is not idempotent — a second run shifts the names again, and the result is indistinguishable from the current broken state without re-reading the PDF. The guard is cheap relative to that failure mode.

## Risks / Trade-offs

- **Non-idempotent migration** → see Decision 6. Additional mitigation: after B1, `vizhaztartas_vizkivetel` must return **zero** rows until B2 inserts it. That is a clean, checkable post-condition distinguishing "B1 done" from "B1 done twice".
- **Other `vizhaztartas` consumers** → `generate_csapadek_chart.py` and the other two chart scripts do not read `vizhaztartas_*` (verified: they use `csapadek_mm` and `monthly_balance`). No script breaks.
- **1984 anomaly may not resolve** → if the printed page turns out internally inconsistent, Rule D applies: `NULL` plus a tracker note, not a guess.
- **Rows 11–13 may be printed as derived totals with their own rounding** → they may not reconcile to the component rows exactly. Insert as printed (Rule B); note any gap.

## Migration Plan

1. Copy DB to scratchpad.
2. Pre-flight counts per affected variable.
3. B1 transaction with guards.
4. Post-condition: `vizhaztartas_vizkivetel` count = 0.
5. Docs updated in the same turn (`AGENTS.md` requires tracker updates to be part of the insert turn).
6. B2 as a separate turn, own tracker row.

Rollback: restore the scratchpad copy. B1 has no dependants mid-flight.

## Open Questions

- **Does the same shift affect other `historical_monthly` variable families?** The `vizhaztartas_*` block was extracted alongside `csapadek_mm`, `leghom_celsius`, `vizallas_cm`, `szel_ms`, `vizhom_celsius`, `paranyomas_hpa` (tbl10–15, all marked `skip | already in DB` with the same shared row count of 4715). Those are single-variable year×month grids, structurally unlike tbl16's multi-row layout, so the same failure mode is unlikely — but "unlikely" is not "checked". Out of scope here; worth a separate spot-check change.
- **Should `vizhaztartas_hozzafolyas` be renamed to make its "total" nature explicit?** Currently a reader could reasonably assume it is the catchment series. Deferred — see Decision 3 alternatives.
