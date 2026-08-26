## Why

`output/vizmerleg.db` holds 40 years of Lake Velence hydrological data extracted from KDT-VIZIG yearbooks. Nothing presents it. `docs/climate-charts-plan.md` specifies 12 charts across three tiers, with a per-chart rationale — a narrative arc from "the lake is drying" through mechanism to adaptation — but the plan is unimplemented and its output medium was left undecided.

Three chart scripts exist (`generate_csapadek_chart.py`, `generate_csapadek_heatmap.py`, `generate_temp_chart.py`). They predate the plan, cover fragments of charts 2/5/6/7, and each emit a standalone HTML file in a different visual idiom. None carries provenance or a data-quality caveat.

The data is AI-transcribed from scanned PDFs and may diverge from the source. That has to be stated where a reader will actually see it, not buried on an about page.

## What Changes

A static Hungarian site at `output/site/`, generated from the DB, served by GitHub Pages.

**Pages** (shared nav + persistent caveat banner)

| Page | Role |
|---|---|
| `index.html` | Tier 1 narrative — charts 1–3, fixed views, short Hungarian caption each |
| `klima.html` | All 12 charts, Tier 1→3, sticky TOC, per-chart controls |
| `adattar.html` | Filterable raw tables + station browser, lazy-loaded |
| `forras.html` | Methodology, AI caveat in full, coverage matrix, source link |

**Stack** — Bootstrap 5 + Chart.js, both CDN. No Vue: Bootstrap's own components cover nav, scrollspy TOC, offcanvas, collapse, tabs and alerts, leaving ~120 lines of vanilla JS. Chart.js is imperative and stateful; wrapping it in a reactive proxy is a known friction point, so the framework would have to be disabled exactly where it would otherwise help.

**Generation** — `generate_site.py` reads the DB once at generate time and writes:

- `data/charts/*.json` — pre-aggregated, one file per chart, small
- `data/tables/*.json` — one per DB table, fetched only when `adattar.html` opens that table
- `data/coverage.json` — year × table coverage matrix
- the four HTML pages, by substituting into `site/templates/*.html`

Templates are real HTML files under `site/` (version-controlled source), not Python strings. Substitution is `str.replace` on a handful of placeholders — no template engine, no new dependency.

**Transparency** — the caveat banner sits under the nav on every page. `forras.html` carries a year × table coverage matrix built from **both** the DB (what exists) and `import_tracker.md` statuses (what is `pending`, `skip`, `verify`, `error`). A DB-only matrix would render unprocessed years identically to years with no such data — a misleading claim on a site whose premise is candour about its own reliability. Each chart renders the `display_hu` note of any matching `docs/known-issues.md` row.

**Deployment** — GitHub Actions workflow: checkout → `generate_site.py` → `upload-pages-artifact` → `deploy-pages`. Pages source is Actions, not a branch, so `docs/` keeps its meaning and the site never needs to live there. `output/site/` is gitignored; only `vizmerleg.db` stays version-controlled, and the site refreshes whenever an extraction turn commits the DB.

**Docs hygiene** (requested alongside)

- Merge `docs/file-index-docs.md` + `docs/file-index-scripts.md` back into a single `docs/file-index.md`. The three-file split indexes seven files.
- Mark `docs/csapadek-chart.md` and `docs/csapadek-heatmap.md` superseded; mark the three chart scripts superseded in the file index. Code stays — `AGENTS.md` says flag dead code, don't delete.
- New `docs/README.md` stating `docs/` is project documentation, not the published site.

## Capabilities

### New Capabilities

- `site-data-export`: `generate_site.py` reads `output/vizmerleg.db`, `import_tracker.md` and `docs/known-issues.md` at generate time and writes a self-describing JSON snapshot plus four HTML pages into `output/site/`.
- `static-site`: a four-page Hungarian site presenting the water-balance and climate record, carrying its own provenance and data-quality caveats, deployable to GitHub Pages with no runtime database access.

### Modified Capabilities

- `csapadek-chart`, `csapadek-heatmap`: marked superseded. Scripts and outputs remain; the site does not link to them.

## Impact

- New: `generate_site.py`, `site/templates/*.html`, `site/assets/{site.css,site.js}`, `.github/workflows/pages.yml`, `docs/README.md`
- New generated (gitignored): `output/site/**`
- Modified: `docs/file-index.md` (absorbs both splits), `.gitignore`, `docs/csapadek-chart.md`, `docs/csapadek-heatmap.md`
- Deleted: `docs/file-index-docs.md`, `docs/file-index-scripts.md`
- Reads at generate time: `output/vizmerleg.db`, `import_tracker.md`, `docs/known-issues.md`, `docs/climate-charts-plan.md` (chart ids)
- Dependencies: Python 3 + pandas (already used); Bootstrap 5 + Chart.js via CDN
- No DB writes. No runtime DB access.

## Dependencies

**`fix-vizhaztartas-column-shift` must land first for charts 1, 4, 8 and 12.** Those splice `historical_monthly` 1971–1995 onto `monthly_balance` 1996+, and until B1/B2 complete the historical columns are mislabelled — the charts would present outflow as withdrawal and catchment inflow as reservoir inflow, precisely at the era boundary. Chart 12 additionally needs `vizhaztartas_keszletvaltozas`, which B2 extracts.

Charts 2, 3, 5, 6, 7, 9, 10, 11 have no such dependency.

## Risks

- **`AGENTS.md` needs edits and only the user may make them.** Its routing table and documentation-update protocol name `docs/file-index-docs.md` and `docs/file-index-scripts.md` (11 references). The docs-hygiene tasks are blocked until those edits are proposed and approved.
- **Extraction is ~32 tracker rows from complete.** The site ships against a moving dataset. Mitigated by design: the coverage matrix states what is missing, and CI regenerates on every DB commit.
- **CDN dependency** → no internet, no charts. Consistent with the three existing chart scripts; noted on `forras.html`.
- **Relative paths are load-bearing.** Project Pages serve from `https://<user>.github.io/<repo>/`; any absolute `/data/...` path 404s in production while working locally. Enforced by a build-time check.
