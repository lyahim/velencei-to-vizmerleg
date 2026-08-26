## Why

`historical_monthly` stores the 1971–1996 water-balance series (`vizhaztartas_*`, 8 variables, `month=0` annual rows only), extracted from tbl16 of `Velencei-tó vízmérleg, 1996.pdf` (doc_id=27, p.26–27, rotated scan).

Three of those variables carry **wrong names**. The source table has two blocks: rows 1–5 hold aggregated terms, rows 6–9 hold their breakdown. Extraction skipped row 6 (`hozzáfolyás`), assuming row 2 (`hozzáfolyás + hozzáf. tározóból`) already covered it. Every subsequent label shifted one position early, and row 9 fell off the table entirely.

Confirmed 1996 mapping (source header read by user; values cross-checked against `import_tracker.md` tbl6/tbl8 notes and `monthly_balance`):

| # | Source row | 1996 | Current DB variable | Status |
|---|---|---|---|---|
| 1 | csapadék | 559 | `vizhaztartas_csapadek` | correct |
| 2 | hozzáfolyás + hozzáf. tározóból | 510 | `vizhaztartas_hozzafolyas` | correct (is a total) |
| 3 | vízpótlás | 0 | `vizhaztartas_vizpotlas` | correct |
| 4 | párolgás | 801 | `vizhaztartas_parologas` | correct |
| 5 | leeresztés + vízkivétel | −248 | `vizhaztartas_leer_vk` | correct |
| 6 | hozzáfolyás | 498 | `vizhaztartas_tarozo` | **misnamed** |
| 7 | hozzáfolyás tározóból | 12 | `vizhaztartas_leeresztes` | **misnamed** |
| 8 | leeresztés | 228 | `vizhaztartas_vizkivetel` | **misnamed** |
| 9 | vízkivétel | 20 | — | **not captured** |
| 11 | negatív elemek | 1049 | — | **not captured** |
| 12 | pozitív elemek | 1069 | — | **not captured** |
| 13 | készletváltozás | +20 | — | **not captured** |

Two independent structural confirmations, both computed against the DB:

- `hozzafolyas = tarozo + leeresztes` holds exactly in 25 of 26 years (only 1984 deviates: 514 vs 536).
- `−leer_vk − vizkivetel` yields a plausible positive value every year, and for 1996 equals **20** — matching `monthly_balance.vizkivetel`, extracted independently from tbl6/tbl8.

**Values in the DB are correct. Only the labels are wrong.** Nothing needs re-reading for rows 1–8; row 9 and rows 11–13 were never extracted.

This blocks charts 1, 4, 8 and 12 of `docs/climate-charts-plan.md` — the plan's "Blocking data-quality items" section records the symptom (1996 column-mapping mismatch) but not the cause. Splicing 1971–1995 onto 1996+ under the current names would mislabel outflow as withdrawal and catchment inflow as reservoir inflow, i.e. the charts would misstate the structure of the water balance precisely at the era boundary.

`EXTRACTION_GUIDE.md` §5 records the same wrong mapping, so any future extraction of this table would repeat the error.

## What Changes

Two phases. Coupled by design: B1 frees the `vizhaztartas_vizkivetel` name that B2 then fills with the real withdrawal series.

**B1 — rename shifted variables** (data migration, no re-reading)

- Chained `UPDATE` on `historical_monthly.variable`, in collision-free order:
  1. `vizhaztartas_tarozo` → `vizhaztartas_vizgyujto`
  2. `vizhaztartas_leeresztes` → `vizhaztartas_tarozo`
  3. `vizhaztartas_vizkivetel` → `vizhaztartas_leeresztes`
- Correct the §5 mapping list in `EXTRACTION_GUIDE.md`; record the shift in §13/§14 (known bad data).
- Note the correction in `import_tracker.md`.

**B2 — extract the four missing rows** (real extraction, Rule A applies)

- Read rows 9, 11, 12, 13 of tbl16 from `Velencei-tó vízmérleg, 1996.pdf` p.26–27 for 1971–1996.
- Insert as `vizhaztartas_vizkivetel`, `vizhaztartas_negativ`, `vizhaztartas_pozitiv`, `vizhaztartas_keszletvaltozas` (~104 values, `month=0`).
- Resolve the 1984 discrepancy (`hozzafolyas` 514 vs `tarozo+leeresztes` 536) and the slightly negative derived withdrawals for 1972 (−4) and 1985 (−1) against the printed page.

## Capabilities

### New Capabilities

- `vizhaztartas-integrity`: the 1971–1996 water-balance series in `historical_monthly` carries labels matching the source table, and stores every data row the source prints.

### Modified Capabilities

_(none — no existing spec covers `historical_monthly`)_

## Impact

- Modified data: `output/vizmerleg.db` → `historical_monthly`, 8 variables renamed/added across 26 annual rows (~208 existing rows touched by B1, ~104 new rows from B2).
- Modified docs: `EXTRACTION_GUIDE.md` (§5 mapping, §13/§14 known-bad-data), `import_tracker.md` (1996 tbl16 row, currently `skip`), `docs/climate-charts-plan.md` (blocking-items section can be closed).
- No script changes. No schema change — `historical_monthly` is key/value by `variable`, so new series need no DDL.
- Unblocks charts 1, 4, 8, 12 for the planned static site.
- `output/vizmerleg_inserts.sql` is a frozen snapshot and is **not** updated (per `AGENTS.md`).

## Risks

- **B1 is destructive and not idempotent.** Running the chained renames twice would shift the names a second time. Mitigation: guard each `UPDATE` on the expected row count, take a DB copy first, verify before `COMMIT`.
- **B2 reads a rotated scan.** Same class of risk as every era-B extraction. Mitigation: standard `render_page.py` flow, `EXTRACTION_GUIDE.md` §4b/§4c; Rule D (doubt → `NULL` + tracker note) applies.
