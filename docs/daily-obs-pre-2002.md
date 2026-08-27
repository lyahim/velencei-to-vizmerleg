# daily_obs Gap Before 2002 — Cause + Chart-Digitization Feasibility

Session finding, 2026-08-27. No extraction performed. No DB write. Decision open.

## Finding

`daily_obs` holds no row before 2002. Not extraction backlog. Source PDFs 1986–2001 contain no daily table.

Earliest `daily_obs` year = 2002. Confirmed by `SELECT year, COUNT(*) FROM daily_obs GROUP BY year`.

## Cause — era structure

| era | years | tables | daily grid |
|---|---|---|---|
| A | 1986–1995 | tbl1–8 | absent |
| B | 1996–2001 | tbl1–8 (+historical tbl10–16, early years only) | absent |
| C | 2002–2010 | tbl1–9 + tbl10+ | present, first appearance |
| D/E | 2007– | same as C | present |

Daily grids (`tbl10–19`: Agárd vízállás, vízhőmérséklet, 6 hozzáfolyás gauge, 2 tározó) enter with era C. Vendor appends them starting 2002 doc.

Per-doc confirmation in `import_tracker.md` toc rows:

| year | line | evidence |
|---|---|---|
| 2001 | `:556` | ToC lists 8 táblázat. "NO daily-grid tables at all in ToC". `5. ábra - napi vízállásai` listed under ÁBRÁK, not TÁBLÁZATOK |
| 2000 | `:573` | 8 táblázat, same structure as 2001 |
| 1999 | `:590` | tbl8 p14 last table, p15 already `1. ábra` |
| 1995 | `:672` | era A confirmed, ToC = TÁBLÁZATOK 1–8 + ÁBRÁK 1–6 |

Era A/B docs 18–19 pages. Era C docs 30–32 pages. Page-count delta ≈ daily grids.

## Charts — what exists

Daily lake level appears as plotted curve in both eras:

| doc | page | figure | title | axis | span |
|---|---|---|---|---|---|
| `Velencei-tó vízmérleg, 2001.pdf` | 18 | `5. ábra` | A Velencei-tó napi vízállásai 2001. | 100–180 cm | jan–dec |
| `Velencei-tó vízmérleg, 1995.pdf` | 19 | `6. ábra` | A Velencei-tó vízállása 1995 | 80–180 cm | 1995-01-01 → 1996-04-25 |

Curve = Excel step-polyline drawn from daily series. Day-vertices geometrically present in ink, not smoothed.

Decoy: `Velencei-tó vízmérleg, 2001.pdf` p17 `4. ábra` — 3 panels (Zámolyi tározó, Pátkai tározó, Velencei-tó), 1971–2001, hóeleji (month-start) values. Not daily.

**Charted daily: lake water level only.** No daily figure for vízhőmérséklet, for the 6 hozzáfolyás gauges (Kápolnásnyék, Kőrakáspuszta, Kisfalud, Csákvár, Zámoly, Pátka), or for Pátkai/Zámolyi tározó level. Digitization recovers 1 of 9 era-C daily series.

## Resolution ceiling

`pdfimages -list -f 18 -l 18` on 2001 PDF: 2340×1654 rgb jpeg, 200 ppi, 126K, ratio 1.1%. Native scan 200 dpi. Rendering above 200 dpi adds no information.

| axis | span | pixels | resolution |
|---|---|---|---|
| vízállás | 100–180 cm | ~870 | ~11 px/cm |
| time | 365 days | ~1730 | ~4.7 px/day |

Existing `agard_vizallas` values integer cm (2002/2010/2020 spot-check: 37–47 distinct integer values per year). ±1 cm plausible at 11 px/cm.

Degraders:

- Page rot 90° + visible scan skew. Per-page deskew required before axis calibration. See `EXTRACTION_GUIDE.md` §4b, `scripts/render_rot.py`.
- JPEG smear at 1.1% compression ratio on ~3 px lines.
- Occlusion. Regulation-band lines (max/min szabályozási szint) cross data curve. Observed 1995 Ápr–Jún + Nov, 2001 Jún.

## Validation available

1. **Error calibration against truth.** Years ≥2002 carry same chart plus real daily table already in DB. Digitize 2009 or 2010, diff against `daily_obs`, obtain measured error distribution before trusting pre-2002 output.
2. **Per-year monthly constraint.** `monthly_station_obs` holds lake `max_cm` / `atlag_cm` / `min_cm`, 12 months each, from tbl7. Stored with `station_id` NULL. 36 constraints per pre-2002 year. Digitized series must reproduce them.

## Blockers — not technical

- `AGENTS.md` data rule: "Never derive, interpolate, or back-compute a missing value. Missing is `NULL`." Digitized pixel readings are estimates.
- `daily_obs` has no provenance column (`id, year, month, day, station_id, value, source_doc_id`). Digitized estimates would be indistinguishable from transcribed values. Downstream `scripts/generate_site.py` charts would render them as read data.
- Backfill requires schema change (provenance/method column, or separate table). Schema question → Rule C, user decision.

## Status

Open. Three paths presented 2026-08-27:

1. Calibration spike on a year ≥2002, report measured error, no insert.
2. Backfill 1986–2001 lake level + provenance column.
3. Drop. Keep NULL per never-derive rule. Monthly max/átlag/min already covers most lake-level analysis.

No path chosen. Nothing built.
