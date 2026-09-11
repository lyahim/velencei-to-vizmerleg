## MODIFIED Requirements

### Requirement: Deep-dive page carries all twelve charts

`klima.html` SHALL present every chart in the implemented chart set — the twelve
`docs/climate-charts-plan.md` charts plus the groundwater overlay chart ("A tó és a talajvize
együtt lélegzik", lake level and talajvíz monthly means in Baltic datum, drought years shaded)
— with a table of contents and interactive controls.

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

#### Scenario: Groundwater overlay included

- **WHEN** `klima.html` is viewed
- **THEN** the groundwater overlay chart is present with the other deep-dive charts
- **THEN** its axis is Baltic datum (m.a.f.) shared by lake level and talajvíz series
- **THEN** 2019–2022 drought years are visually distinguished

## RENAMED Requirements

### Requirement: Deep-dive page carries all twelve charts
- FROM: `Deep-dive page carries all twelve charts`
- TO: `Deep-dive page carries the full chart set`

---

### Requirement: Source page documents method and coverage

`forras.html` SHALL describe the data, the extraction method, the AI caveat in full, the
original source URLs, and a year × table coverage matrix. The yearbook source (KDT-VIZIG) and
the VRA földalatti source (OVF Vízrajzi Adatbázis, data.vizugy.hu) SHALL each be attributed
with their scope.

#### Scenario: Source attribution

- **WHEN** `forras.html` is viewed
- **THEN** it links to the KDT-VIZIG source page for the yearbooks
- **THEN** it links to the OVF VRA portal (data.vizugy.hu) as the source of the földalatti
  víz series, naming the wells and their observation period

#### Scenario: Groundwater freshness stated

- **WHEN** `forras.html` is viewed
- **THEN** the last VRA fetch date for földalatti data is displayed

#### Scenario: Method and caveat stated

- **WHEN** `forras.html` is viewed
- **THEN** it explains that yearbook values were transcribed from PDFs by AI-assisted
  processing and may diverge from the source
- **THEN** it explains that földalatti values are copied unmodified from the VRA API

#### Scenario: Coverage matrix rendered

- **WHEN** `forras.html` is viewed
- **THEN** a year × table matrix distinguishes present, pending, skipped and unconfirmed data

## ADDED Requirements

### Requirement: Archive page carries the groundwater depth panel

`adattar.html` SHALL present the talajvíz depth panel ("Milyen mélyen van a víz a lábunk
alatt?"): filled depth-area small multiples in Relativ mode (cm below surface), one panel per
well for the seven registry wells.

#### Scenario: Panel shows all wells

- **WHEN** `adattar.html` is viewed
- **THEN** all seven registry wells appear as small multiples with their Hungarian names

#### Scenario: Depth reads downward

- **WHEN** a well's depth series is rendered
- **THEN** greater depth (larger cm value) renders as a deeper area, so drought lows are
  visually low

#### Scenario: Observation-density change is not read as level change

- **WHEN** the panel spans the 2018 telemetry switchover
- **THEN** the rendered series is aggregated to monthly means so pre-2018 manual and post-2018
  automated observation densities remain visually comparable
