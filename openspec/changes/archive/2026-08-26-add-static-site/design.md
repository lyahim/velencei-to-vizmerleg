## Context

The project is a data-archaeology pipeline: PDFs → `output/vizmerleg.db`. No build system, no package, no server, no test suite. Chart scripts are flat files run as `python3 <script>.py`, emitting self-contained HTML into `output/`.

`docs/climate-charts-plan.md` supplies the editorial spine: 12 charts, tiered, each with a stated rationale. That plan is the site's content model — this change is its delivery mechanism, not a re-planning of it.

Source: <https://www.kdtvizig.hu/kozep-dunantuli/vizgazdalkodas-vizszolgaltatas/csatolmanyok/velencei-to-vizmerleg/$rppid0x1187710x14_pageNumber/1>

## Goals / Non-Goals

**Goals:**
- Present all 12 planned charts in Hungarian, in the plan's narrative order.
- Make the AI-transcription caveat unavoidable, on every page.
- State coverage and known defects honestly, per chart and in aggregate.
- Zero runtime database access — the DB is read once, at generate time.
- Deploy to GitHub Pages without displacing `docs/`.

**Non-Goals:**
- Translation. Hungarian only, per the project's language convention.
- A build step, bundler, or npm dependency.
- Server-side anything, auth, or user state.
- Editing the DB. This change is read-only against `vizmerleg.db`.
- Waiting for extraction to finish. The site ships against current data and refreshes on commit.

## Decisions

### Decision 1: Bootstrap 5 + Chart.js, no Vue

**Chosen:** Bootstrap 5 for layout and interaction primitives, Chart.js for charts, ~120 lines of vanilla JS for the rest.

**Alternatives considered:**
- Vue 3 from CDN driving chart panels and the data table — the original direction.

**Rationale:** Bootstrap's own components already cover navbar/collapse, **scrollspy** (the `klima.html` sticky TOC through 12 charts), offcanvas (mobile TOC), collapse/accordion (per-chart control panels), tabs (`adattar.html` table switcher) and alert (the caveat banner). What remains is fetch + Chart.js instantiation (framework-agnostic), ~20 lines of control handlers, and ~100 lines of table filter/sort/paginate.

There is also a concrete technical argument: Chart.js is imperative and holds substantial internal state. A reactive proxy wrapping a chart instance degrades performance and produces hard-to-trace bugs; the correct Vue pattern is to hold the instance in `shallowRef`, i.e. to opt out of reactivity exactly where the framework would otherwise earn its place. `AGENTS.md`: "No abstractions for a single call site."

**Reversal condition:** if `adattar.html` grows cross-filtering across tables, saved views, or joins, hand-written DOM updates start to hurt and a framework pays off.

### Decision 2: Template files, not Python strings

**Chosen:** `site/templates/*.html` as version-controlled source; `generate_site.py` substitutes a small placeholder set with `str.replace`.

**Alternatives considered:**
- Python f-string templates, as the three existing chart scripts do — consistent with the project, but the pages carry substantial hand-written Hungarian prose, which is miserable to edit inside string literals.
- Jinja2 — a new dependency for a handful of substitutions.

**Rationale:** Decision 1 makes this work. Because chart behaviour lives in `site/assets/site.js` rather than in per-chart HTML, the templates hold prose plus mount points, and the placeholder set stays small:

```
{{NAV}} {{BANNER}} {{FOOTER}} {{DATA_VERSION}} {{GENERATED_AT}}
```

`str.replace` is adequate for that and adds nothing to install.

### Decision 3: Chart panels are declared in HTML, hydrated by JS

**Chosen:** Templates declare `<div class="chart-panel" data-chart="vizhaztartas" data-controls="false">`. `site.js` scans for `.chart-panel`, fetches `data/charts/<id>.json`, builds the Chart.js instance, and renders the controls only when `data-controls="true"`.

**Rationale:** One code path, two presentations. `index.html` gets fixed narrative views — the chart shows exactly what the surrounding paragraph claims. `klima.html` gets year filters and series toggles on the same charts. Narrative integrity and explorability without duplicated chart code.

### Decision 4: Two JSON tiers — pre-aggregated charts, raw tables

**Chosen:** `data/charts/*.json` holds exactly what a chart plots, aggregated in Python. `data/tables/*.json` holds per-table rows, fetched only on demand.

**Alternatives considered:**
- One combined JSON — every page pays for `daily_obs` (84k rows) to render an annual bar chart.
- Client-side aggregation from raw tables — moves work to the browser for no benefit, given the data is static.

**Rationale:** The narrative pages stay light (~50 KB). Pages gzips text automatically and JSON compresses ~8–10×, so even the largest table ships as a few hundred KB, and only when asked for. Aggregating in Python also keeps the SQL — including the `COALESCE(final, adj, raw)` rules and `value IS NOT NULL` filters — in one auditable place.

### Decision 5: Coverage matrix from DB **and** tracker

**Chosen:** `data/coverage.json` merges per-table/per-year row counts from the DB with per-row status from `import_tracker.md`.

**Alternatives considered:**
- DB only — trivially computed.

**Rationale:** A DB-only matrix cannot distinguish "no such data exists for this year" from "not processed yet" — both render as an empty cell. On a site whose stated premise is that its data is AI-derived and may be wrong, silently presenting a backlog as an absence is the one failure mode most worth avoiding. The tracker holds `pending`, `skip`, `verify`, `error`; the matrix shows all four.

Parsing markdown tables is brittle. Mitigation: parse defensively, and treat an unparseable row as `unknown` rather than crashing or omitting it.

### Decision 6: Per-chart notes from `docs/known-issues.md`

**Chosen:** `generate_site.py` reads the registry, joins its `charts` column to chart ids, and renders each matching `display_hu` under the chart. A `—` suppresses the note.

**Rationale:** Keeps caveats next to the claim they qualify. The registry is the single edit point; the site has no second copy to drift.

### Decision 7: GitHub Actions deployment, `output/site/` gitignored

**Chosen:** Pages source = GitHub Actions. Workflow runs `generate_site.py` and deploys the artifact. Generated output never enters git.

**Alternatives considered:**
- Deploy from branch `/docs` — forces the site into `docs/`, displacing project documentation, requiring ~23 reference updates and an `AGENTS.md` rewrite, and committing regenerated output.
- `gh-pages` branch — leaves `docs/` alone but needs a push step and offers nothing over Actions.

**Rationale:** `docs/` keeps its meaning. Only `vizmerleg.db` is version-controlled, so the ~32 remaining extraction turns don't each push megabytes of regenerated JSON into history. The site rebuilds whenever the DB is committed, which is exactly the desired refresh trigger.

### Decision 8: Pages-specific hardening

**Chosen:**
- `output/site/.nojekyll` — Pages runs Jekyll by default, which skips `_`-prefixed paths and rewrites content.
- Relative fetch paths only (`./data/...`). Project Pages serve under `/<repo>/`, so an absolute `/data/...` resolves to the domain root and 404s in production while working locally.
- Cache-bust via `?v={{DATA_VERSION}}` on every fetch, where `DATA_VERSION` is the generate timestamp.

**Rationale:** Each of these fails silently or only in production. A build-time assertion for absolute paths (task 5.3) is cheaper than diagnosing it after deploy.

## Risks / Trade-offs

- **`AGENTS.md` is user-owned.** The docs-hygiene tasks require edits to its routing table and documentation-update protocol. They are gated on user approval and can land separately from the site.
- **Markdown parsing of `import_tracker.md`** → brittle. See Decision 5 mitigation.
- **CDN dependency** → no internet, no charts. Same trade-off as the existing chart scripts; stated on `forras.html`.
- **Moving dataset** → coverage matrix and `GENERATED_AT` make the snapshot's age explicit rather than hiding it.
- **12 charts on one page** → heavy on mobile. Mitigation: charts render lazily via `IntersectionObserver`; the TOC is offcanvas below `lg`.

## Migration Plan

1. Docs hygiene and `.gitignore` first — no dependencies, unblocks nothing, but small and self-contained.
2. `generate_site.py` with the JSON export, verified by inspecting written files.
3. Templates and assets; charts 2, 3, 5, 6, 7, 9, 10, 11 (no dependency on the column-shift fix).
4. Charts 1, 4, 8, 12 after `fix-vizhaztartas-column-shift` lands.
5. Workflow last, once the site renders correctly from a local generate.

Rollback: delete `output/site/` and disable the workflow. Nothing else is touched.

## Open Questions

- **Does `adattar.html` offer CSV download?** Leaning yes — trivial from already-fetched JSON, and it serves the "give me the numbers" audience the archive page exists for. Not specified below; decide during implementation.
- **Is a chart-image export worth it?** Chart.js can emit PNG via `toBase64Image()`. Useful for anyone citing the site. Deferred.
