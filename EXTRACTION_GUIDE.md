# Extraction Process Guide — Velencei-tó PDF Import

Resumption guide for AI agent. Read this when starting a new session or continuing after interruption.

---

## 0. Operating Principle — Hard Rules

### Rule A: One step = one turn

Each tracker row is processed in its own conversation turn. Screenshot only the page(s) needed for that one table. INSERT. Update tracker. Stop.

Do NOT batch multiple tables in one turn. Do NOT screenshot more pages than needed.

### Rule B: Read once, no verification loops

**Read each value once from the screenshot. Do not re-read. Do not verify.**

- If a value is clearly readable → use it.
- If a value cannot be read clearly → store `NULL`, add a note to the tracker, move on.
- Do NOT attempt to verify values by computing mass balances, cross-referencing other tables, or deriving expected values mathematically.
- Trust the source table. Insert what you see.
- If annual totals are readable, store only those for the `month=0` row when monthly values are unclear.

Verification by equation is the #1 cause of token limit hits. It is forbidden.

### Rule D: Doubt = NULL, not analysis

When a value is ambiguous or two readings conflict:
- Store `NULL`.
- Add a brief note in the tracker (e.g. `notes: parologas_adj unclear`).
- Move on immediately.

Do NOT spend tokens trying to resolve the ambiguity through reasoning.

### Rule C: When Unclear, Ask

**Never guess silently. If anything is unclear, ambiguous, or not covered by this guide — stop and ask the user.**

Examples that require asking:
- Table structure differs from what this guide describes (e.g., unexpected column, missing row, unknown label)
- A value's unit is ambiguous (mm vs tómm, m3/s vs m3)
- A station name appears in the PDF that is not in the §6 station mapping
- Data in the PDF contradicts data already in the DB
- A table seems to map to multiple DB tables and the right split is unclear
- A page is unreadable and the missing data would affect correctness
- Any schema question: "should this go in table X or table Y?"

Format for asking:
```
⚠️ UNCLEAR SITUATION — need user decision:
[describe what you found]
[describe what the options are]
[ask which to do]
```

Do not proceed past the unclear step until the user responds. Mark the tracker step `error` with the question in the notes column so the session state is preserved if interrupted.

### Rule F: Structure Cross-Check Against §15 Registry

**After reading a table's row/column layout from the screenshot — before transcribing values — compare it against that table's entry in §15 (Table Structure Registry).**

Check:
- Row count and row labels (same names, same order, same count)
- Column count and column headers (months present, extra/missing summary columns like Átlag/Összeg/Évi összes)
- Station list (same set of named stations, same count)

If the registry has no entry yet for this table (first time it's been extracted), skip the check, extract normally, then **add a new entry to §15** once done (see §15 for the entry format).

If the registry DOES have an entry and the current document's table **differs** (extra row, missing row, renamed row, different station count, reordered columns, etc.) — this is a Rule C "table structure differs" situation: **stop and ask the user** before inserting, using the format in Rule C. Do not silently adapt or guess which historical convention still applies.

This check is a direct comparison against recorded facts (row labels, counts) — it is NOT the same as Rule B's forbidden "verification by equation." Reading structure is fine; recomputing balance equations to check values is not.

After the user resolves a mismatch, update the §15 entry to reflect the new/confirmed structure (note which years use which variant if both are legitimate).

### Rule G: One shell command per tool call — no chaining, no batching

**The user must manually confirm every single tool call in this project.** This means:
- Never chain multiple shell commands together with `&&`, `;`, or pipes into other commands whose sole purpose is to run a second independent action (e.g. `cmd1 && cmd2`, `rm x; python3 y.py`). Each logically distinct action (an install, a script run, a file move, a DB write) is its own separate tool call, run one at a time, waiting for its own result before issuing the next.
- This is distinct from a single command's own necessary internal syntax (e.g. `sqlite3 db < file.sql`, or `python3 script.py arg1 arg2 > out.txt 2>&1` to capture output) — those are one action with output redirection, not two chained actions, and are fine.
- Never issue multiple tool calls in parallel in the same message (established earlier this session) — this rule extends the same principle to *compound commands within a single call*: a chained command bundles multiple actions the user cannot individually approve or deny, which defeats the purpose of manual per-call confirmation just as much as parallel calls would.
- When in doubt about whether a command is "one action" or secretly several, err toward splitting it into separate calls.

---

## 1. Quick Resume Checklist

> **One tracker row = one turn. Complete all steps, then stop.**

```
1. Read import_tracker.md — find first row with status=pending (top of file = highest priority)
2. Note: doc_id, filename, year, step, db_table
3. Screenshot ONLY the page(s) for this one step (check ToC or prior toc step for page number)
4. Read the row/column structure and compare against §15 registry (Rule F) — mismatch = stop and ask
5. Read values once — unclear value = NULL with note, no re-reads, no verification
6. Generate INSERT SQL using templates below
7. Execute: sqlite3 output/vizmerleg.db < /tmp/insert_block.sql
8. Verify row count with SELECT COUNT(*) — one query only
9. Update tracker row: status=done, rows=N, notes=any NULLs, updated=YYYY-MM-DD
10. Update §15 registry entry if this is the first time the table was seen, or if structure changed
11. STOP. Wait for next turn to process the next step.
```

---

## 2. File Locations

| File | Purpose |
|------|---------|
| `output/vizmerleg.db` | SQLite database — primary target |
| `output/vizmerleg_inserts.sql` | Rebuild SQL snapshot — **not updated during extraction; DB is source of truth** |
| `import_tracker.md` | Per-doc per-step status tracker |
| `EXTRACTION_GUIDE.md` | This file |
| `*.pdf` | Source PDFs in project root |

---

## 3. Database Insert Procedure

`output/vizmerleg.db` is the **sole target**. `vizmerleg_inserts.sql` is a historical snapshot — do not update it.

**Execute inserts directly:**
```bash
sqlite3 output/vizmerleg.db "
BEGIN;
INSERT OR IGNORE INTO table_name (...) VALUES (...);
...
COMMIT;"
```

Or write to a temp file and execute:
```bash
sqlite3 output/vizmerleg.db < /tmp/insert_block.sql
```

**Verify after insert:**
```bash
sqlite3 output/vizmerleg.db "SELECT COUNT(*) FROM table_name WHERE source_doc_id=N AND year=YYYY;"
```

---

## 4. PDF Extraction Method

**If the agent model is text-only (cannot view images), skip directly to §4c (Z.AI vision transcription) for any scanned/rasterized table.**

**OCR fails for scanned docs** — use AI vision (document_screenshot):
```python
# Tool: document_screenshot
# path: /home/lyahim/Documents/DEV/velenceito/vizmerleg/<filename>
# pages: "N-M"  (check toc step first to know which pages hold which table)
# dpi: 150
```

**Digital PDFs** (source_type=digital) — try document_parse first:
```python
# Tool: document_parse, ocr=off
# If output empty or garbled, fall back to document_screenshot
```

**Hungarian decimal:** `1,23` → `1.23` in SQL  
**Missing value (dash, dot, "–"):** → `NULL` in SQL  
**Thousands separator (space or period in large numbers):** `185 603` → `185603`

### 4a. Dense Daily-Data Tables — docling (preferred method, added 2010)

For scanned era A/B/C daily tables (tbl10+: ~365 rows × 12 months per station, one table per page) pure visual/vision reading is slow and error-prone — individual digits in a dense rotated grid are genuinely ambiguous at the available scan resolution, and there's no independent cross-check table the way tbl8/tbl9 have each other. [docling](https://github.com/docling-project/docling) (table-structure ML model) reads these grids far more reliably and consistently than manual visual transcription — confirmed on the 2010 doc's tbl10 (Agárd napi vízállás): it correctly resolved a cell that manual reading couldn't (day 16 August), and its per-month computed averages matched the table's own printed `Átlag` row exactly for every month checked. **Use this for any large scanned daily-data table going forward**, not just as a one-off.

**Install (CPU-only, once per environment):**
```bash
python3 -m pip install --user --break-system-packages torch --index-url https://download.pytorch.org/whl/cpu
python3 -m pip install --user --break-system-packages docling --extra-index-url https://download.pytorch.org/whl/cpu
```
Installing plain `pip install docling` pulls the CUDA build of torch (multi-GB, can exhaust disk on a small root partition) — always install CPU torch first so docling reuses it. If disk fills mid-install: `pip cache purge` and retry (docling's own model weights are small, tens of MB, downloaded lazily on first use into `~/.local/lib/python3.12/site-packages/rapidocr/models/` and the HF cache).

**Usage — two scratchpad-turned-project scripts in the repo root:**
- `docling_scan.py <pdf_path> <start_page> <end_page>` — prints each table found in a page range (page number, shape, first row, first column sample) so you can identify which `table_index` on which page holds the daily grid you need, before running the full extraction.
- `docling_daily.py <pdf_path> <page> [table_index=1] [min_plausible]` — extracts a single daily-grid table into `{month: {day: value}}`, prints per-month `n/avg/min/max` (compare `avg` against the table's own printed `Átlag` row as a sanity check), then prints every `YYYY-MM-DD = value` line for building the SQL insert.

Both scripts take the PDF path as their first argument — never hardcode a path inside them, since every year is a different file.

**Known quirks:**
- Day 1 and day 2 sometimes merge into a single table row, with each month's cell containing two space-separated values (e.g. `"135 135"`, `"141 A 141 A"`) instead of two separate rows — `docling_daily.py` already splits this case (an index cell with 2+ day numbers → same count of space-separated values per month cell).
- Quality-flag letters (`A` = interpolated, `P` = a different fill/replacement flag per the source doc's own legend) are glued onto some numbers (e.g. `"159 P"`) — stripped automatically.
- OCR occasionally inserts a stray decimal point into a 3-digit integer (e.g. a water level misread as `"1.54"` instead of `154`) — pass `min_plausible` (e.g. `50` for cm-scale water levels) so the script detects an implausibly-small decimal value and re-parses it as the intended integer. Leave `min_plausible` unset/`None` for tables whose real values ARE small decimals (vízhozam in m³/s, vízhőmérséklet in °C).
- The table's own printed **Minimum/Maximum summary rows are NOT reliable** for cross-checking — they showed a clear column-misalignment artifact (e.g. printed "Maximum" for January reading the same as "Minimum", which is impossible given the printed `Átlag`). The **Átlag (average) row IS reliable** — computing the mean of the extracted daily values and comparing to the table's own printed Átlag per column is the correct validation step, not the Min/Max rows.
- `export_to_dataframe()` requires the `doc` argument in current docling versions (`table.export_to_dataframe(doc)`, not `table.export_to_dataframe()` alone) — the no-arg form is deprecated and warns on every call.
- **Convert ONE page at a time, never a multi-page range for scanning/identification.** A single-page `convert(pdf, page_range=(p,p))` call takes ~3-4 min (mostly one-time model load). A 10-page range (`page_range=(21,30)`) was tried to identify multiple tables' page numbers at once and did not finish in 25+ minutes of wall time despite heavy CPU usage — killed without result. Always loop single-page calls (`docling_scan.py <pdf> N N`, `docling_daily.py <pdf> N ...`) instead of batching a page range, even though it means re-paying the model-load cost per call.

### 4b. Fallback when docling fails: render the page as an image and read it directly (added 2026-07-27)

docling is **not reliable across all documents**, even ones that look "digital" (embedded text, not a flatbed scan). On the 2007 doc's daily tables (tbl10+), docling produced garbled nonsense output (`'fel dol goz ott 11 /VÍ ZÁL LÁS 20 07 Jan -2007 Dec'` repeated across every column) — and RapidOCR fired even though the document is nominally digital, meaning that specific page range is actually a rasterized image embedded in the PDF, not real text. **Test docling on a sample page first; if the output is garbled, stop and switch to this method instead of trying to fix docling.**

**Method — render the page at high DPI and read it with vision:** use `scripts/render_page.py` (takes the PDF path as an argument like the docling scripts — never hardcode a path):
```bash
python3 scripts/render_page.py <pdf_path> <page> [--dpi 300] [--out-dir DIR]
```
This produces `<out-dir>/p<page>-<page>.png` (defaults to cwd if `--out-dir` omitted — always pass the scratchpad dir explicitly). Then use the Read tool on that PNG directly — at 300dpi these dense daily-grid tables render fully legible, far better than docling's OCR pass on the same page. This worked cleanly for every 2007 daily table tried this way (tbl10 Agárd vízállás, tbl11 Pátkai, tbl12 Zámolyi, tbl13 Agárd vízhő).

⚠️ **Landscape scans render sideways — rotate before reading, and always before cropping** (found 2026-08-20 on the 1997 doc; `pdfinfo` shows `Page rot: 270`). `pdftoppm` emits a portrait PNG with the table rotated 90°, so `--crop x0,y0,x1,y1` coordinates are in a rotated frame and are nearly impossible to aim — a first crop attempt landed on the row-label strip instead of the data. Rotate the rendered PNG once, then read and crop the rotated copy in natural landscape coordinates:
```bash
python3 -c "from PIL import Image; Image.open('scratchpad/<year>/p<N>-<NN>.png').rotate(-90, expand=True).save('scratchpad/<year>/p<N>_rot.png')"
```
Full-page legibility improves dramatically too — every 1997 table (incl. the dense 23-row tbl8) read cleanly off the rotated 300dpi PNG with no per-cell cropping needed. **`scripts/render_rot.py` wraps render + rotate + crop into one call** — like the other scripts it takes the PDF path as its first argument, so it works for any year:
```bash
python3 scripts/render_rot.py <pdf_path> <page> --out-dir scratchpad/<year>            # render + rotate, then Read the *_rot.png
python3 scripts/render_rot.py <pdf_path> <page> --out-dir scratchpad/<year> --crop x0,y0,x1,y1 --zoom 4
```
Crop coordinates are in the ROTATED (landscape) frame; both the base render and the rotated copy are cached, so re-running to add a crop costs nothing.

**Always cross-validate the transcription against the table's own printed stats block** (Minimum/Átlag/Maximum/Nap rows at the bottom of every daily table) before trusting it — this catches real transcription errors that a single eyeball pass misses:
1. Compute each month's min/max from your transcribed grid (excluding cells flagged `A`/`P` — those are excluded from the printed stats too).
2. Compare against the printed Minimum/Maximum **value** for that month. A mismatched value (not just a mismatched day) means a real error — re-check by cropping and zooming that exact region of the PNG (see below) rather than re-reading the whole page.
3. **A ±1-day mismatch in the "Nap" (day-of) pointer, with the value itself matching somewhere adjacent, is normal and not an error** — these tables mix a 7:00am daily snapshot (the grid) with continuous-monitoring extremes (the stats block), so the true min/max can fall on the day before/after the snapshot recorded it. Check the stats block's own `Óra:Perc` column: if it's far from 7:00 (e.g. `16:00`, `21:30`), the discrepancy is expected — the instantaneous extreme happened later/earlier the same or an adjacent day. If `Óra:Perc` is ~7:00 and the value still doesn't match anywhere in your transcription, that IS a real error.
4. Also cross-check monthly averages against the already-validated `monthly_station_obs` table (populated from tbl3/tbl7) where available — an independent second source catches errors the table's own stats block might share (e.g. if both were generated from the same flawed upstream process).

**Cropping to verify a specific cell:** when a month's value doesn't match, don't re-read the whole page — crop and zoom just that region with the same script's `--crop`/`--zoom` flags:
```bash
python3 scripts/render_page.py <pdf_path> <page> --crop x0,y0,x1,y1 --zoom 2 --out-dir DIR
```
(full page is ~2480x3509 at 300dpi; re-run `scripts/render_page.py` without `--crop` first if the base PNG isn't already rendered). Then Read the resulting `*_crop_*.png`. **Crop wide enough to include all 12 month columns**, not just the suspect one — a narrow crop that only shows a few columns risks silently mis-mapping which column is which when you re-transcribe, which is exactly the kind of error this technique exists to catch. This caught two real transcription errors this session: a column swap between adjacent months in one row (Ápr/Máj values transposed), and a multi-row column-drift in a flow table where one station's column silently held a neighboring column's values for several rows.

### 4c. Vision-model transcription via Z.AI GLM-4.6V — `vision_read.py` (added 2026-08-14)

**If the agent model is text-only (cannot view PNGs), the "Read the PNG" step of 4b is unavailable** — `document_screenshot` and Read-on-PNG return "Current model does not support images". OCR (docling/document_parse) garbles dense numeric tables anyway (digits transposed, decimals mangled). The replacement for the visual-reading step is `scripts/vision_read.py`: it sends the rendered PNG to the Z.AI GLM-4.6V vision model and returns a table transcription on stdout.

**Built for Z.AI document processing.**

**Usage (after rendering the page with `scripts/render_page.py`, see 4b):**
```bash
python3 scripts/vision_read.py scratchpad/<year>/p<N>-<NN>.png            # default prompt: monthly hydro table → TSV
python3 scripts/vision_read.py <png> "<custom prompt>"                   # custom prompt as 2nd arg
```
Full-page transcription takes ~1-4 min (timeout 420s, 2 retries built in).

**Endpoint details** (full doc: `docs/vision-extraction.md`):
- `https://api.z.ai/api/coding/paas/v4/chat/completions`, model `glm-4.6v` (also `glm-4.5v`).
- Auth: Z.AI Coding Plan key from `~/.pi/agent/auth.json` → `zai` → `.key`. The Coding Plan key ONLY works on the `/api/coding/paas/v4/` path — the standard `/api/paas/v4/` endpoint rejects it with error 1113 "Insufficient balance".
- The request MUST set `"thinking": {"type": "disabled"}` — otherwise reasoning tokens can consume the entire max_tokens budget and content comes back empty (intermittent). Retry on empty content.

**Mandatory validation protocol:**
1. **Two-pass read**: same PNG, two prompts (row-major and column-major). All values must match exactly. Mismatch → crop the suspect region (`scripts/render_page.py --crop`), third read, stop and flag if still unclear.
2. **Never trust station-header names from a single vision read.** GLM-4.6V transcribes digits reliably but misassigns header labels (observed: 7 station names read for 6 data columns, off-by-one shift). Resolve column→station mapping via: a digital-era doc's ToC (e.g. 2024 PDF has a text layer with exact station order), DB magnitude cross-check (station Átlag values vs adjacent years), hydrology logic (release-driven spikes belong on Császár-víz stations below the Zámolyi/Pátkai tározó).
3. **Rules A/B/D still apply** inside each read: read each cell once, write `?` if unreadable → NULL per Rule D, never derive values (Rule B).

**Proven:** 2001 tbl3 (havi középvízhozamok, `Velencei-tó vízmérleg, 2001.pdf` p8) — 6 stations × 13 values, two-pass exact agreement on all 78 values, header misalignment caught and corrected via 2024 ToC + 2004-06 magnitude comparison.

---

## 5. Table → DB Mapping

### tbl1 — Hóeleji vízállás + vízeresztések
**→ `release_events`**

One row per (year, month, station). If no release that month: release fields = NULL, still insert water_level_cm.

```sql
INSERT INTO release_events
  (year, month, station_id, water_level_cm,
   release_period_start, release_period_end,
   release_volume_1e6m3, release_volume_tomm, source_doc_id)
VALUES
  (2024, 1, 'agard_vizallas', 158, NULL, NULL, NULL, NULL, 15),
  (2024, 1, 'patkai_tarozo_vizallas', 446, NULL, NULL, NULL, NULL, 15),
  ...;
```

Release period format in PDF: `"7-31"` → start=7, end=31. `"1-18"` → start=1, end=18.  
Volume in m3 (large number) and tómm (smaller).

`release_events` also has a `note` TEXT column (added 2010) — see §15 tbl1 entry for when to use it (multi-period months, footnotes, Rule D fallback on illegible compound periods).

---

### tbl2 — Vízgyűjtő havi csapadékösszegei
**→ `monthly_station_obs`, variable=`csapadek_mm`**

One row per (year, month, station_id). Rows labeled with station names (see §7 for mapping).  
Annual total row (Összeg/Összesítés): month=0.

```sql
INSERT OR IGNORE INTO monthly_station_obs
  (year, month, station_id, variable, value, source_doc_id)
VALUES
  (2024, 1, 'agard_csapadek', 'csapadek_mm', 62.0, 15),
  (2024, 1, 'dinnyesi_csapadek', 'csapadek_mm', 58.7, 15),
  ...;
```

Some stations may be absent in older PDFs — only insert stations that appear in the table.

---

### tbl3 — Havi középvízhozamok
**→ `monthly_station_obs`, variable=`kozepes_m3s`**

Monthly average flow per tributary station. One row per (year, month, station_id).

```sql
INSERT OR IGNORE INTO monthly_station_obs
  (year, month, station_id, variable, value, source_doc_id)
VALUES
  (2024, 1, 'kapolnasnyekvizhozam', 'kozepes_m3s', 0.012, 15),
  ...;
```

---

### tbl4 — Meteorológiai jellemzők havi közepei
**→ `monthly_station_obs`, station_id=NULL (Agárd meteo)**

Variables from Agárd station — store with station_id=NULL:

| PDF row label | variable key |
|---------------|-------------|
| Léghőmérséklet (°C) | `leghomerseklet` |
| Páranyomás (hPa) | `paranyomas_hPa` |
| Szél (m/s) | `szel_ms` |
| "A" kád párolgás (mm) | `a_kad_parologas_mm` |
| Napsütés (h) | `napsutes_h` |

Note: older docs (era A) may label rows differently. Match by unit/meaning.  
"Zámolyi műszerkert" section (if present) = separate station, store with appropriate station_id if in stations table, else NULL.

```sql
INSERT OR IGNORE INTO monthly_station_obs
  (year, month, station_id, variable, value, source_doc_id)
VALUES
  (2024, 1, NULL, 'leghomerseklet', -2.4, 15),
  (2024, 1, NULL, 'paranyomas_hPa', 4.7, 15),
  (2024, 1, NULL, 'szel_ms', 1.8, 15),
  (2024, 1, NULL, 'a_kad_parologas_mm', NULL, 15),
  (2024, 1, NULL, 'napsutes_h', 37.5, 15),
  ...;
```

---

### tbl5 — Párolgásszámítás
**→ `evaporation_inputs`**

Winter months (Nov–Mar): formula_type='winter', K_nad/A_sum_mm/A_atl_mm = NULL  
Summer months (Apr–Oct): formula_type='summer'

| PDF row | column |
|---------|--------|
| E (mb) / E_sat | `E_sat_mb` |
| e (mb) | `e_act_mb` |
| t (°C) | `t_celsius` |
| U (m/s) | `u_ms` |
| n (days/nap) | `n_days` |
| K (nád) | `K_nad` |
| A (sum) mm | `A_sum_mm` |
| A (átl) mm | `A_atl_mm` |
| P (mm) | `P_mm` |

```sql
INSERT OR IGNORE INTO evaporation_inputs
  (year, month, formula_type, E_sat_mb, e_act_mb, t_celsius, u_ms,
   n_days, K_nad, A_sum_mm, A_atl_mm, P_mm, source_doc_id)
VALUES
  (2024, 4, 'summer', 8.2, 5.1, 12.3, 2.5, 30, 1.13, 85.9, 2.9, 109.0, 15),
  ...;
```

UNIQUE constraint: (year, month) — insert once. If conflict, the record already exists.

---

### tbl6 — Hozzáfolyás számítása
**→ `expedition_flows`**

Expedition flow measurements (not daily continuous). Each row = one measurement event.  
measurement_date format: `YYYY-MM-DD`  
station_id: match from §7 or NULL if station not in registry.

```sql
INSERT OR IGNORE INTO expedition_flows
  (year, measurement_date, station_name, station_id,
   water_level_cm, flow_m3s, is_estimate, is_dry, notes, source_doc_id)
VALUES
  (2024, '2024-03-15', 'Kápolnásnyék', 'kapolnasnyekvizhozam', 12.0, 0.045, 0, 0, '', 15),
  ...;
```

Special markers in PDF:
- "Műszaki becslés" or "(b)" → `is_estimate=1`
- "A meder száraz" or "száraz" → `is_dry=1, flow_m3s=0`

---

### tbl7 — Jellemző vízállások + vízhőmérsékletek
**→ `monthly_station_obs`**

Lake water level characteristics (station_id=NULL for Velencei-tó summary):

| PDF row | variable key | notes |
|---------|-------------|-------|
| Átlag (cm) | `atlag_cm` | monthly average water level |
| Max (cm) | `max_cm` | monthly maximum |
| Min (cm) | `min_cm` | monthly minimum |
| Vízhőmérséklet (°C) | `vizhom_celsius` | |

For Pátkai/Zámolyi tározók (if shown in this table): use respective station_id.

```sql
INSERT OR IGNORE INTO monthly_station_obs
  (year, month, station_id, variable, value, source_doc_id)
VALUES
  (2024, 1, NULL, 'atlag_cm', 141.0, 15),
  (2024, 1, NULL, 'max_cm', 143.0, 15),
  (2024, 1, NULL, 'min_cm', 140.0, 15),
  (2024, 1, NULL, 'vizhom_celsius', 4.0, 15),
  (2024, 1, 'patkai_tarozo_vizallas', 'atlag_cm', 628.0, 15),
  ...;
```

---

### tbl8 — Vízmérleg (nyers + javított)
**→ `monthly_balance` (raw and adj columns)**

Era A (1986-1995): Table 8 was expected to contain ONLY final values (no raw/adj split)  
→ Insert into FINAL columns (csapadek, hozzafolyas, etc.), leave raw/adj as NULL.

⚠️ **This does NOT hold for 1995 — check the actual rows before choosing columns.** 1995's table 8 (titled "A Velencei-tó **éves** vízmérlege") prints the full raw/adj pairing — `Cj`, `Hj`, `Pj`, `VKj`, `Lj`, `DKm javított`, `DKsz javított` — and was mapped to raw/adj like era B, final columns left NULL. Look for any `…j` / `…javított` row label: if one exists, it is a raw/adj table whatever the era says. **Confirmed down to 1990** (1991, 1990 both print 23-row raw/adj layouts; 1990 titled "havi vízmérlegei", 1991 "éves vízmérlege" — title wording varies, row labels decide). Era-A specifics: dash on a `j`-row = carry the raw value (Hj/Pj/VKj Év sums verify only with carries); dash on a raw row = 0; no Vp row + Bevétel label without Vp ⇒ vizpotlas=0; no adj-Záróhiba row ⇒ zarohibia_adj NULL.

Era B/C/D (1996+): Table 8 has two halves: nyers (raw) and javított (adj).  
→ Insert both into raw and adj columns.

Column mapping for era B/C/D tbl8:

| PDF label | raw column | adj column |
|-----------|-----------|-----------|
| Csapadék (C) | csapadek_raw | csapadek_adj |
| Hozzáfolyás (H) | hozzafolyas_raw | hozzafolyas_adj |
| Hozzáfolyás tározóból (Ht) | hozzafolyas_t_raw | hozzafolyas_t_adj |
| Vízpótlás (Vp) | vizpotlas_raw | vizpotlas_adj |
| Párolgás (P) | parologas_raw | parologas_adj |
| Vízkivétel (Vk) | vizkivetel_raw | vizkivetel_adj |
| Lefolyás (L) | lefolyas_raw | lefolyas_adj |
| Készletváltozás mért (ΔK) | keszletv_mert_raw | keszletv_mert_adj |
| Készletváltozás számított | keszletv_szam_raw | keszletv_szam_adj |
| Záróhiba | zarohibia_raw | zarohibia_adj |
| Természetes készletv. | term_keszletv_raw | term_keszletv_adj |

Annual total row (Összeg): month=0.

```sql
INSERT OR IGNORE INTO monthly_balance
  (year, month,
   csapadek_raw, hozzafolyas_raw, hozzafolyas_t_raw, vizpotlas_raw,
   parologas_raw, vizkivetel_raw, lefolyas_raw, keszletv_mert_raw,
   keszletv_szam_raw, zarohibia_raw, term_keszletv_raw,
   csapadek_adj, hozzafolyas_adj, hozzafolyas_t_adj, vizpotlas_adj,
   parologas_adj, vizkivetel_adj, lefolyas_adj, keszletv_mert_adj,
   keszletv_szam_adj, zarohibia_adj, term_keszletv_adj,
   source_doc_id)
VALUES (2024, 1, 26.0, 26.0, 0.0, 0.0, 34.0, 0.0, 0.5, 16.0, -8.5, NULL, -8.5,
        26.0, 26.0, 0.0, 0.0, 33.0, 0.0, 0.5, 18.0, -7.5, NULL, -7.5, 15);
```

**If row already exists** (e.g., from previous partial extraction): use UPDATE instead of INSERT:
```sql
UPDATE monthly_balance SET
  csapadek_raw=26.0, ...
WHERE year=2024 AND month=1;
```

---

### tbl9 — Végleges vízmérleg (era B/C/D) OR Geometriai jellemzők
**→ `monthly_balance` (final columns) OR SKIP**

**If tbl9 = "végleges vízmérleg"** (era C/D: 2002+):

| PDF label | column |
|-----------|--------|
| Csapadék (C) | csapadek |
| Hozzáfolyás (H) | hozzafolyas |
| Hozzáfolyás tározóból (Ht) | hozzafolyas_tarozo |
| Külső vízpótlás | kulso_vizpotlas |
| Párolgás (P) | parologas |
| Vízkivétel (Vk) | vizkivetel |
| Lefolyás (L) | lefolyas |
| Mért készletváltozás | keszletv_mert |
| Természetes készletv. | term_keszletv |

**keszletv_mert** = DKm_final from tbl9 "Mért vízkészletváltozás" row — authoritative source. Can differ from `keszletv_mert_raw` (e.g. 2021 Feb: raw=40, tbl9=30). Always use tbl9 value.

**term_keszletv** = DKm_final − Ht_final = "Természetes készkletváltozás" row in tbl9. Natural lake stock change excluding reservoir contributions.

**Annual keszletv_mert** (month=0): use tbl9 annual Évi összes — NOT the sum of monthly keszletv_mert_raw (can differ by a few tómm due to measurement method).

**Vizkivetel (Vk):** If non-zero in annual row, include in annual INSERT. Monthly Vk: use tbl8 monthly Vk row; store 0 if not shown.

```sql
-- If monthly_balance row already exists from tbl8, UPDATE the final cols:
UPDATE monthly_balance SET
  csapadek=26.0, hozzafolyas=26.0, hozzafolyas_tarozo=0.0,
  kulso_vizpotlas=0.0, parologas=33.0, vizkivetel=0.0,
  lefolyas=0.5, keszletv_mert=18.0, term_keszletv=-7.5
WHERE year=2024 AND month=1;

-- If inserting fresh (no tbl8 yet or combined):
INSERT OR IGNORE INTO monthly_balance
  (year, month, csapadek, hozzafolyas, hozzafolyas_tarozo,
   kulso_vizpotlas, parologas, vizkivetel, lefolyas,
   keszletv_mert, term_keszletv, source_doc_id)
VALUES (2024, 1, 26.0, 26.0, 0.0, 0.0, 33.0, 0.0, 0.5, 18.0, -7.5, 15);
```

**If tbl9 = "geometriai jellemzők"** (era B: 1996–2001): **SKIP** — area/volume lookup curve, no DB table, not time-series data.

---

### tbl10–16 / tbl10+ — Historical series (era B) OR Daily data (era C/D)

**Era B (1996–2001): Historical series → `historical_monthly`**

Check first: `SELECT COUNT(*) FROM historical_monthly WHERE source_doc_id=<doc_id>;`  
If > 0 → skip all historical tables for this doc (already in DB).

If not yet in DB, insert using:

| Series | station_id | variable |
|--------|-----------|---------|
| Tbl10: havi közepes vízállás | NULL | `vizallas_cm` |
| Tbl11: havi csapadékösszeg | NULL | `csapadek_mm` |
| Tbl12: havi léghőmérséklet Agárd | NULL | `leghom_celsius` |
| Tbl13: havi vízhőmérséklet | NULL | `vizhom_celsius` |
| Tbl14: havi szélsebesség | NULL | `szel_ms` |
| Tbl15: havi páranyomás | NULL | `paranyomas_hpa` |
| Tbl16: vízháztartási jellemzők | NULL | `vizhaztartas_*` |

Tbl16 source layout — 13 header rows, two blocks (rows 1–5 aggregated terms, rows 6–9 their
breakdown, row 10 `Összesen` is a section label not data, rows 11–13 totals):

| Row | Source label | vizhaztartas variable |
|-----|-------------|------------------------|
| 1 | csapadék | `vizhaztartas_csapadek` |
| 2 | hozzáfolyás + hozzáf. tározóból | `vizhaztartas_hozzafolyas` (total, = row 6 + row 7) |
| 3 | vízpótlás | `vizhaztartas_vizpotlas` |
| 4 | párolgás | `vizhaztartas_parologas` |
| 5 | leeresztés + vízkivétel | `vizhaztartas_leer_vk` |
| 6 | hozzáfolyás | `vizhaztartas_vizgyujto` (catchment inflow) |
| 7 | hozzáfolyás tározóból | `vizhaztartas_tarozo` (reservoir inflow) |
| 8 | leeresztés | `vizhaztartas_leeresztes` (lake release) |
| 9 | vízkivétel | `vizhaztartas_vizkivetel` (withdrawal) |
| 10 | Összesen | — (section label, not data) |
| 11 | negatív elemek | `vizhaztartas_negativ` |
| 12 | pozitív elemek | `vizhaztartas_pozitiv` |
| 13 | készletváltozás | `vizhaztartas_keszletvaltozas` |

Row 6's name is not the bare `vizhaztartas_hozzafolyas` — that name is already taken by row 2's
total. See §13/§14 for the historical column-shift this corrects.

```sql
INSERT OR IGNORE INTO historical_monthly
  (year, month, station_id, variable, value, source_doc_year, source_doc_id)
VALUES (1931, 1, NULL, 'vizallas_cm', 160, 1996, 27);
```

source_doc_year = year of the PDF document containing this historical table (NOT the data year).

**Era C/D (2002+) + 1989 appendix: Daily data → `daily_obs`**

Check first: `SELECT COUNT(*) FROM daily_obs WHERE source_doc_id=<doc_id>;`  
If > 0 → skip all daily tables for this doc.

1989 exception: daily data lives in the appendix station sheets (p13–p20), not numbered
tables — same station mapping, `source_doc_id=20`, values are computer-printout daily grids
(7:00 obs). See `import_tracker.md` 1989 section, `docs/daily-obs-pre-2002.md`.

| PDF table | station_id |
|-----------|-----------|
| Velencei-tó vízállásai | `agard_vizallas` |
| Pátkai tározó vízállásai | `patkai_tarozo_vizallas` |
| Zámolyi tározó vízállásai | `zamolyi_tarozo_vizallas` |
| Vízhőmérsékletek | `agard_vizhomerseklet` |
| Vereb-Pázmándi / Forna-puszta | `fornapuszta_vizhozam` |
| Kaisár-víz Kőrakáspuszta | `korakaspuszta_vizhozam` |
| Császár-víz Kisfalud | `kisfalud_vizhozam` |
| Császár-víz Csákvár | `csakvar_vizhozam` |
| Burján víz Zámoly | `zamoly_vizhozam` |
| Rovákja-patak Pátka | `patka_vizhozam` |

```sql
INSERT OR IGNORE INTO daily_obs
  (year, month, day, station_id, value, source_doc_id)
VALUES (2006, 1, 1, 'agard_vizallas', 140.0, 37);
```

**Scanned daily tables are large** (~365 rows × N stations). Process page by page; update tracker rows=running total after each page.

---

### text_annual — Annual summary from text body
**→ `annual_climate_summary`**

Extract from narrative text (Bevezetés / Hidrológiai viszonyok section):

| Text mention | column |
|-------------|--------|
| Jégborítás / jég összesen N nap | `ice_total_days` |
| ebből partjég | `ice_shore_days` |
| szakaszos | `ice_intermittent_days` |
| összefüggő | `ice_solid_days` |
| max. jégvastagság X cm (dátum) | `ice_max_thickness_cm`, `ice_max_thickness_date` |
| Hőségnap N nap | `heat_days_count` |
| Léghőmérséklet min X°C (dátum) | `air_temp_min_celsius`, `air_temp_min_date` |
| Léghőmérséklet max X°C (dátum) | `air_temp_max_celsius`, `air_temp_max_date` |
| Csapadék sokévi átlag X mm | `precip_longterm_avg_mm` |
| Csapadék tény. X mm | `precip_actual_mm` |
| Csapadék % | `precip_pct_of_avg` |
| Párolgás sokévi átlag X tómm | `evap_longterm_avg_tomm` |
| Párolgás tény. X tómm | `evap_actual_tomm` |
| Párolgás % | `evap_pct_of_avg` |
| Záróhiba éves X mm | `closing_error_annual_mm` |
| Záróhiba min X mm (hónap) | `closing_error_min_mm`, `closing_error_min_month` |
| Záróhiba max X mm (hónap) | `closing_error_max_mm`, `closing_error_max_month` |

Not all fields appear in every document. Use NULL for missing.  
Date format in PDF: `"február 14."` → `"1996-02-14"`

UNIQUE: (year) — one row per year.

⚠️ **`hó` (snow) is not `jég` (ice) — the narrative discusses both, in adjacent paragraphs, with similar phrasing.** `hótakaró` / `hóvastagság` (snow-cover days, snow depth) belong to NO column in this table; only `jég` / `jégvastagság` sentences feed `ice_*`. Confirmed 1996: p2 says 61 days of snow cover and 37 cm max snow depth, p3 says max ice thickness 28 cm on Feb 16 — only the latter pair is `ice_max_thickness_cm`/`_date`. An earlier version of the example below had the snow numbers in the ice fields; the DB row was corrected 2026-08-20.

⚠️ **`ice_total_days` is usually NULL in these documents.** Ice spells routinely start in December and end the following February, so a calendar-year total is rarely stated; do not sum or apportion the spells yourself (Rule B). Only fill it when the text gives an explicit "X napig" figure for the report's own year.

**precip_actual_mm = the lake figure, not the catchment figure.** These reports state both ("a vízgyűjtőre hulló csapadék X mm" vs the tbl2 summary row "(1.-4.) A Velencei-tóra hulló csapadék átlaga"); the balance's own Csapadék row uses the lake one, so that is what goes in the column — consistent across 1996 (559 lake / 600 catchment), 1997 (356 / 408), 1998 (663 / 673). Keep the catchment figure in the tracker note.

```sql
-- 1996, as actually stored (doc_id 27):
INSERT OR IGNORE INTO annual_climate_summary
  (year, ice_total_days, ice_solid_days, ice_max_thickness_cm, ice_max_thickness_date,
   precip_longterm_avg_mm, precip_actual_mm, precip_pct_of_avg,
   evap_actual_tomm, closing_error_annual_mm, source_doc_id)
VALUES (1996, NULL, NULL, 28.0, '1996-02-16', 561.0, 559.0, 99.6, 801.0, -65.0, 27);
```

---

## 6. Station ID Reference

### Precipitation (csapadek)
| PDF name | station_id |
|----------|-----------|
| Agárd | `agard_csapadek` |
| Dinnyés | `dinnyesi_csapadek` |
| Gánt | `gant_csapadek` |
| Kápolnásnyék | `kapolnasnyekcsapadek` |
| Lovasberény | `lovasbereny_csapadek` |
| Pákozd | `pakozd_csapadek` |
| Pátka (141129) | `patka_csapadek` |
| Pázmánd | `pazmand_csapadek` |
| Sukoró | `sukoro_csapadek` |
| Székesfehérvár | `szekesfehervar_csapadek` |
| Velence | `velence_csapadek` |
| Velencefürdő | `velencefurdo_csapadek` |
| Zámoly | `zamoly_csapadek` |
| Agárd (meteo) | `agard_meteo` |

### Water levels / reservoirs (vizallas)
| PDF name | station_id |
|----------|-----------|
| Velencei-tó / Agárd | `agard_vizallas` |
| Pátkai tározó | `patkai_tarozo_vizallas` |
| Zámolyi tározó | `zamolyi_tarozo_vizallas` |

### Water temperature
| PDF name | station_id |
|----------|-----------|
| Agárd (vízhőmérséklet) | `agard_vizhomerseklet` |

### Flow stations (vizhozam / expedition)
| PDF name | station_id |
|----------|-----------|
| Agárdi-árok | `agardi_arok_exp` |
| Bella-patak | `bella_patak_exp` |
| Csontréti-patak | `csontreti_patak_exp` |
| Császár-víz (Zámoly-tározó alvíz) | `csaszar_viz_exp` |
| Csákvár / Császár-víz | `csakvar_vizhozam` |
| Gárdonyi-víz | `gardonyi_viz_exp` |
| Forna-puszta / Vereb-Pázmándi | `fornapuszta_vizhozam` |
| Kápolnásnyék | `kapolnasnyekvizhozam` |
| Kisfalud-puszta / Cinca-patak | `kisfalud_vizhozam` |
| Kőrakáspuszta / Csukás-ér | `korakaspuszta_vizhozam` |
| Névtelen-árok (Pákozd) | `nevtelen_arok_exp` |
| Pátka / Rovákja-patak | `patka_vizhozam` |
| Pátkai Szivárgó (Cs.víz alatt) | `patkai_szivargo_csaszarviz` |
| Pátkai Szivárgó (gátőrház) | `patkai_szivargo_gatoorhaz` |
| Pátkai Szivárgó (kábelgát) | `patkai_szivargo_kabelgat` |
| Sukorói-ér | `sukoroi_er_exp` |
| Zámoly / Burján-víz | `zamoly_vizhozam` |

**Station not in registry:** use `station_id=NULL`, preserve original name in `station_name` column.

**Find station_id from DB:**
```bash
sqlite3 output/vizmerleg.db "SELECT id, name FROM stations WHERE name LIKE '%<keyword>%';"
```

---

## 7. Data Formatting Rules

| Rule | Example |
|------|---------|
| Hungarian decimal comma | `1,23` → `1.23` |
| Thousands separator | `185 603` → `185603` |
| Missing value (dash, em-dash, dot) | `–`, `-`, `·` → `NULL` |
| Annual total row | "Összeg" / "Évi összeg" → `month=0` |
| Negative value | `-16` stays `-16` |
| Release period "X-Y" | `"7-31"` → `start=7, end=31` |
| Date `"február 14."` | → `'YYYY-02-14'` (infer year from doc) |
| Month number from column | Jan=1, Feb=2, ..., Dec=12 |
| is_estimate | "Műszaki becslés", "(b)" → `1` else `0` |
| is_dry | "száraz", "A meder száraz" → `1` else `0` |

---

## 8. Handling "verify" Items

Some docs already have partial data (status=verify in tracker). Before inserting:

```bash
# Check what's there:
sqlite3 output/vizmerleg.db "SELECT * FROM monthly_balance WHERE source_doc_id=<id> ORDER BY month;"
```

Strategy:
- If raw/adj cols are NULL but data is available → UPDATE to fill them
- If final cols are NULL → UPDATE to fill  
- If row missing (e.g., tbl8 only has month=0 but not months 1-12) → INSERT missing rows
- If values differ from what PDF shows → investigate; if PDF is source of truth, UPDATE

For `monthly_balance` verify with existing data:
```sql
-- Add monthly breakdown (month=1-12) if only annual (month=0) exists:
INSERT OR IGNORE INTO monthly_balance (year, month, ..., source_doc_id) VALUES (...);
-- OR update fields on existing row:
UPDATE monthly_balance SET csapadek_raw=X, ... WHERE year=Y AND month=M;
```

---

## 9. Tracker Update Procedure

After completing a step, update the tracker row in `import_tracker.md`:

```
| tbl2 | havi csapadékösszegek | monthly_station_obs | done | 156 | 2026-07-10 |
```

Update fields:
- `status`: `pending` → `done` (or `error`, `skip`, `verify`)
- `rows_in_db`: actual count from DB query
- `updated`: today's date (YYYY-MM-DD)
- `notes`: add any issue or anomaly found

**For `error` status:** add full description in notes column. Example:
```
| tbl5 | párolgásszámítás | evaporation_inputs | error | 0 | 2026-07-10 | page 11 unreadable, OCR failed, vision shows corrupt scan |
```

After completing ALL steps of a doc, check:
```bash
sqlite3 output/vizmerleg.db "SELECT COUNT(*) FROM release_events WHERE source_doc_id=<id>;"
# etc for each table
```

---

## 10. Skipped Data (Do Not Extract)

| Data type | Reason |
|-----------|--------|
| tbl9 geometriai jellemzők (era B, 1996-2001) | Static physical lookup curve (area vs water level). Not time-series. No DB table. |
| In-text multi-year summary tables (e.g. 2006 text shows 1997-2006 balance) | Duplicate — same data will be extracted from each year's own PDF |
| Chart/diagram pages | Visual only, data already in tables |

---

## 11. Era Quick Reference

| era | years | tbl count | daily embedded | historical series |
|-----|-------|-----------|---------------|------------------|
| A | 1986–1995 | 8 (exception: 1991 has 12 — adds tbl9–12 tározó mérlegek/párolgás szimuláció) | no — **exception: 1989 appendix daily sheets** | no |
| B | 1996–2001 | ~16 | no | yes (tbl10-16) |
| C | 2002–2010 | ~19 | yes (tbl10+) | no |
| D | 2007–2024 digital | ~19 | yes (tbl10+) | no |
| E | 2025– | 19 | yes (tbl10–18) | no |

Era A tbl8: only has final values (no raw/adj split) → insert into final columns only.
Exception: 1989, 1990 print era-B-style 23-row raw/adj tbl8 (see §15).
Era B tbl9: geometric = skip. Era C/D/E tbl9: végleges vízmérleg = monthly_balance final cols.

Era A/B "daily embedded: no" — true for every doc checked except **1989** (found 2026-08-26:
"Vízállás, vízhozam és vízhőmérséklet évi összesítő táblázatok" appendix, p13–p20, 8 station
sheets, computer printouts, 7:00 obs; user decision: extract → `daily_obs` with era-C
station_ids; 1990's MELLÉKLETEK heading was empty). Check each doc's ToC/appendix before
assuming absence — era-A docs vary. For remaining era A/B docs daily lake level otherwise
exists only as plotted curve under ÁBRÁK (2001 p18 `5. ábra`, 1995 p19 `6. ábra`) — figure,
not table. Digitization feasibility + blockers: `docs/daily-obs-pre-2002.md`.

Era E quirks (2025+):
- Tables renumbered. Doc→canonical: 1→tbl1, 2→tbl7, 3→tbl3, 4→tbl6-calc, 5→tbl2, 6→tbl4,
  7→tbl5, 8→tbl8, 9→tbl9, 10–18→tbl10+, 19→expedition_flows source (was tbl20 in era D).
- PDF is digital but doc tbl1–9 are **embedded images, no text layer** → §4b/§4c render+read.
  Doc tbl10–19 have a normal text layer.
- Tracker uses canonical step names; doc table number + page live in the notes column.

---

## 12. Common Issues

**OCR returns empty on scanned PDF:**
→ Use document_screenshot instead. AI vision can read scanned Hungarian text.

**Table number differs from expected:**
→ Always check toc step first. Table numbers shifted in some years.

**Station not found in §7 mapping:**
→ Check: `sqlite3 output/vizmerleg.db "SELECT id, name FROM stations;"`
→ If not there, use station_id=NULL with full name in station_name.

**Row already exists (UNIQUE constraint violation):**
→ `INSERT OR IGNORE` silently skips. To UPDATE: use UPDATE statement.
→ For expedition_flows: check for duplicate date+station combinations before inserting.

**Scanned PDF page too dark/blurry:**
→ Increase dpi: use dpi=200 or 250 in document_screenshot.

**Value in different unit than expected:**
→ Check header row carefully. Some older docs use mm instead of tómm for balance.
→ Do NOT convert — insert as-is (exact original value).

---

## 13. Pre-existing Data Repair Patterns (Digital Years 2021–2022)

Some digital years were partially extracted in an earlier session. Before inserting, check what exists and apply repairs.

### tbl3 (kozepes_m3s with NULL station_id)
```sql
-- Check:
SELECT COUNT(*) FROM monthly_station_obs
  WHERE source_doc_id=X AND variable='kozepes_m3s' AND station_id IS NULL;
-- If > 0: delete, then insert clean rows with station_ids:
DELETE FROM monthly_station_obs
  WHERE source_doc_id=X AND variable='kozepes_m3s' AND station_id IS NULL;
```

### tbl4 (meteo NULL station_id duplication)
```sql
-- If pre-existing rows exist (shows 25 instead of 13 per variable):
DELETE FROM monthly_station_obs WHERE source_doc_id=X AND station_id IS NULL
  AND variable IN ('leghomerseklet','paranyomas_hPa','szel_ms','a_kad_parologas_mm','napsutes_h');
-- Then reinsert clean 60 rows.
```

### tbl5 (7 summer-only rows)
```sql
-- Check:
SELECT COUNT(*) FROM evaporation_inputs WHERE source_doc_id=X;  -- 7 = summer only
-- UPDATE to add missing A_atl_mm to existing summer rows:
UPDATE evaporation_inputs SET A_atl_mm=2.4 WHERE source_doc_id=X AND month=4;
-- ... repeat for months 5–10
-- INSERT 5 winter rows (months 1,2,3,11,12):
INSERT INTO evaporation_inputs
  (year,month,formula_type,E_sat_mb,e_act_mb,t_celsius,u_ms,n_days,P_mm,source_doc_id)
VALUES (YYYY,1,'winter',E,e,t,u,n,P,X), ...;
```

### tbl7 (NULL station_id water level rows)
See repair pattern in §5 tbl7 section.

### tbl8+9 (monthly_balance with partial cols)
```sql
-- Check which cols are NULL:
SELECT month,keszletv_mert,keszletv_mert_adj,zarohibia_adj
  FROM monthly_balance WHERE year=YYYY ORDER BY month;
-- Add missing cols via UPDATE (12 months individually):
UPDATE monthly_balance SET
  keszletv_mert=<tbl9_DKm>, keszletv_mert_adj=<tbl9_DKm>, keszletv_szam_adj=<tbl9_DKm>,
  zarohibia_adj=0, term_keszletv_adj=<tbl9_DKt>
WHERE year=YYYY AND month=M;
-- INSERT annual row:
INSERT OR IGNORE INTO monthly_balance (year,month,...,source_doc_id) VALUES (YYYY,0,...,X);
```

---

## 14. Known Data Quality Issues

### daily_obs — do NOT trust pre-existing "skip | already extracted" tracker notes without checking (found 2026-07-27, 2007)

Several tracker rows for `tbl10+`/daily_obs across years say `skip | already extracted` from before this project's current extraction effort. **2007's row said this and was wrong.** On inspection (prompted by the user directly asking "was this really checked?"), the pre-existing daily_obs for 2007 (doc_id=38) had a confirmed systematic bug:

- **Phantom day rows**: short months (Feb in a non-leap year, or any 30-day month) had day 29/30/31 rows that shouldn't exist at all — e.g. Feb 2007 (28 real days) had day 29/30/31 all present with the value 154 (a plausible-looking but entirely fabricated number).
- **Wrong values at real month-boundary days**: the last 1-3 real days of many months held values well outside that month's own printed Minimum/Maximum range (sometimes looking like a "preview" of the next month's typical range, sometimes just an outlier). Confirmed by testing every daily value against the month's authoritative min/max (from `monthly_station_obs` `max_cm`/`min_cm`, or a table's own printed Minimum/Maximum stats block) and finding real violations.
- **For at least one station (Kőrakáspuszta, 2007, tbl15)** the problem was far worse than a few boundary cells: ~110 of 365 days (30%) were out of range, including a run of **22 consecutive identical-value days** in November — this looks like extended placeholder/fabricated data, not a simple boundary leak, and would require real re-transcription (not just NULLing) to fix properly.

**How to check a year before trusting its "skip" daily_obs note:**
1. Pick 2-3 stations. Pull the table's own printed Minimum/Maximum row (every daily table in this series has one at the bottom) — or use the already-validated `max_cm`/`min_cm` in `monthly_station_obs` if that table's tbl7 data has itself been verified.
2. Query `daily_obs` for that year/station and flag any value outside `[min, max]` for its month. Any hit is a confirmed error (impossible by definition, not a matter of interpretation).
3. If violations cluster only at the last 1-3 days of a month (small in count), it's likely the known boundary-leak pattern — safe to NULL those specific cells (don't guess-replace).
4. If violations are numerous, span most of a month, or include repeated-identical-value runs — that station's data needs a full re-transcription from the source PDF page, not a spot-fix.
5. **Be careful reading a table's own tiny bottom stats block** — it's easy to misread by a few units in a dense small font (happened once during this check, on tbl11/Pátkai; the authoritative `monthly_station_obs` values, already independently validated earlier in the same session, resolved the ambiguity). When two sources disagree, prefer whichever was already cross-validated against the annual balance narrative/formulas.

**Status as of 2026-07-27 (2007, doc_id=38)**: agard_vizallas, patkai_tarozo_vizallas, zamolyi_tarozo_vizallas, agard_vizhomerseklet, kapolnasnyekvizhozam checked and boundary-cell-NULLed (small number of fixes each, phantom rows deleted for all 9 stations). korakaspuszta_vizhozam found to need full re-transcription (not done yet — paused here per user request to reassess scope). kisfalud_vizhozam, csakvar_vizhozam, zamoly_vizhozam, patka_vizhozam not yet checked at all. **Every other year in the tracker marked "skip | already extracted" (2006 and earlier) is unverified against this same bug and should not be assumed clean.**

### daily_obs — 2025 doc ships two stale 2024 pages instead of 2025 data (found 2026-08-22)

In `Velencei-tó vízmérleg 2025.pdf` (doc_id=41), doc tbl16 (p.24, Zámoly/Burján-árok) and tbl17
(p.25, Pátka/Rovákja-patak) daily flow tables both print `Év: 2024` in their own header block, carry
an older `Készült:` timestamp than the other 7 daily tables in the same document (2025.03/2026.03
vs the others' 2026.03.25/04.01), and their Jan 1–3 values match the already-extracted 2024
`daily_obs` rows for `zamoly_vizhozam`/`patka_vizhozam` exactly. The vendor appears to have left
last year's pages in by mistake instead of regenerating them for 2025.
USER DECISION 2026-08-22: did not insert this data under year=2025. `zamoly_vizhozam` and
`patka_vizhozam` daily data for 2025 is simply missing from this source document — not extracted,
not guessed. Check for a corrected/reissued PDF before assuming this gap is permanent. If a future
year's document shows the same header/timestamp mismatch pattern, treat it the same way (Rule C
stop, don't insert as the current year).

### historical_monthly — vizhaztartas_* tbl16 column shift, three variables misnamed (found 2026-08-25, fixed 2026-08-25)

`historical_monthly`'s `vizhaztartas_*` family (1971–1996, from tbl16 of `Velencei-tó vízmérleg,
1996.pdf`, doc_id=27, p.26–27, rotated scan) had three variables carrying wrong names. Source
table has two blocks: rows 1–5 aggregated terms, rows 6–9 their breakdown. Original extraction
skipped row 6 (`hozzáfolyás`, catchment inflow) — assumed row 2's total already covered it — so
every subsequent row's label shifted one position early, and row 9 (`vízkivétel`) fell off the
table entirely. Rows 11–13 (`negatív elemek`, `pozitív elemek`, `készletváltozás`) were never
extracted either.

Wrong mapping (pre-fix): row 6 → `vizhaztartas_tarozo`, row 7 → `vizhaztartas_leeresztes`,
row 8 → `vizhaztartas_vizkivetel`. Correct mapping in §5.

**Values were correct, only labels were wrong** — confirmed by two independent cross-checks:
`hozzafolyas = tarozo + leeresztes` (old names) held in 25/26 years (only 1984 deviated), and
`−leer_vk − vizkivetel` (old names) matched `monthly_balance.vizkivetel` for 1996 exactly (20).

**How to recognise the same failure elsewhere:** a multi-row source table with an aggregated-terms
block followed by a breakdown block, where the breakdown's row count doesn't match the number of
DB variables actually populated — check whether the first breakdown row was silently dropped
because a differently-named total variable already "covered" it.

**Fix (2026-08-25):** three `UPDATE`s on `historical_monthly.variable`, collision-free order
(see `openspec/changes/fix-vizhaztartas-column-shift/design.md` Decision 2):
`vizhaztartas_tarozo`→`vizhaztartas_vizgyujto`, `vizhaztartas_leeresztes`→`vizhaztartas_tarozo`,
`vizhaztartas_vizkivetel`→`vizhaztartas_leeresztes`. Row 9 and rows 11–13 extracted separately
(B2, own tracker turn) as `vizhaztartas_vizkivetel`, `vizhaztartas_negativ`, `vizhaztartas_pozitiv`,
`vizhaztartas_keszletvaltozas`.

**Separate value error found during B2 row-alignment pinning (2026-08-25):** while cross-checking
row 6/7 (`vizgyujto`/`tarozo`) against p.26 for 1971–1984 to pin the label-vs-data vertical offset
(labels print one row lower than their data on this table — same "half-line label offset" as tbl7/
tbl8, §13), `vizhaztartas_vizgyujto` 1984 was found to be a genuine mistranscription: DB held `319`
(a duplicate of 1983's value), page clearly prints `297`. This is the exact source of the "1984
anomaly" flagged by the arithmetic check `hozzafolyas = vizgyujto + tarozo` (514 vs 536 with the
wrong value; 514 vs 514 with 297). Corrected via direct `UPDATE` after re-confirming on a 4x zoom
crop. Unlike the naming bug, this was a value error in an already-"verified" row — a reminder that
"already correct" claims about rows 1–8 pre-date this pinning check and were not independently
re-verified cell-by-cell.

### monthly_station_obs — kozepes_m3s NULL station_id

Years 2011, 2012 (partial), 2013, 2019, 2022 still have `kozepes_m3s` rows with `station_id=NULL`. (2021 fixed 2026-07-08: 72 NULL rows deleted, 65 clean rows inserted.) These are 6 different flow stations per month but station identities were not recorded during original extraction. 2023 and 2024 extractions correct (all rows have station_ids).

**Impact:** A UNIQUE index on `(year, month, COALESCE(station_id,''), variable)` cannot be created until these rows are fixed. The existing embedded `UNIQUE(year, month, station_id, variable)` constraint still works for non-NULL station_id rows.

**Rule going forward:** When extracting `tbl3` (havi középvízhozamok), ALWAYS assign the correct `station_id` to each row. Never insert kozepes_m3s with station_id=NULL.

**To fix:** Re-process tbl3 for years 2011, 2012, 2013, 2019, 2021, 2022 — match each row's values to the station column headers in the PDF, UPDATE the existing rows with the correct station_id.

### Schema fixes applied (2026-07-07)

| Fix | Description |
|-----|-------------|
| `expedition_flows` | Deleted 7 true-duplicate NULL rows (Agárdi-árok ids 11,15,16,17,18,19,20) |
| `expedition_flows` | Added `idx_expflows_unique` expression index on (date, station_name, COALESCE level, COALESCE flow) |
| `release_events` | Recreated with `UNIQUE(year, month, station_id)` + `station_id NOT NULL` |
| `historical_monthly` | Added `idx_hm_unique` expression index on (year, month, COALESCE(station_id,''), variable, source_doc_year) |
| `monthly_station_obs` | Deferred — blocked by NULL kozepes_m3s rows (see above) |

---

## 15. Table Structure Registry (Row/Column Metadata)

**Purpose:** a per-table baseline of expected row labels/order/count and column layout, built up as each table type gets extracted for the first time. Use it per Rule F: after reading a table's structure and before transcribing values, diff what's on the page against the entry below for that `tblN` + era. First time a table is seen, there's nothing to diff against — extract, then write the entry. After that, any deviation is a Rule C stop-and-ask, not a silent judgment call.

Entry format: table id, confirmed year(s)/era, row labels in printed order, column layout, station list (if applicable), free-text gotchas.

### tbl1 — Hóeleji vízállás + vízeresztések (→ release_events)

**Confirmed: 2010 (era C scanned), 2013–2024 (era D digital), 1988–1995 (era A)**

- **Era-A years can print 2 tables per landscape page** (1988: tbl1 top + tbl2 bottom on p8, like 1989; 1990 = 1/page) — check the page map from the toc step, don't assume.
- **Era-A volume units vary: 1988 prints E.m³ = EZER m³ (thousand)** (title "(E.M3)"; ÷1000 → release_volume_1e6m3; tbl6 II.a "millió m³" row confirms: 50,4 E.m³ = 0,05 M m³), while 1989/1990 print raw m³ and 1995-era uses m³ too — always check the title unit per document.
- 1988 Pátka Júl: level ROSE during a 13-31 release (457→493) with a single-month volume (2 110 700 m³) larger than typical annual — printed identically in tbl1 AND tbl6 II.a, so a genuine source figure; stored as printed, anomaly noted in tracker (likely Zámolyi→Pátka transfer passing through).

⚠️ **Layout varies**: 2013 and earlier era-D years (and the 2010 era-C scan) use a clean horizontal table (rows=metrics, columns=months, not rotated) — much easier to read directly. 2016–2024 use a rotated/portrait layout (see below). Same fields either way.

- 3 station blocks, fixed order: Velencei-tó (Agárd), Pátkai-tározó, Zámolyi-tározó
- Velencei-tó block: **4 rows** — `Vízállás (cm)`, `Vízeresztés időtartam`, `Mennység (10^6 m³)`, `tómm` (lake-mm equivalent — confirmed 2010; only the lake has this extra row, reservoirs don't since "tó mm" is a lake-specific unit)
- Pátkai-tározó / Zámolyi-tározó blocks: **3 rows** each — `Vízállás (cm)`, `Vízeresztés időtartam`, `Mennység (10^6 m³)` (no tómm row)
- Columns: Jan…Dec, `<next-year>.jan.` (extra 13th month, NOT inserted — it duplicates next year's own Jan row, already covered when that year is processed), `Össz.` (annual total — NOT inserted as month=0; used only as a cross-check: sum Jan–Dec and compare, small 1-2 unit rounding differences on tómm are expected/acceptable, do not force-correct)
- Dash (`-`) in időtartam/mennység = no release that month → NULL, not 0, unless narrative text explicitly states a literal zero reading. Distinguish from an explicit printed `0`, which IS a real zero (insert 0, not NULL).
- **`note` TEXT column** (added 2010, ALTER TABLE — schema originally had no notes field): use for (a) months where a single month has **two disjoint release sub-periods** (e.g. "1-7, 18-30" with a pause in between) — store the overall min-start/max-end span in `release_period_start/end` and the exact printed text verbatim in `note`; (b) footnote text that applies to a specific station/month (e.g. "csak árapasztón át, zsilipnyitás X-én"); (c) Rule D fallback when a compound/comma-separated időtartam string can't be confidently mapped to its month in a dense scanned table — leave `release_period_start/end` NULL, put best-effort transcription in `note`, but still keep the water_level_cm/volume figures if they're independently cross-checked (e.g. against the printed Össz. sum).
- Confirmed 2010: Pátkai/Zámolyi Jan–Feb showed `-` for water level AND volume (not `0`) → genuine missing data, NULL not 0.

⚠️ **Confirmed 2000 (era B scanned)**: Zámolyi block can carry an extra **Túlfolyás (overflow)** row+volume alongside the standard Vízeresztés (scheduled release) row, plus an **Összesen** (combined) summary row — 6 rows total for that station block instead of the usual 3. USER DECISION 2026-08-18: `release_volume_1e6m3`/`release_period_start/end` store only the Vízeresztés row (consistent with every other station/year); the Túlfolyás period+volume goes into `note` as text, not summed into the main release field.

⚠️ **Confirmed 1997 (era B scanned) — 5-row Zámolyi variant**: same overflow situation, but printed as `Vízállás` / `Vízeresztés (nap)` / `Mennyiség (m3)` / `Túlfolyás` / `Mennyiség (m3)` — 5 rows, and the trailing Mennyiség row is the **combined** (túlfolyás + vízeresztés) monthly total, NOT a túlfolyás-only volume. Tell the two apart by direct read, never by subtraction: in 1997 the trailing row repeats the vízeresztés figures verbatim in the months that had a release but no overflow (Okt 90 936, Dec 966 492), and it sums to its own printed Össz. Consequence: the túlfolyás-only volume is not printed at all that year. Same USER DECISION applies — release fields = Vízeresztés row only; túlfolyás periods and the printed combined figure go into `note`.

- Era-B years also print an **extra 13th `<next-year>.jan.` column** (1995/1996/1997/1998/1999 confirmed) — not inserted, but it cross-checks against the next year's own Jan row once that document is processed. ⚠️ 1995 mislabels this column **"1993. Jan."**; its values matched 1996's own January exactly, so trust the values over the header.
- Era-B volume units are **raw m³**, not 10⁶ m³ (1997/1998/1999 confirmed) → divide by 1e6 for `release_volume_1e6m3`.

⚠️ **Era-A layout (confirmed 1995)** — simpler again: 3 blocks × **3 rows** (`<station>` level, `Vízeresztés`, `Mennyiség (m3)`), with **no tómm row and no `Össz.` column**, so there is no printed annual to cross-check the monthly volumes against. A year with no releases at all is normal here (1995: every Vízeresztés/Mennyiség cell a dash, confirmed by the narrative) — that is 36 rows of water_level_cm with all release fields NULL, not an extraction failure.
- An **empty reservoir prints explicit `0` levels, not dashes**, often with a spanning footnote (1995 Zámolyi: "A tározó üres" across Jan–Nov, "zárás 19-én" under Dec marking the start of the refill). Store the 0s and put the footnote in `note`; do not convert them to NULL.
- A reservoir can carry the "A tározó üres" footnote **while still printing non-zero levels** (1993 Pátkai: footnote spans the whole Vízeresztés row, levels run 22…102…1…50) — the footnote describes the operating regime (sluice open, no retention), it does not mean every level is zero. Read the level row as printed either way.
- A level cell can print a **word instead of a number** — 1993 Pátkai January reads `jég` (frozen, level not measurable) → `water_level_cm` NULL, word verbatim in `note`.

### tbl2 — Vízgyűjtő havi csapadékösszegei (→ monthly_station_obs, csapadek_mm)

**Confirmed: 1988 (era A, 5 stations), 2011 (9 stations), 2014 (8 stations), 2015 (7 stations), 2016–2020 (6 stations), 2024 (5 stations) — era D**

- **Era-A roster is NOT fixed: 1988 prints only 5 stations** (Agárd, Velence, Sukoró, Pákozd, Dinnyés) vs 1989–1992's 11 (incl Sukoró D. ház). Zámoly precipitation is NOT in tbl2 those years — it lives in tbl4's Zámoly műszertérkert block (zamoly_meteo). Read the actual station column per document.
- 1988 summary row = single ÁTLAG (5-station mean) which the narrative cites as "tóra hulló csapadék" (433 mm) — but the balance C raw (tbl9) = this Átlag rounded (434) and C jav = 431; three closely-related figures, only the tbl8/tbl9 ones go into monthly_balance.

- One row per precipitation station; station SET varies by year — always read the actual station column, don't assume a fixed count. Confirmed changes: **Nadap** (`nadap_csapadek` — had to be added to the `stations` table, wasn't in the registry at all) active in 2011, OMSZ discontinued its daily readings from 2011-10-01 (that document's own footnote says so; Oct–Dec of that year are themselves estimates averaged from Velencefürdő/Pázmánd/Lovasberény, insert as printed anyway — not a Rule D case since the doc gives real numbers, just flags them as estimated); **Gánt** (`gant_csapadek`) active in 2014, unreliable/excluded by 2015 text, decommissioned by 2016; **Velencefürdő** (`velencefurdo_csapadek`) active through 2015, decommissioned before the 2016 report. So: 2011 → 9 stations (adds Nadap), 2014 → 8 (adds Gánt+Velencefürdő, no Nadap), 2015 → 7 (no Gánt), ≥2016 → 6 (no Gánt, no Velencefürdő).
- If a station name in the table isn't in the `stations` table at all (unlike Gánt/Velencefürdő which already existed there unused) — this has no `station_name` text fallback the way `expedition_flows` does. Add a new row to `stations` (id/name/type='csapadek'/unit='mm') rather than dropping the data or forcing `station_id=NULL` (NULL is reserved for the Agárd meteo/lake-level variables, not for named-but-unregistered precip stations).
- Columns: Jan…Dec, `Össz.` (→ month=0 annual row, inserted)
- Below the main station rows: 1–2 summary average rows (e.g. "(1-6.) A vízgyűjtőre hulló csapadék átlaga", "(1-3.) A Velencei-tóra hulló csapadék átlaga") — these are catchment/lake-area averages, **not** individual stations; not inserted into `monthly_station_obs` (no station_id for them), but the "(1-3.) tóra hulló" figure is useful as a cross-check for tbl8's Csapadék row (see tbl8 note below)

### tbl3 — Havi középvízhozamok (→ monthly_station_obs, kozepes_m3s)

**Confirmed: 1988 (era A, 4 gauges), 2020, 2021 (6 stations, identical set) — era D**

- **Era-A gauge roster varies year to year**: 1988 = 4 gauge rows (Császárvíz-Kőrakás, Császárvíz-Csákvár, Rovákja-Pátka, Vereb-Kápolnásnyék; plain data rows, no group headings — unlike 1989's 2 gauges under CSÁSZÁRVÍZ/VEREB-FAZMANDI headings, or 1990's 3). VÍZKIVÉTEL block (m³/s + tómm rows) present every year — never stored, but the tómm row sums to tbl8/tbl9 Vk raw (1988: 96 vs comparison 97 = jav).
- Kőrakás spikes can be Pátka-release transit water (1988 Júl 1,04 / Aug 0,497 m³/s during Pátka 13-31 Júl + 1-12 Aug releases into Császár-víz above the gauge) — plausible, not a misread; tbl6's II−II.a formula exists precisely to remove it.

- 6 flow stations, fixed set across at least 2020–2021: Kápolnásnyék (`kapolnasnyekvizhozam`), Kőrakáspuszta (`korakaspuszta_vizhozam`), Kisfalud (`kisfalud_vizhozam`), Csákvár (`csakvar_vizhozam`), Zámoly/Burján-víz (`zamoly_vizhozam`), Pátka/Rovákja-patak (`patka_vizhozam`)
- Columns: Jan…Dec, `Átlag` (→ month=0 annual row, inserted — it's an average not a sum, but stored the same way)
- Always assign station_id per row — never insert with station_id=NULL (see §14 known issue)

### tbl4 — Meteorológiai jellemzők havi közepei (→ monthly_station_obs, station_id=NULL)

**Confirmed: 1988 (era A), 2020, 2024 — era D**

- **Era-A Agárd block can lack the Napsütés row entirely** (1988: 4 rows léghő/páranyomás/szél/kád; 1989 had all 5) — row set varies, read it.
- 1988 confirms the era-A kád unit = monthly totals (Ápr–Okt 77…177, Év = own sum), matching the 1991/1993 convention; the A(sum) cross-check against tbl5 settled a 177-vs-180 Júl digit dispute (Összeg cell 748 decisive).

- 5 rows, fixed order: `Léghő (°C)`, `Páranyomás (hPa)`, `Szél (m/s)`, `"A" (1,14 m²) kád párolgása (mm)`, `Napsütéses órák száma (h)`
- Columns: Jan…Dec, `Átlag`, `Összeg` — Átlag applies to Léghő/Páranyomás/Szél (temperature-like rows), Összeg applies to kád párolgás/Napsütés (accumulative rows); the non-applicable column is a dash for each row, not both filled
- Kád párolgás row only has values Apr–Oct (summer months); Jan/Feb/Mar/Nov/Dec are dashes → NULL, not inserted
- "Zámolyi műszerkert" sub-section may appear in some years as a second station block — check for it; if present, needs a station_id decision (ask user if not in §6 mapping). Era B 1997/1998/1999/2000 confirmed: it carries 3 rows (`Csapadék`, `Léghő`, `Páranyomás`) → `zamoly_meteo`; its Csapadék row duplicates that station's row in tbl2.
- ⚠️ **The kád párolgás row's unit is NOT stable across years — always check it against tbl5 before inserting.** 1998/1999 print monthly TOTALS (76.7 … 143.7 mm). 1997 prints the DAILY MEAN instead (2.4 … 4.5), identical to tbl5's `A (átl.)` row, while tbl5's `A (sum)` row carries that year's monthly totals. Tell them apart by magnitude (single digits = daily mean) and by matching the row against both tbl5 rows. USER DECISION 2026-08-20: `a_kad_parologas_mm` always stores the **monthly total** — take it from tbl5's `A (sum)` when tbl4 prints the daily mean — so the variable has one meaning across years; the daily mean is preserved in `evaporation_inputs.A_atl_mm` anyway. If `A (sum)` has no printed annual (dash), insert no month=0 row rather than summing it (Rule B).

### tbl5 — Párolgásszámítás (→ evaporation_inputs)

**Confirmed: 2020, 2024 — era D**

- Two sub-tables sharing the page: **winter formula** block (rows `E (mb)`, `e (mb)`, `t (°C)`, `u (m/s)`, `n (nap)`, `P (mm)`; columns Jan, Febr, Márc, Nov, Dec, `Összeg`) and **summer formula** block (rows `K(nád)`, `A(sum) mm`, `A(átl) mm`, `u (m/s)`, `n (nap)`, `P (mm)`; columns Ápr…Okt, `Összeg`)
- An `Évi összeg` (annual grand total P) appears once, near the summer block — narrative-only, not inserted (no month=0 in evaporation_inputs)
- Winter rows never carry K_nad/A_sum_mm/A_atl_mm; summer rows never carry E_sat_mb/e_act_mb/t_celsius — leave the other formula's columns NULL
- **The printed formula constants change over time** (only inputs are stored, so nothing in the schema depends on this — but note the year's formula in the tracker): 1995 uses winter `P=0.41*[((E-e)/1,33)**0.9]*…` and summer `P=0.555*(1+K)*A(átl.)**0.79*…`; 1996–1999 use winter `0.55*…` and summer `1.11*(0.58+0.42K)*…`. The 1996 report re-derived the summer formula after a geodetic survey changed the assumed water:reed ratio from 50:50 to 58:42.
- **Cheap sanity cross-reads** (direct reads, not derivations): the winter block's `e`/`t`/`U` rows repeat tbl4's Agárd Páranyomás/Léghő/Szél for the same months, and `A (sum)` repeats tbl4's kád párolgás row. If they disagree, one of the two tables was mis-transcribed.

### tbl6 — "Hozzáfolyás számítása" (ToC-numbered table 6) — ⚠️ NOT the expedition_flows source

**Confirmed: 2020 (era D)** — flagged and resolved with user 2026-07-25

- This ToC-numbered table is a **monthly calculation/roll-up table**, reusing tbl3's two upstream flow series (Vereb-Pázmándi-vf./Kápolnásnyék and Császár-víz/Kőrakáspuszta) and applying fixed formulas (`III = I−IIa`, `IV = 2,05+II`, `V = 1,84·II`, `VI = Hozzáfolyás = IV+V`) to derive the monthly inflow term used in the water balance (tbl8/9's "H"). It is a derived/computed table, not a record of field measurements.
- **Do not extract this table into `expedition_flows`.** The actual sporadic, dated, multi-tributary field-measurement table (which IS the expedition_flows source) is a separate, unnumbered-in-ToC table titled **"A Velencei-tó vízgyűjtőjén mért vízhozamok, `<year>`-ban"** — this was table 20 in the 2020 ToC (last of the 20 numbered `táblázatok`), spanning 3 pages (p.29–31 in the 2020 doc), immediately before the `ábrák` (figures) section starts.
- When resuming tbl6 for a new year: locate the ToC, find the "...mért vízhozamok..." table (usually the LAST numbered table, right before the figures), and use that page range — not the "hozzáfolyás számítása" page.
- Expedition table structure: one block per station (bold station name spanning multiple rows), columns `dátum` (MM.DD, no year — infer from doc year), `vízállás (cm)` (often dash for streams without a gauge), `vízhozam (m³/s)` (or a special text value — see markers below)
- Station list varies by year; not every registry station (§6) appears every year, and some appear with literal text "`<year>`-ban nem volt vízhozam mérés" (no measurement that year) → skip entirely, no rows
- Special value markers seen in cell: `száraz meder` / `meder száraz` → `is_dry=1, flow_m3s=0`; `nem mérhető` (unqualified) → `flow_m3s=NULL`, note the reason (e.g. `hideg miatt nem mérhető` = unmeasurable due to cold); `nem mérhető, becslés alapján kb. X` → `is_estimate=1, flow_m3s=X` if a single value is given, `NULL` with a note if only a range is given; `köbözéssel X` → real measurement via bucket method, `is_estimate=0`, note the method
- Duplicate date+station rows with different readings (e.g. two visits same day) are legitimate — insert both
- More special value markers (confirmed 2019): `állóvíz` (standing water, no flow) → `flow_m3s=0`, note; `nincs vízmozgás` (no water movement) → `flow_m3s=0`, note; `növényzet miatt nem mérhető` / `síkos rész miatt nem mérhető` (unmeasurable due to vegetation/slippery access) → `flow_m3s=NULL`, note the reason
- Station set is NOT fixed year to year — 2019 included "Dinnyés-Kajtori-csatorna, Aba" and "Császár-víz Dinnyési IN duzzasztó" with real readings (absent/no-data in 2020); neither is in the §6 registry → use `station_id=NULL`, keep the full printed name in `station_name` (per §6's own fallback rule, not a Rule C stop)
- More markers (confirmed 2018): `zsilip nyitva` (sluice gate open, no flow figure given) → `flow_m3s=NULL`, note; `pangóvíz` (stagnant/pooled water, no real flow) → `flow_m3s=0`, note (same treatment as `állóvíz`)
- More markers (confirmed 2016): `csordogál` (trickling, no numeric flow given) → `flow_m3s=NULL`, note
- More markers (confirmed 2015): `pangó` / `pangóvíz` (stagnant, no real flow) → `flow_m3s=0`, note (same treatment as `állóvíz`)
- 2012 confirmed: a range-only reading (e.g. `0,002-0,003`, no single value given) → `flow_m3s=NULL`, note the range as text — do not average or pick an endpoint (Rule D)
- 2014 confirmed a distinct station "Császár-víz, Fornapuszta" → `fornapuszta_vizhozam` (separate from "Vereb-Pázmándi-vízfolyás, Kápolnásnyék" → `kapolnasnyekvizhozam`, which also appeared the same year) — don't conflate the two even though §6's own label text bundles "Forna-puszta / Vereb-Pázmándi" together. Also saw "Dinnyési-tápcsatorna, Dinnyési duzzasztó" as a name variant of the NULL-station-id Dinnyés IN duzzasztó entries seen in other years.

### tbl7 — Jellemző vízállások és vízhőmérsékletek (→ monthly_station_obs)

**Confirmed: 2020, 2024 — era D**

- 3 station blocks: Velencei-tó·Agárd (rows `Max.`, `Átlag.`, `Min.`, `Vízhő (°C)` — 4 rows), Pátkai-tározó (`Max.`, `Átlag.`, `Min.` — 3 rows), Zámolyi-tározó (`Max.`, `Átlag.`, `Min.` — 3 rows)
- Row count: 10 data rows total (4+3+3)
- Columns: Jan…Dec, `Év` (→ month=0 annual row, inserted)
- Velencei-tó block uses station_id=NULL; Pátkai/Zámolyi blocks use their tározó station_id

⚠️ **Summary-column variants** — read which summary columns exist before mapping month=0:
- 1996/1997 (era B): a single `Év` column, used by all four rows.
- 1995 (era A): **both `Átlag` and `Év`**, and each row fills exactly one — `Max.`/`Min.` fill `Év` (the annual extreme), `Átlag`/`Vízhő` fill `Átlag`. Take whichever is filled as month=0; the other prints a dash.
- Era-B/A scans often print the row labels half a line off their value rows (see the tbl8 warnings below). Verify Max/Átlag/Min order from the summary column itself (row 1's summary = the largest monthly value, row 3's = the smallest) and against tbl1, whose start-of-month levels equal each month's `Min`.
- ⚠️ **A reservoir's December Min cell has twice now printed a value larger than that month's Max** (1997 Zámolyi 480 vs 448; 1995 Zámolyi 110 vs 0) — in both cases the block's own annual cell ignores it, and in both cases the reservoir was refilling in late December. Treat as a source error: store NULL and record the printed value in the tracker, don't move it to the Max row.
- **1992 (era A) prints the table transposed**: months as rows × variables as columns (same orientation flip as that year's tbl1), with BOTH an `Átlag` and an `Év` summary ROW (Átlag fills Átlag/Vízhő, Év fills Max/Min — same semantics as 1995's dual columns). Station set/blocks unchanged. Pátkai's Vízhő prints only Márc–Jún (sparse-vízhő, no annual — 1993 precedent); Zámolyi block all dashes → 0 rows.

### tbl8 — A Velencei-tó vízmérlege, tómm (→ monthly_balance raw/adj cols)

**Confirmed: 1988 (era A, SINGLE-VALUE javított variant), 2020, 2019 (era D) — 23-row layout**

⚠️ **1988 role-swap variant**: in that document tbl8 is a single-value JAVÍTOTT (final-style) table — 10 rows, no raw/j pairs, no Záróhiba row (Z lives in tbl9) — and the nyers raw/adj pairs live in tbl9 instead (see tbl9 entry). Era-C/D convention (tbl8=raw/adj, tbl9=final) is REVERSED in 1988. Rule: row labels decide, title wording varies (1988 titled "évi vízmérlege", printed outflows NEGATIVE — store magnitudes). Its ΔK row is ΔKszám-jav (=Bevétel−Kiadás, formula-locked), NOT mért; the mért series comes from tbl9's DKm column. Narrative phrase "a megváltoztatott elemek 'j' indexszel szerepeltek a 8.táblázatban" refers to this jav-only table.

Full row order, top to bottom, each pair is raw-value-row immediately followed by its "j" (javított/adjusted) subscript row.

⚠️ **The Hozzáfolyás-tározóból/Htj pair's order is NOT fixed across documents** — 2020 printed `Htj` before `Hozzáfolyás tározóból` (reversed, confirmed with the user that year since the scan was too dense to read labels directly), while 2019's scan was clearly legible and printed the standard raw-then-adj order. **Always read the actual printed label for this pair per document — do not assume either order from a prior year.** If the scan is too dense/rotated to read the label text directly (as in 2020), cross-check candidate values against tbl9's final values (see cross-check note below) rather than assuming the previous year's order.

1. `Csapadék` → csapadek_raw
2. `Cj` → csapadek_adj
3. `Hozzáfolyás` → hozzafolyas_raw
4. `Hj` → hozzafolyas_adj
5. `Htj` → hozzafolyas_t_adj  *(adj printed before raw — confirmed order)*
6. `Hozzáfolyás tározóból` → hozzafolyas_t_raw
7. `Bevétel (C+H+Ht+Vp)` → aggregate sum row, **not stored** (no monthly_balance column for it)
8. `Bevétel javított` → aggregate, **not stored**
9. `Párolgás` → parologas_raw
10. `Pj` → parologas_adj
11. `Vízkivétel` → vizkivetel_raw
12. `Vkj` → vizkivetel_adj
13. `Lefolyás` → lefolyas_raw
14. `Lj` → lefolyas_adj
15. `Kiadás (P+Vk+L)` → aggregate, **not stored**
16. `Kiadás javított` → aggregate, **not stored**
17. `Mért készletváltozás` → keszletv_mert_raw
18. `Mért javított készletváltozás` → keszletv_mert_adj
19. `Számított készletváltozás` → keszletv_szam_raw
20. `Számított jav.készletváltozás` → keszletv_szam_adj
21. `Záróhiba Z=ΔKsz−ΔKm` → zarohibia_raw (single row only — no separate adj row printed; convention: `zarohibia_adj=0` for every month, `NULL` for the annual/month=0 row)
22. `Természetes készletváltozás` → term_keszletv_raw
23. `Jav. természetes készletváltozás` → term_keszletv_adj

Other notes:
- **No `Vízpótlás`/`Vp`/`Vpj` row is printed** even though the Bevétel formula references Vp — when tbl9 (final) also shows Vízpótlás=0 for the year, treat vizpotlas_raw=vizpotlas_adj=0 for all months; don't assume NULL by default here, confirm against tbl9 first.
- Columns: Jan…Dec, `Össz.` (→ month=0 annual row, inserted for all raw/adj columns except zarohibia_adj which stays NULL at annual)
- **Cross-check trick that resolved a mid-extraction row-mapping error**: tbl9 (final vízmérleg, next table) prints clean, unambiguous final values for Csapadék/Hozzáfolyás/Párolgás/Vízkivétel/Lefolyás/Mért-kv/Term-kv. In this era D layout, **every tbl9 final value equals the matching tbl8 `_adj` column exactly** (final = adjusted, no further transformation). If your tbl8 row/value assignment is uncertain, read tbl9 first (or immediately after) and match its final values 1:1 against your tbl8 adj-row candidates — this is a direct-read cross-check between two independently-printed tables, not equation-derivation, so it does not violate Rule B.
- Narrative text (Bevezetés/Hidrológiai viszonyok, and the `IV. A <year>. évi vízmérleg számítása` section) usually states the annual Vízkivétel, Mért készletváltozás, Záróhiba, and Term.kv figures in prose — use these as an independent confirmation of which row is which (they matched exactly for 2020: Vk=6, Mért ΔK=-250, Záróhiba=-124, Jav.term.kv=-244).

**Era B (1997/1998/1999 confirmed)** — same 23-row layout, printed in the standard raw-then-adj order (`Hozzáfolyás tározóból` BEFORE `Htj`, i.e. not 2020's reversed pair), with the last three rows labelled `Záróhiba Z=DKsz-DKm`, `DKt=C+H-P`, `DKt jav.=Cj+Hj-Pj`. Two era-B specifics:
- **Adjusted rows are printed sparsely** — only the cells the correction actually changed; a blank adj cell means "unchanged from raw", NOT missing data. Validate per row, never per table: fill the blanks with the raw values and check the row sums to its own printed `Össz.`. If it reconciles exactly (1997: Cj 357, Htj 180, Lj 34, Delta K mért jav. -120), store the filled row. If it does not (1997: VKj, raw sum 32 vs printed 31; 1998: Hj and Pj), store monthly NULL and keep only the printed annual — Rule D. Narrative text often names the exempt months outright ("a hozzáfolyáson **június kivételével** minden hónapban kellett korrekciót végezni") — that is the strongest confirmation available, prefer it over the sum check.
- **No tbl9 final table exists** (era B's table 9 is the geometric lookup) → leave every final column NULL, and leave `zarohibia_adj` NULL as well (no adj Záróhiba row is printed). Confirmed 1998/1999/1997.
- **Row count is not fixed across era B**: 1996 prints 23 rows — no `Htj` row at all — while 1997/1998 print 24. With no `Htj`, put the single `Hozzáfolyás tározóból` series into both `hozzafolyas_t_raw` and `_adj`. Count the label column before mapping; do not assume the neighbouring year's row count.
- ⚠️ **Some scans print the row labels about half a line BELOW their value rows** (1996 tbl7 and tbl8 both do). Never map labels to values by vertical position alone on such a page — pin the assignment with direct reads from other tables first: tbl5's P row = tbl8's Párolgás, tbl6's tómm rows = Hozzáfolyás / Hozzáfolyás tározóból / Vízkivétel, tbl1's lake tómm row = Lefolyás, and in tbl7 each block's `Év` cell identifies Max vs Min while tbl1's start-of-month levels equal each month's Min.
- ⚠️ **`Vízkivétel` and `Lefolyás` are easy to swap and the swap is silent** — both are outflows, and the lake-release figure is the larger of the two. `Lefolyás` = water released from the lake (tbl1's Velencei-tó tómm row); `Vízkivétel` = the Dinnyési Ivadéknevelő withdrawal from the Császár-víz (tbl6's Vízkivétel row). 1996's pre-existing annual row had them reversed (254/20 instead of 20/254); corrected 2026-08-20 after cross-checking both source tables.
- Narrative annual figures can disagree with the table by a few tómm in era B (1997: prose says hozzáfolyás 340 / párolgás +18 / term.kv -241 while the table prints 337 / +9 / -237) — the table is the source of truth, note the gap and move on.

**Era E (2025 confirmed)** — 26-row variant: same 23 rows as above, plus explicit `Vízpótlás`/`Vp` and `Vízpótlás javított`/`Vpj` rows (raw-then-adj, right after Htj) and an explicit `Jav. Záróhiba Zj=DKszj-DKmj` row (right after the raw Záróhiba row) — both additions were previously only inferred as an implicit 0 (see "No Vízpótlás row" and "convention: zarohibia_adj=0" notes above); 2025 prints them outright, all-zero, consistent with those defaults. Treated as a low-risk additive variant, not a Rule F stop, since the printed values match what the registry already assumed.

### tbl9 — A Velencei-tó végleges vízmérlege (→ monthly_balance final cols)

**Confirmed: 1988 (era A, TRANSPOSED nyers raw/adj variant), 2020, 2024 — era D/C (2002+)**

⚠️ **1988 structure**: titled "A Velencei-tó 1988. évi NYERS vízmérlege /tómm/", printed **transposed** (months I.–XII. as rows × elements as columns) and carrying the raw + jav pairs (C/Cj, H/Hj, Ht/Htj, Bevétel/jav, P/Pj, Vk/Vkj, L/Lj, Kiadás/jav, DKm/DKmj, DKsz/DKszj, Záróhiba, DKt) — i.e. era-B-style tbl8 content in the tbl9 slot, transposed. Mapping: tbl9 → raw/adj cols, tbl8 → final cols. Dense transposed scans suffer heavy column-bleed on monthly reads; reliable extraction path = lock the Összesen row against external sources (tbl5 P, tbl6 VI/II.a, tbl3 tómm, tbl2-Átlag C, tbl1 L), take raw monthlies from those source tables, and use the printed identity Z = DKsz_raw − DKm per month to lock the DKm/Z series. 1988 Aug: monthly DKsz raw sum −131 vs printed Év −129 (2 tómm source inconsistency, stored as-is); monthly Z sum ≠ Év Z (65 vs 31) → Rule D NULL on ambiguous months, annual + narrative-locked extremes kept.

- 9 rows, fixed order, clean single-value table (no raw/adj split): `Csapadék`, `Hozzáfolyás`, `Hozzáfolyás tározóból`, `Vízpótlás`, `Párolgás`, `Vízkivétel`, `Lefolyás`, `Mért vízkészletváltozás`, `Természetes készletváltozás*` (footnote: *a tározóból történt vízeresztés nélkül* — natural change excluding reservoir releases)
- Columns: Jan…Dec, `Évi összes` (→ month=0 annual row, inserted)
- Era B (1996–2001): table 9 in this position is instead "geometriai jellemzők" (area/volume lookup curve) — **skip**, not time-series (see §10)

### tbl16 — Vízháztartási jellemzők (→ historical_monthly, `vizhaztartas_*`, station_id=NULL)

**Confirmed: 1996 (era B), doc_id=27, p.26–27, rotated scan (`Page rot: 270`)** — a single retrospective
table spanning both pages: p.26 covers 1971–1984 (14 year columns), p.27 covers 1985–1996 (12 year
columns) plus a trailing `1971-1996` summary column (not a data year — skip).

- **13 header rows in two blocks**, `Összesen:` (row 10) is a section label with no data row of its own:
  - Block 1 (rows 1–5, aggregated terms): `Csapadék`, `Hozzáfolyás+hozzáf. tározóból` (total),
    `Vízpótlás`, `Párolgás`, `Leeresztés+vízkivétel`
  - Block 2 (rows 6–9, breakdown of rows 2 and 5): `Hozzáfolyás` (catchment inflow only — do not
    confuse with row 2's total), `Hozzáfolyás tározóból`, `Leeresztés`, `Vízkivétel`
  - Block 3 (rows 11–13, under `Összesen:`): `Negatív elemek`, `Pozitív elemek`, `Készletváltozás`
- Variable mapping: see §5 table — corrected 2026-08-25, was column-shifted (§14).
- ⚠️ **Blocks 1–2 print each label one visual row below its own data** (the "half-line label
  offset" pattern, same as tbl7/tbl8) — e.g. the label `Csapadék` sits beside row 2's numbers, not
  row 1's. **Block 3 (`Összesen:` onward) has no offset** — its labels align directly with their
  data (confirmed via the internal identity `pozitiv + negativ = keszletvaltozas`, holds exactly
  for all 26 years). Do not assume the offset carries across the `Összesen:` line.
- **Pin the offset before transcribing new rows**: query the DB for the already-extracted rows in
  the same block (they hold correct data even where labels were wrong) and match against the raw
  pixel values — don't rely on eyeballing which label sits next to which number band.
- Row 9 (`vízkivétel`) verification identity: `vizkivetel = −leer_vk − leeresztes` (Decision 4,
  `openspec/changes/fix-vizhaztartas-column-shift/design.md`) — holds exactly for 25/26 years; 1985
  is off by 1 (page prints `0`, formula gives `−1`) — treated as source rounding, not a misread.
- Both pages' first row (Csapadék) and the `1971-1996` summary column visually resemble data but are
  not extra year columns — check the header row's year labels before assuming column count.

### tbl10 — Velencei-tó napi vízállásai / "11/VÍZÁLLÁS" (→ daily_obs, station_id=agard_vizallas)

**Confirmed: 2006 (era C scanned)**

- Single station block, header block: `Állomás kód: 000818`, `Állomás neve: Agárd`, `Vízfolyás: Velencei tó`. Header states reading window `Időpont: 7:00 +- 60 perc` — one reading per day, taken near 7am.
- Grid: rows=Nap (day 1–31), columns=Jan…Dec (12 months, no annual summary column in the grid itself).
- Quality-flag letters seen glued to values: `N` (plain/normal reading) and `NA` (interpolated during ice cover — Jan/Feb/Már 2006 are entirely `NA`, later months mostly plain `N`). Neither is `A` or `P` from the §4a docling note — `N` is a new flag not previously documented; stripped the same way (letters carry no numeric meaning, safe to discard per the guide's existing regex-strip approach). Not a Rule C stop — flag stripping is unconditional regardless of which letter.
- Bottom stats block (present every month column that has non-`NA`-only data): `Minimum`/`Nap`/`Óra:Perc`, `Átlag`, `Maximum`/`Nap`/`Óra:Perc`, plus separate `Jeges min`/`Jeges max` rows (with their own Nap/Óra:Perc) for ice-covered months where the plain Minimum/Maximum are blank. Also a whole-period summary block at the very bottom (`Az egész időszakra vonatkozó`: minimum/átlag/maximum + jeges minimum/maximum with explicit dates) — narrative-only, not inserted.
- **docling reliability confirmed poor on this table** — on the 2006 page it silently mis-scanned 4 distinct cells to implausible values (a 3-digit value inflated to 691, two instances of a leading-digit-dropped 14 instead of 140, a duplicated-digit 1401 instead of 140) and dropped 11 of 30 September day-rows entirely, with no error/warning raised. `scripts/render_page.py` at 300dpi direct visual read was fully legible with zero ambiguous cells and cross-validated exactly against the table's own printed extremes (see §4b method) — prefer this method over docling for tbl10+ daily grids going forward unless docling is spot-checked clean first.
- Cross-check method confirmed effective: match each month's printed Minimum/Maximum value+Nap+Óra:Perc against the transcribed grid. Exact match when Óra:Perc falls inside the 7:00±60min header window; a small (~1 unit) explainable mismatch when Óra:Perc is far from that window (continuous-monitoring instant vs. the daily snapshot) — see §4b point 3. Zero unexplained mismatches across all 12 months on this table = high-confidence transcription.

⚠️ **Older template variant confirmed: 2002 (era C scanned)** — a visually distinct, older report generator, still the same underlying daily-grid data:
- Header block reads `Feldolgozott` / `VÍZALLASOK` / `Évszám: <year>` / `adatok jégkóddal` (not `11/VÍZÁLLÁS` / `Adatok minősítő kód nélkül / interpolációval`). Reading window still `Időpont: 7:00 ± 1:00 KEI`.
- Grid layout identical (Nap × Jan…Dec), but an extra inline `Éves` column sits to the right of Dec — only populated in the summary rows, always blank on the 31 day-rows themselves.
- Summary block uses different labels for the same statistics, following the Kis/Közép/Nagy convention already seen in vízhozam tables: `KV` = minimum (Kisvíz), `KöV` = average (Közepes víz), `NV` = maximum (Nagyvíz) — each with its own `nap`/`óra:perc` sub-rows. Separate `Jeges KV`/`Jeges NV` rows (own nap/óra:perc) hold the ice-covered-period extremes, same concept as tbl10's 2006-template `Jeges min`/`Jeges max`. No separate "Az egész időszakra vonatkozó" paragraph — the whole-period stat is just the `Éves` column value on each summary row.
- New flag letters seen: `Z`, `I` (glued to values, e.g. `141 Z`, `142 I`) — not previously documented (2006 template only had `N`/`NA`). **Confirmed not a Rule C stop** (per the tbl10/tbl12 2006 precedent: any new single-letter flag is stripped unconditionally, flag identity never changes handling) — USER CONFIRMED 2026-08-18.
- **This template's KV/KöV/NV summary block is not reliably cross-checkable against the grid** — spot checks on the 2002 doc found KV(Már) matched the grid exactly, but NV(Már) and NV(Nov) matched nothing anywhere in their respective month's grid values at all (not even an adjacent-day quirk). Treat mismatches on this specific template as expected noise, not transcription errors — don't loop trying to reconcile every month.
- **Confirmed anomaly (2002, Júl day 22): a literal `-117` printed value**, physically impossible given day21=118/day23=116 (a smooth trend). Zoom-crop confirmed the digits are genuinely printed with a leading dash, not an OCR misread. USER DECISION 2026-08-18: treat as a printer/scan artifact, insert the unsigned value (117) with a tracker note — don't silently insert a negative water level, and don't NULL it either given the digits themselves are unambiguous.

### tbl11 / tbl12 — Pátkai tározó / Zámolyi tározó napi vízállásai / "11/VÍZÁLLÁS" (→ daily_obs, station_id=patkai_tarozo_vizallas / zamolyi_tarozo_vizallas)

**Confirmed: 2006 (era C scanned)**

- Same "11/VÍZÁLLÁS" template as tbl10, one station per page (tbl11: `Állomás kód 142080`, Pátkai tározó; tbl12: `Állomás kód 142029`, Zámolyi tározó), same grid/stats-block layout.
- tbl11 (Pátkai): flags seen were only `N` and `NA`, same as tbl10 — no new flags.
- tbl12 (Zámolyi): two new quality-flag letters not previously documented — `B` (dominant flag for most of the year, mixed with `A`/`P` as 2nd letters e.g. `BA`, `BP`) and a one-off single-occurrence `J` (Aug day 30, `485J`). Both stripped the same unconditional way as any other flag letter — not a Rule C stop (flag identity never changes handling, per the tbl10 precedent above).
- **New structural finding (tbl12, likely applies to any "11/VÍZÁLLÁS" table with a mix of real and interpolated days within the same month, not just fully-`NA` ice months like tbl10)**: the printed `Minimum`/`Maximum` block only considers days whose flag is a single letter (`B` or `N` alone) — any day flagged with a 2-letter combo (`BA`, `NA`, `BP`, `NP` = interpolated/estimated) is silently excluded from Minimum/Maximum, even though `Átlag` (average) is computed over every day including 2-letter-flagged ones. Confirmed by filtering the transcribed grid to single-letter-flagged days only and getting an exact Nap+value match for all 12 months (incl. the Jan/Feb/Már `Jeges` min/max split, which behaves like tbl10's ice-covered-month case). When cross-checking future tables of this type, filter out 2-letter-flagged days before comparing against the printed Minimum/Maximum — comparing against the raw whole-month min/max will look like a false mismatch otherwise.

### tbl13 — napi vízhőmérsékletek / "11/VÍZHŐ A VÍZFELSZÍN KÖZELÉBEN" (→ daily_obs, station_id=agard_vizhomerseklet)

**Confirmed: 2006 (era C scanned)**

- Same station (Agárd, kód 000818) and template family as tbl10, but measuring water temperature (°C) instead of water level. All values plain `N` flag — no interpolation/ice complications for this measurement type.
- Clean table: all 12 months' printed Minimum/Maximum + the whole-period summary matched the transcribed grid exactly, zero discrepancies (unlike the vízállás tables, no 2-letter-flag filtering needed here since every day was single-letter `N`).

### tbl14 — Vereb-Pázmándi napi vízhozamok / "11/VÍZHOZAM" (→ daily_obs, station_id=kapolnasnyekvizhozam)

**Confirmed: 2006 (era C scanned)**

- Discharge/flow table, header block `Állomás kód 000820`, `Állomás neve: Kápolnásnyék`, `Vízfolyás: Vereb-Pázmándi vízfolyás`, unit m3/sec. Per the §6/§7 disambiguation already on record (Forna-puszta/Császár-víz is a **separate** station from Vereb-Pázmándi/Kápolnásnyék despite the bundled label text) — this table's station_id is `kapolnasnyekvizhozam`, not `fornapuszta_vizhozam`.
- Grid: same Nap × 12-month layout as the vízállás tables, but most cells are unflagged (bare number, no letter) with `P` and `J` appearing on a meaningful minority of days (not rare one-offs — `J` recurs across whole months, e.g. most of Máj/Okt/Nov/Dec). Stripped unconditionally same as any other flag.
- **Cross-check caveat for this table type**: flow/discharge is far noisier intraday than water level or temperature. Several months' printed Minimum/Maximum have Óra:Perc well outside the 7:00±60min window (14:30, 19:00, 22:00 etc.), and the value gap from the day-of grid reading can be a real double-digit percentage (not just ~1 unit) — still the same "instantaneous continuous-monitoring extreme vs. daily 7am snapshot" explanation from §4b, just proportionally larger for this noisier measurement type. Don't treat a large gap as a transcription error on this table family without first checking whether the printed Óra:Perc is inside or outside the window.
- Also saw a **one-day offset between the printed per-column Minimum/Nap and the grid**: Okt's printed Minimum (0.002, Nap 19, 7:45 — nominally inside window) actually matches the grid value at day 20, not day 19 (grid day 19 = 0.003). Value itself is unambiguous either way; treat this as a benign day-attribution quirk in the source's own summary block, insert the grid's own day/value pairs as printed, don't "correct" the grid to match the stats block's day label.
