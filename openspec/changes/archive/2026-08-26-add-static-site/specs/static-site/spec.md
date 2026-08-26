## ADDED Requirements

### Requirement: Four Hungarian pages with shared navigation

The site SHALL consist of `index.html`, `klima.html`, `adattar.html` and `forras.html`, all in Hungarian, sharing one navigation bar. The site name is "Velencei-tó vízmérleg".

#### Scenario: Navigation is present on every page

- **WHEN** any of the four pages is loaded
- **THEN** the nav offers Áttekintés, Klíma, Adattár and Forrás
- **THEN** the current page is marked active

#### Scenario: No translation layer

- **WHEN** any page is viewed
- **THEN** all prose, labels, station names and column labels are Hungarian
- **THEN** identifiers keep the Hungarian forms the database uses

---

### Requirement: Persistent AI-transcription caveat

Every page SHALL display a caveat banner directly under the navigation, linking to `forras.html`.

#### Scenario: Banner on all pages

- **WHEN** any of the four pages is loaded
- **THEN** a banner states that the data was produced by AI-based processing and may differ from the source
- **THEN** the banner links to `forras.html`

#### Scenario: Banner precedes content

- **WHEN** a page is loaded
- **THEN** the banner appears above the first chart or table

---

### Requirement: Narrative page carries fixed chart views

`index.html` SHALL present Tier 1 charts 1–3 in the order given by `docs/climate-charts-plan.md`, each with a short Hungarian caption stating the finding, and without interactive controls.

#### Scenario: Tier 1 in plan order

- **WHEN** `index.html` is viewed
- **THEN** charts appear in the plan's Tier 1 order
- **THEN** each is accompanied by explanatory Hungarian text

#### Scenario: Narrative charts are fixed

- **WHEN** a chart on `index.html` is rendered
- **THEN** it displays the preset view, with no year filter or series toggles

---

### Requirement: Deep-dive page carries all twelve charts

`klima.html` SHALL present all 12 charts across Tiers 1–3, with a table of contents and interactive controls.

#### Scenario: Same charts, now adjustable

- **WHEN** a chart on `klima.html` is rendered
- **THEN** a year range control and series toggles are available
- **THEN** adjusting them updates the existing chart instance

#### Scenario: Table of contents tracks position

- **WHEN** the reader scrolls
- **THEN** the table of contents highlights the current chart

#### Scenario: Table of contents adapts to narrow screens

- **WHEN** viewport width is below the `lg` breakpoint
- **THEN** the table of contents is presented as an offcanvas panel

#### Scenario: Charts render lazily

- **WHEN** `klima.html` first loads
- **THEN** only charts within the viewport are initialised

---

### Requirement: Charts state their provenance

Every chart SHALL display its data source and any matching known-issue note.

#### Scenario: Known defect surfaced at the chart

- **WHEN** a chart's id matches a `docs/known-issues.md` row with non-empty `display_hu`
- **THEN** that text is shown beneath the chart

#### Scenario: Source named

- **WHEN** any chart is displayed
- **THEN** the database table or tables behind it are named

---

### Requirement: Archive page exposes raw data

`adattar.html` SHALL let a reader browse database tables with filtering, sorting and pagination, loading each table only when selected.

#### Scenario: Table selection triggers load

- **WHEN** the reader selects a table not yet viewed
- **THEN** that table's JSON is fetched
- **THEN** rows are displayed paginated

#### Scenario: Filtering and sorting

- **WHEN** the reader filters by year or station, or sorts by a column
- **THEN** the displayed rows update accordingly

---

### Requirement: Source page documents method and coverage

`forras.html` SHALL describe the data, the extraction method, the AI caveat in full, the original source URL, and a year × table coverage matrix.

#### Scenario: Source attribution

- **WHEN** `forras.html` is viewed
- **THEN** it links to the KDT-VIZIG source page for the yearbooks

#### Scenario: Method and caveat stated

- **WHEN** `forras.html` is viewed
- **THEN** it explains that values were transcribed from PDFs by AI-assisted processing and may diverge from the source

#### Scenario: Coverage matrix rendered

- **WHEN** `forras.html` is viewed
- **THEN** a year × table matrix distinguishes present, pending, skipped and unconfirmed data

---

### Requirement: Self-contained, CDN-only dependencies

The site SHALL depend on no build step and no local asset pipeline. Bootstrap 5 and Chart.js SHALL load from CDN.

#### Scenario: No build artefacts

- **WHEN** the site is generated
- **THEN** no bundler, package manifest or compiled asset is produced

#### Scenario: Offline behaviour stated

- **WHEN** the site is loaded without internet access
- **THEN** `forras.html` documents that charts require CDN access to render

---

### Requirement: GitHub Pages compatibility

The generated site SHALL deploy to GitHub Pages from a GitHub Actions workflow, served from a repository subpath.

#### Scenario: Jekyll disabled

- **WHEN** `output/site/` is generated
- **THEN** it contains a `.nojekyll` file

#### Scenario: Paths are relative

- **WHEN** any generated page is inspected
- **THEN** no asset or fetch path begins with `/`

#### Scenario: Site works under a repository subpath

- **WHEN** the site is served from `https://<user>.github.io/<repo>/`
- **THEN** all pages, assets and data files resolve

#### Scenario: Regenerated data is not stale-cached

- **WHEN** a page fetches a data file
- **THEN** the request carries the current `DATA_VERSION` as a cache-busting parameter

#### Scenario: Deployment is automated

- **WHEN** a commit changes `output/vizmerleg.db` on the default branch
- **THEN** the workflow regenerates the site and deploys it

---

### Requirement: Superseded chart scripts are flagged, not deleted

The three pre-existing chart scripts and their docs SHALL be marked superseded once the site covers their charts.

#### Scenario: Marked in the file index

- **WHEN** `docs/file-index.md` is read
- **THEN** `generate_csapadek_chart.py`, `generate_csapadek_heatmap.py` and `generate_temp_chart.py` are marked superseded by the site

#### Scenario: Code retained

- **WHEN** the change is complete
- **THEN** the three scripts and their generated HTML files still exist
