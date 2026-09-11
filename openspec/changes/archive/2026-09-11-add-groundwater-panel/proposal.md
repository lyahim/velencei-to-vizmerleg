## Why

The public site narrates the lake's water crisis entirely from yearbook-derived data. The
"catchment inflow collapse" chart (chart 4) hypothesizes that drier subsurface storage consumes
runoff before it reaches the lake — but the site has no direct evidence for the subsurface, only
inference. Live probing of the OVF VRA API (verified 2026-09-11) shows it carries 35-year
talajvíz (shallow groundwater) observation series for seven wells within 15 km of the lake,
including Pákozd 3 km away, in both felszín-alatti mélység (cm) and Baltic datum (m.a.f.). The
Pákozd series shows the 2019–2022 drought as a ~1 m water-table drop with only partial recovery
by 2024 — independent, direct confirmation of the drought mechanism the site already claims.

## What Changes

- New `groundwater_obs` table in `output/vizmerleg.db` storing VRA talajvíz observations
  (adatFajtaKod 69) for the seven lake-adjacent wells, both value modes: Relativ (cm below
  surface) and Balti (m.a.f.), 1990–present.
- New `documents` row marking VRA földalatti as its own source family (precedent: doc_id 42/43
  for VRA surface discharge), so provenance stays explicit per the established convention.
- New script `scripts/fetch_groundwater.py`: VRA API → SQL insert block (operator applies via
  the existing `sqlite3 … < /tmp/…sql` flow; no silent DB writes from scripts).
- `scripts/generate_site.py` exports new pre-aggregated JSON from `groundwater_obs`.
- Two new public charts:
  - **Chart A — "A tó és a talajvize együtt lélegzik"** (klima page): lake level (m.a.f.) and
    Pákozd/Agárd/Kápolnásnyék talajvíz (Balti m.a.f.) monthly means on one axis, drought years
    shaded.
  - **Chart B — "Milyen mélyen van a víz a lábunk alatt?"** (adattár page): filled
    depth-area small multiples per well, Relativ cm.
- Forrás page gains the new data source entry: OVF Vízrajzi Adatbázis (data.vizugy.hu), with
  provenance note and last-fetched date.
- Documentation corrections/updates: `docs/vra-api.md` vmoType table fix (12 = talajvíz,
  13 = rétegvíz, 14 = hidromet, 1 = forrás), new data-type codes (69, 70, 76, 299, 303, 304),
  Balti mode for wells; `docs/file-index.md` row for the new script; `EXTRACTION_GUIDE.md` §14
  provenance entry; `import_tracker.md` rows for the ingest; §15 registry entry for the table.

Out of scope (deferred): rétegvíz wells (adatFajtaKod 70, chart C), hóvízegyenérték (76),
talajnedvesség/talajhő (299/303), any pre-1990 backfill.

## Capabilities

### New Capabilities

- `groundwater-data`: storage, provenance, and refresh of VRA földalatti (talajvíz) observation
  series in `vizmerleg.db` — table shape, source-family separation, fetch script behavior,
  no-derivation rule.

### Modified Capabilities

- `static-site`: two new chart panels (klima chart A, adattár chart B) and the new VRA data
  source entry on the forrás page.
- `site-data-export`: `generate_site.py` additionally reads `groundwater_obs` and writes its
  JSON export; database stays read-only at generate time.

## Impact

- **Database**: `output/vizmerleg.db` gains `groundwater_obs` table + one `documents` row.
  No existing table changes.
- **Scripts**: new `scripts/fetch_groundwater.py`; `scripts/generate_site.py` extended (new
  export + panels hydrate).
- **Site**: `site/templates/klima.html`, `site/templates/adattar.html`,
  `site/templates/forras.html`, `site/assets/site.js` extended.
- **CI**: `.github/workflows/pages.yml` unchanged — data lives in the DB, build reads DB.
- **Docs**: `docs/vra-api.md`, `docs/file-index.md`, `EXTRACTION_GUIDE.md` §14/§15,
  `import_tracker.md`.
- **External dependency**: VRA API (data.vizugy.hu / vmservice.vizugy.hu), guest token, no key.
  Fetch happens on operator machines, not in CI.
- **Known risk**: chart A needs the Agárd vízállás gauge datum (cm → m.a.f. conversion). If the
  datum is not recoverable from existing metadata, chart A falls back to anomaly-index overlay
  (design documents both paths).
