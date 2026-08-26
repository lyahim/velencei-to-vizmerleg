## 1. Docs hygiene (independent — no site dependency)

- [x] 1.1 **Propose to user** the `AGENTS.md` edits: routing table row `docs/file-index.md → the split` becomes a single index; documentation-update-protocol rows naming `docs/file-index-scripts.md` / `docs/file-index-docs.md` collapse to `docs/file-index.md`. **Do not edit `AGENTS.md` directly** — its own rule 1 forbids it
- [x] 1.2 Merge `docs/file-index-docs.md` + `docs/file-index-scripts.md` into `docs/file-index.md` as one path-alphabetical table → verify: every row from both splits present, no path lost
- [x] 1.3 Delete `docs/file-index-docs.md` and `docs/file-index-scripts.md`
- [x] 1.4 Write `docs/README.md` — caveman style: `docs/` holds project documentation; published site is generated to `output/site/`; Pages deploys from Actions, not this folder
- [x] 1.5 Add `output/site/` to `.gitignore` → verify: `git status --short output/` shows nothing after a local generate
- [x] 1.6 Register `docs/README.md` in `docs/file-index.md`

## 2. Data export — `generate_site.py`

- [x] 2.1 Create `generate_site.py` at repo root, flat script, hand-rolled argv, per `AGENTS.md` code rules
- [x] 2.2 Chart query layer: one function per chart id, returning the exact series a chart plots. Apply `COALESCE(final, adj, raw)` for `monthly_balance`, and `value IS NOT NULL` for every `daily_obs` aggregate → verify: `data/charts/parolgas_csapadek.json` 1971–2024, evaporation 801 (1996) and 1049 (2024)
- [x] 2.3 Write `data/charts/<id>.json`, one file per chart → verify: 12 files (all 12 unblocked — `fix-vizhaztartas-column-shift` already archived 2026-08-25), each under 100 KB
- [x] 2.4 Write `data/tables/<table>.json`, one per DB table → verify: `daily_obs.json` row count matches `SELECT COUNT(*) FROM daily_obs WHERE value IS NOT NULL`
- [x] 2.5 Parse `import_tracker.md` statuses per year/table — parse defensively, unparseable row → `unknown`, never crash or drop → verify: counts by status sum to the tracker's total data rows
- [x] 2.6 Build `data/coverage.json` merging DB row counts with tracker statuses → verify: a year with `pending` status renders distinctly from a year with no such table
- [x] 2.7 Parse `docs/known-issues.md` registry, join `charts` column to chart ids → verify: chart 4 carries `korakaspuszta-flat-runs` and `kozepes-m3s-null-station` notes; `handled` rows with `—` produce no note
- [x] 2.8 Emit `DATA_VERSION` (generate timestamp) into every JSON and into the page placeholders

## 3. Site shell

- [x] 3.1 Create `site/templates/{index,klima,adattar,forras}.html` — hand-written Hungarian, Bootstrap 5 markup, placeholder set `{{NAV}} {{BANNER}} {{FOOTER}} {{DATA_VERSION}} {{GENERATED_AT}}`
- [x] 3.2 Shared nav: Áttekintés · Klíma · Adattár · Forrás — Bootstrap navbar, collapses below `lg`
- [x] 3.3 Persistent caveat banner under the nav on **all four** pages, linking to `forras.html`: "Az adatok AI-alapú feldolgozással készültek, eltérhetnek a forrástól. Részletek →"
- [x] 3.4 `site/assets/site.css` — minimal, on top of Bootstrap. No design system, no custom framework
- [x] 3.5 Substitution in `generate_site.py`: `str.replace` over the placeholder set, write to `output/site/` → verify: all four pages written, zero `{{` remaining in output
- [x] 3.6 Write `output/site/.nojekyll` → verify: file exists, empty

## 4. Charts

- [x] 4.1 `site/assets/site.js`: scan `.chart-panel`, read `data-chart` / `data-controls`, fetch `./data/charts/<id>.json?v=<DATA_VERSION>`, build Chart.js instance
- [x] 4.2 Lazy render via `IntersectionObserver` → verify: on `klima.html` load, only charts in view have canvases initialised (confirmed in headless Chromium: 3/18 hydrated at initial load, 18/18 after gradual scroll)
- [x] 4.3 Controls, rendered only when `data-controls="true"`: year range + series toggles in a Bootstrap `collapse`, calling `chart.update()` → verify: `index.html` charts have no controls, `klima.html` same charts do (confirmed: 0 vs 13 `.chart-controls`)
- [x] 4.4 Per-chart provenance line under each canvas, from the known-issues join → verify: chart 3 (`napi_vizallas`) shows the `agard-vizallas-gaps` 2010 note
- [x] 4.5 Charts **2, 3, 5, 6, 7, 9, 10, 11** — no dependency on `fix-vizhaztartas-column-shift`
- [x] 4.6 Charts **1, 4, 8, 12** — unblocked: `fix-vizhaztartas-column-shift` already archived 2026-08-25 (user-confirmed), `vizhaztartas_keszletvaltozas` present in DB. Implemented alongside the rest
- [x] 4.7 `index.html` — Tier 1 only (charts 1–3), each with a short Hungarian caption stating the finding
- [x] 4.8 `klima.html` — all 12, Tier 1→3, sticky TOC via Bootstrap scrollspy, offcanvas below `lg`

## 5. Adattár, Forrás, deployment

- [x] 5.1 `adattar.html` — Bootstrap tabs per DB table; lazy `fetch` on tab open; filter/sort/paginate in vanilla JS (~100 lines) → verify: opening the page issues no `daily_obs.json` request until that tab is selected (confirmed in headless Chromium: only `documents.json` fetched on load, `daily_obs.json` fetched only after clicking its tab)
- [x] 5.2 `forras.html` — methodology, AI caveat in full, source URL, coverage matrix from `data/coverage.json`, CDN/offline note
- [x] 5.3 Build-time assertion: no absolute `/`-rooted asset or fetch path in any generated page → verify: assertion fails on a deliberately introduced `/data/x.json`
- [x] 5.4 `.github/workflows/pages.yml` — checkout → setup-python → `python3 generate_site.py` → `upload-pages-artifact` (path `output/site`) → `deploy-pages`; Pages source set to GitHub Actions (workflow written; repo Pages source setting + first push are a deploy action, gated on user confirmation, see 5.5)
- [ ] 5.5 Deploy and verify **in production, not locally**: all four pages load under `/<repo>/`, charts render, `adattar.html` fetches lazily, banner present on every page — ⚠️ requires pushing to `origin/main` and setting repo Pages source to Actions; needs explicit user go-ahead before pushing
- [x] 5.6 Mark superseded: `docs/csapadek-chart.md`, `docs/csapadek-heatmap.md`, and the three chart scripts in `docs/file-index.md`. Code and outputs stay — flag, don't delete
- [x] 5.7 Register `generate_site.py`, `site/`, `output/site/`, `.github/workflows/pages.yml` in `docs/file-index.md`
- [x] 5.8 Close the "Output medium undecided" line in `docs/climate-charts-plan.md`
