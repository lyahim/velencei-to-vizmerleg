# VRA — data.vizugy.hu connection manual

How to connect to OVF Vízrajzi Adatbázis (VRA) open-data API. Verified working 2026-09-09.

## What it is

- OVF (Országos Vízügyi Főigazgatóság) free data portal. Since 2024-07-15.
- Daily/hourly series per network station: vízállás, vízhozam, vízhőmérséklet, csapadék, léghőmérséklet, talaj, talajvíz, rétegvíz.
- No registration. No API key. Guest JWT per session.
- License (download-tool welcome dialog): downloaded data usable freely and free of charge, without restriction, provided the source (OVF or the competent VÍZIG) is credited. Last ~1 year of series typically unprocessed — "tájékoztató jellegű"; for official proceedings request verified data via ovf.hu.
- SPA at `https://data.vizugy.hu/` (Angular). SPA calls hidden REST API. This doc documents that API directly.

## Architecture

```
browser SPA      https://data.vizugy.hu/          (Angular shell, no useful static HTML)
auth endpoint    https://data.vizugy.hu/AuthApi/auth/token
data API         https://vmservice.vizugy.hu/vraquery/...
```

- Auth issues Bearer token. Data API demands Bearer + Origin. Both verified via curl.
- Swagger page at `https://vmservice.vizugy.hu/vraquery/swagger` = default petstore config. Decoy. Ignore.
- SPA JS bundle (`data.vizugy.hu` index → `main.*.js`, ~3.5 MB) holds all endpoint names + request builders. Source of every fact below. Re-grep bundle if API changes: `grep -oE '.{100}_apiRootUrl.{200}' main.*.js`.

## Step 1 — get guest token

```bash
TOKEN=$(curl -sk -H "Origin: https://data.vizugy.hu" \
  "https://data.vizugy.hu/AuthApi/auth/token" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

- `Origin: https://data.vizugy.hu` header REQUIRED. Without it: HTTP 403 `Forbidden: Unauthorized origin`.
- Response: `{"access_token":"eyJ..."}`. JWT, claim `nameid=opendatauser`.
- TTL ~900 s (`nbf`→`exp` in JWT). Re-fetch when expired. No refresh call needed — just re-GET.
- curl `-k` used: cert verification flaky from this machine. Harmless here (public data, token is guest).

## Step 2 — station list

```bash
curl -sk -H "Authorization: Bearer $TOKEN" -H "Origin: https://data.vizugy.hu" \
  "https://vmservice.vizugy.hu/vraquery/Vra/InternetVmo/11/false"
```

- Path: `Vra/InternetVmo/{vmoType}/false`.
- vmoType mapping decoded from SPA bundle (`getStationType`), corrected 2026-09-11 (earlier table here was wrong):

| vmoType | Station type | Network | Stations (2026-09-11) |
|---|---|---|---|
| 11 | surface | felszíni vízrajz — all project gauges live here | ~1195 |
| 1 | spring | forrás (Hévíz, Tapolca…) | 7 |
| 12 | nearsurface | **talajvíz megfigyelő kutak** — project wells live here | ~2030 |
| 13 | undersurface | **rétegvíz kutak** (Zámoly-1, Csákvár-1…) | 524 |
| 14 | hidromet | hidrometeorológiai automata (ghosts exist: Tsz 700279 Agárd lists but returns no data) | 441 |

- Response: JSON array. Key fields: `Tsz` (törzsszám = station id), `Nev` (station name), `Telepules`, lat/lon. Well lists (12/13) also carry `Npt` (13 only), `Aft` = **dataTransportType** code (not aquifer), `Uzem`.
- Search by name substring, e.g. `Zámoly`, `Pátka`.

## Step 3 — data series

```bash
curl -sk -X POST \
  -H "Authorization: Bearer $TOKEN" -H "Origin: https://data.vizugy.hu" \
  -H "Content-Type: application/json" \
  -d @request.json \
  "https://vmservice.vizugy.hu/vraquery/TS/TsShortList"
```

Request body (daily mean, one station, one year):

```json
{
  "torzsszamList": [142026],
  "adatFajtaKod": 87,
  "adatTipusKod": 100,
  "startTime": "2002-01-01T00:00:00",
  "endTime": "2003-01-01T00:00:00",
  "dataExtFilter": 0,
  "valueFilter": "Relativ",
  "amKodFilter": [0],
  "aggregateFilters": {
    "rangeType": "daily",
    "aggregateType": "mean",
    "aggregateRangePosition": "none",
    "maxNullDayCount": 0,
    "maxNullDayRangeLengh": 0
  }
}
```

Field notes:

| Field | Meaning |
|---|---|
| `torzsszamList` | Station törzsszám array. Multiple stations allowed (one result element each). |
| `adatFajtaKod` | Data type code. See table below. |
| `adatTipusKod` | Always `100` in SPA. Leave `100`. |
| `startTime`/`endTime` | Local time, `YYYY-MM-DDTHH:MM:SS`. Use `next-year-01-01` as endTime for full year — `Dec-31T00:00:00` omits Dec 31. |
| `dataExtFilter` | `0` for non-precip. Precip (71): `60` hourly, `1440` daily, `null` all. Codes 299/303: `null`. |
| `valueFilter` | `"Relativ"` (gauge datum / depth below surface) or `"Balti"` (Baltic sea level, m.a.f.). Works for talajvíz wells too (code 69) — Balti gives the water table elevation directly (e.g. Pákozd 109.3–110.71 m.a.f. 1993–2026), enabling common-datum overlay with lake level. `"Relativ"` matches yearbook tables. |
| `amKodFilter` | `[0]` always in SPA. |
| `aggregateFilters` | Daily mean: block above verbatim. Omit whole block for raw (hourly) data. |
| `dailyFilters` | Hourly variant exists (`centerMin` 0..1440 step 60, `dailyRangeFind:"nearestime"`). Not verified. |

Data type codes (from SPA bundle, `haf` objects):

| Code | Name | Unit |
|---|---|---|
| 68 | Felszíni vízállás | cm |
| 87 | Felszíni vízhozam | m³/s |
| 85 | Vízhő a vízfelszín közelében | °C |
| 89 | Vízhő a mederfenék közelében | °C |
| 71 | Csapadékösszeg | mm |
| 81 | Léghőmérséklet | °C |
| 82 | Minimum hőmérséklet | °C |
| 83 | Maximum hőmérséklet | °C |
| 75 | Hóvastagság | cm |
| 76 | Hóvízegyenérték | mm |
| 92 | Forrás vízállás | cm |
| 74 | Forrás vízhozam | l/s |
| 69 | **Talajvízállás** | cm |
| 70 | **Rétegvízszint** | m |
| 299 | Talajnedvesség | % |
| 303 | Talajhőmérséklet | °C |
| 304 | Legnedvesség | % |

- `stationtype` per code (SPA bundle): 68/87/85/89 surface, 71/81/82/83/75/76/299/303/304 hidromet, 92/74 spring, 69 nearsurface (vmoType 12), 70 undersurface (vmoType 13).

Response:

```json
[{"ItemId": 142026, "TsItemList": [{"UTCTime": "2001-12-31T23:00:00Z", "Adat": 0.017}, ...]}]
```

- One array element per requested station. `TsItemList` = time series.
- `UTCTime` in UTC. Day mapping: item timestamp = local midnight expressed in UTC. CET winter: `23:00Z` of day D-1 = local day D. CEST summer: `22:00Z` of day D-1 = local day D (verified 2026-09-09). Convert with `Europe/Budapest` timezone, take date — handles both.
- `Adat` = float, full precision. Not rounded like yearbook print.

## Step 4 — report download (not verified)

- `POST {vraquery}Report/MI`, response blob (PDF/Excel). SPA "MI report" button. Body shape unknown. Unverified — decode from bundle if needed.

## Project station map

VRA törzsszám ↔ `daily_obs.station_id` (verified via 2024 value comparison, Jan–Mar, 182 days):

| VRA Tsz | VRA Nev | station_id | Match quality 2024 Jan–Mar |
|---|---|---|---|
| 142026 | Zámoly | `zamoly_vizhozam` | 87/91 within ±0.02 m³/s; 2 outliers on flood-rise day (7:00-obs vs daily-mean) |
| 142421 | Pátka | `patka_vizhozam` | 91/91 within ±0.02 m³/s, mean diff +0.0001 |
| 818 | Agárd | `agard_vizallas` | API responds, not compared |
| 819 | Kőrakáspuszta | `korakaspuszta_vizhozam` | API responds 2024, not compared |
| 820 | Kápolnásnyék | `kapolnasnyekvizhozam` | API responds 2024, not compared |
| 140043 | Kisfalud-puszta | `kisfalud_vizhozam` | not queried |
| 140049 | Fornapuszta | not in DB daily set | — |
| 142098 | Csákvár | `csakvar_vizhozam` | not queried |

Tározó (reservoir) gauges — vízállás yes, vízhozam NO:

| VRA Tsz | VRA Nev | VRA series |
|---|---|---|
| 142029 | Zámolyi-tározó | vízállás 2002 ✓ (364 days). vízhozam EMPTY even 2024. |
| 142080 | Pátkai-tározó | vízhozam EMPTY even 2024. |

Confirmed 2002 + 2025 availability (the two DB gap years):

| Tsz | Station | 2002 | 2025 |
|---|---|---|---|
| 142026 | zamoly_vizhozam | 365/365 days (inserted, doc_id=42) | 365/365 days (inserted, doc_id=43) |
| 142421 | patka_vizhozam | 365/365 days (inserted, doc_id=42) | 363/365 days (inserted, doc_id=43; May 12+25 absent in VRA) |

## Földalatti hálózat (talajvíz) — project wells

Seven nearsurface (vmoType 12) wells ingested 2026-09-11 into `groundwater_obs` via `scripts/fetch_groundwater.py` (see EXTRACTION_GUIDE §14 for provenance, import_tracker for status). All seven have BOTH value modes (Relativ cm + Balti m.a.f.):

| Tsz | Well | Points/mode | Window | Balti range (m.a.f.) |
|---|---|---|---|---|
| 825 | Pákozd | 16 493 | 1993-01 → 2026-03 | 109.30–110.71 |
| 826 | Agárd | 20 553 | 1990-01 → 2026-08 | 104.51–108.51 |
| 143969 | Agárd-2.új házak | 3 156 | 1998-01 → 2026-02 | 103.10–105.74 |
| 143970 | AGÁRD-3.szennyvíztelep | 12 572 | 1998-01 → 2026-04 | 104.12–107.83 |
| 667 | Velence | 18 415 | 1990-01 → 2026-05 | 131.71–133.57 |
| 582 | Kápolnásnyék | 34 680 | 1990-01 → 2026-08 | 117.85–122.73 |
| 587 | Börgönd | 6 387 | 1990-01 → 2025-03 | 110.05–115.58 |

Rétegvíz (vmoType 13, code 70) not ingested — deferred. Near-lake wells probed 2026-09-11: 781 Zámoly-1 (31 813 pont, 1990→2024), 770 Csákvár-1 (artézi, pozitív values), 783 Seregélyes-1, 3987 Iszkaszentgyörgy Kp-248.

## Provenance warning — read before inserting into vizmerleg.db

- Every `daily_obs` row so far = yearbook PDF transcription. VRA = new source family.
- VRA value = daily mean of hourly record. Yearbook daily value = 7:00 observation / `számított (feldolgozottból)` (per `station_metadata_history`). Series identical outside rapid hydrograph rises. Flood-rise days differ up to ±0.07 m³/s (Zámoly 2024 Jan 6–7).
- Inserting VRA data = Rule C user decision + own `documents` entry as source. Decided convention: never mix sources silently in `daily_obs`.
- 2026-09-09: user decision = insert. Done. 4 series inserted (zamoly+patka, 2002 doc_id=42 + 2025 doc_id=43, 1458 rows). 2002 gauge identity validated vs yearbook tbl3 (24/24 months ≤0.0005 m³/s). See EXTRACTION_GUIDE §14 VRA entry for semantics + overwrite rule.

## Quirks summary

- No Origin header on auth → 403 `Forbidden: Unauthorized origin`. Most common failure.
- No Bearer on vraquery → 401 `www-authenticate: Bearer`.
- Token TTL 900 s. Long scripts: re-fetch per batch.
- End-of-year boundary: endTime `YYYY-12-31T00:00:00` drops Dec 31. Use next-year Jan 1.
- CEST verified 2026-09-09: summer responses emit `22:00Z` for local midnight (CET winter: `23:00Z`). Convert with `Europe/Budapest` timezone, not fixed +1h.
- `kdtvizig.hu` (different host, yearbook PDFs) has broken cert chain — unrelated to VRA, needs `-k`.
