## 1. B1 — Pre-flight

- [x] 1.1 Copy `output/vizmerleg.db` to `scratchpad/vizmerleg.db.pre-b1` → verify: file exists, byte size matches original
- [x] 1.2 Record baseline counts → verify: `SELECT variable, COUNT(*) FROM historical_monthly WHERE variable LIKE 'vizhaztartas%' GROUP BY variable;` — note the count per series (expected 26 for most, fewer where the source printed gaps). Actual: all 8 series = 26/26, no gaps.
- [x] 1.3 Confirm no script reads the three variables being renamed → verify: `grep -rn "vizhaztartas_tarozo\|vizhaztartas_leeresztes\|vizhaztartas_vizkivetel" --include=*.py .` returns nothing. Confirmed: empty result.

## 2. B1 — Rename migration

- [x] 2.1 Write the transaction to `/tmp/rename_block.sql` with the three `UPDATE`s **in the order given in design.md Decision 2** (order is load-bearing — reordering merges two series)
- [x] 2.2 Apply via `sqlite3 output/vizmerleg.db < /tmp/rename_block.sql` → verify: command exits 0. Confirmed exit=0.
- [x] 2.3 Post-condition A → verify: `SELECT COUNT(*) FROM historical_monthly WHERE variable='vizhaztartas_vizkivetel';` returns **0** (proves B1 ran exactly once, not twice). Confirmed: 0.
- [x] 2.4 Post-condition B → verify: `SELECT variable, COUNT(*) FROM historical_monthly WHERE variable LIKE 'vizhaztartas%' GROUP BY variable;` — counts per series match 1.2's baseline, with `vizhaztartas_vizgyujto` now carrying the old `vizhaztartas_tarozo` count. Confirmed: all 8 series still 26/26.
- [x] 2.5 Spot-check 1996 semantics → verify: `vizhaztartas_vizgyujto`=498, `vizhaztartas_tarozo`=12, `vizhaztartas_leeresztes`=228. Confirmed exact match.

## 3. B1 — Documentation

- [x] 3.1 Correct the tbl16 mapping list in `EXTRACTION_GUIDE.md` §5 — replace the 8-name list with the 12-row source layout (rows 1–9, 11–13) and the corrected variable names
- [x] 3.2 Add the column-shift to `EXTRACTION_GUIDE.md` §13/§14 (known bad data) — what was wrong, when corrected, how to recognise it
- [x] 3.3 Update `import_tracker.md` 1996 tbl16 row: `skip` → reflect the rename, note rows 9/11/12/13 still outstanding (B2)
- [x] 3.4 Update `docs/climate-charts-plan.md` — replace the "Column-mapping mismatch across 1996" blocking item with the resolution; note charts 1/4/8/12 unblocked pending B2

## 4. B2 — Extraction (separate turn, Rule A)

- [x] 4.0 **Precondition — B1 must have landed.** → verify: `SELECT COUNT(*) FROM historical_monthly WHERE variable='vizhaztartas_vizkivetel';` returns **0**. Non-zero means B1 was not applied (the name still holds the release series, 228 for 1996) or was applied twice. **Stop, do not insert** — `idx_hm_unique` covers `(year, month, COALESCE(station_id,''), variable, source_doc_year)`, so `INSERT OR IGNORE` in 4.5 would silently drop the real withdrawal values, leave the release values in place under the wrong name, and still satisfy the 4.6 row count. Confirmed: 0.
- [x] 4.1 Render `Velencei-tó vízmérleg, 1996.pdf` p.26–27 at 300dpi via `render_page.py`, rotated → verify: PNG readable in `scratchpad/1996/`. Done via `render_rot.py` (p26_rot.png, p27_rot.png).
- [x] 4.2 Compare the rendered layout against `EXTRACTION_GUIDE.md` §15 (Rule F) — tbl16 has no registry entry yet; add one after extraction. Layout confirmed: 13 header rows (two blocks + Összesen section), 14/12 year columns per page, label-below-data half-line offset in the main block (not in the Összesen block) — pinned by cross-checking against already-correct rows 1–8, see §15 entry (task 5.5).
- [x] 4.3 Read row 9 (`vízkivétel`) for 1971–1996 — read once, no re-reads (Rule B); doubt → `NULL` + tracker note (Rule D). All 26 cells legible, no NULLs needed.
- [x] 4.4 Read rows 11–13 (`negatív elemek`, `pozitív elemek`, `készletváltozás`) for 1971–1996. All legible; internal identity `pozitiv+negativ=keszletvaltozas` holds exactly for all 26 years (used as an alignment check, not a substitute reading).
- [x] 4.5 Insert as `vizhaztartas_vizkivetel`, `vizhaztartas_negativ`, `vizhaztartas_pozitiv`, `vizhaztartas_keszletvaltozas`, `month=0`, `source_doc_id=27`, `INSERT OR IGNORE` inside `BEGIN;`/`COMMIT;`. 104 rows via `/tmp/insert_block.sql`, exit=0.
- [x] 4.6 Verify insert → `SELECT COUNT(*) FROM historical_monthly WHERE source_doc_id=27 AND variable LIKE 'vizhaztartas%';` — one query, then move on. Confirmed: 312 (208 existing + 104 new).

## 5. B2 — Reconciliation

- [x] 5.1 Cross-check extracted row 9 against `−leer_vk − leeresztes` per year → verify: agreement within rounding; list any year that disagrees. 25/26 years agree exactly; 1985 disagrees by 1 (formula −1, printed 0, confirmed via 4x zoom crop — page prints an unambiguous "0"). See 5.4.
- [x] 5.2 Cross-check 1996 → verify: extracted `vizhaztartas_vizkivetel` = 20, matching `monthly_balance.vizkivetel` for 1996. Confirmed exact match (20.0 = 20.0).
- [x] 5.3 Resolve the 1984 anomaly (`hozzafolyas` 514 vs `vizgyujto + tarozo` 536) against the printed page → if the page is internally inconsistent, `NULL` + tracker note (Rule D), not a guess. Page is consistent — DB had a transcription error (`vizgyujto` 1984 stored as 319, duplicate of 1983; page prints 297). Fixed via UPDATE, user-approved. `297+217=514` now matches exactly.
- [x] 5.4 Resolve 1972 (−4) and 1985 (−1) negative derived withdrawals against the printed page. 1972: DB's `leer_vk` had a sign error (+4, page prints −4) — fixed via UPDATE; formula now matches extracted `vizkivetel`=4 exactly. 1985: page unambiguously prints `vízkivétel`=0 (confirmed 4x zoom); formula predicts −1. Page is internally consistent to within 1 unit of rounding across its own components — inserted 0 as printed (Rule B), not overwritten, per spec.md "Arithmetic is verification only".
- [x] 5.5 Add the tbl16 structure entry to `EXTRACTION_GUIDE.md` §15 (Rule F) — 13 rows, block layout, year columns, rotation
- [x] 5.6 Update `import_tracker.md` tbl16 row to `done` with final row count and any NULL notes
