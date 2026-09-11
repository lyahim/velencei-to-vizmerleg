## 1. Adatbázis-séma és nyilvántartás

- [x] 1.1 `CREATE TABLE groundwater_wells` (tsz PK, name, telepules, lat, lon, uzem) és `groundwater_obs` (ts_utc TEXT, well_tsz FK, mode CHECK relativ|balti, value REAL, source_doc_id FK, UNIQUE(ts_utc, well_tsz, mode)) — ellenőrzés: `.schema groundwater_wells` + `.schema groundwater_obs` kiírja a táblát
- [x] 1.2 `groundwater_wells` feltöltése a 7 regisztrált kúttal (825, 826, 143969, 143970, 667, 582, 587) — ellenőrzés: `SELECT COUNT(*) FROM groundwater_wells;` = 7

## 2. Letöltő szkript és első betöltés

- [x] 2.1 `scripts/fetch_groundwater.py` írása (urllib, saját guest token, 2 db POST — mode-onként egy, mind a 7 törzsszám egy requestben, 1990-01-01→ma, aggregateFilters nélkül, Adat nélküli pontok kihagyva, INSERT OR IGNORE blokk BEGIN/COMMIT közepette stdout-ra) — ellenőrzés: futtatás után DB bájtonként változatlan, stdout érvényes SQL-t ad
- [x] 2.2 Első betöltés:.documents sor (`filename='VRA földalatti <dátum>'`, source_type='digital') + SQL blokk alkalmazása — ellenőrzés: egy `SELECT COUNT(*), mode FROM groundwater_obs GROUP BY mode;` és kútonkénti pontszámok; második alkalmazás nem változtatja a számokat
- [x] 2.3 Részletes elérhetőségi riport kútonként/mód-onként (Balti hiánya esetén lista a chart A feliratához) — ellenőrzés: riport a notes-ban/trackeben rögzítve

## 3. Dokumentáció (ugyanabban a turnban, mint a betöltés)

- [x] 3.1 `docs/vra-api.md` korrekció: vmoType-tábla (11 surface / 1 spring / 12 nearsurface-talajvíz / 13 undersurface-rétegvíz / 14 hidromet), új kódtábla (69, 70, 76, 299, 303, 304), Balti-mód kútra, Aft = dataTransportType — ellenőrzés: fájlban a javított táblázat
- [x] 3.2 `EXTRACTION_GUIDE.md` §14 provenance-bejegyzés (VRA földalatti, nyers tárolás, UTC, nincs deriválás) + §15 struktúra-regiszter bejegyzés a `groundwater_obs`-ra — ellenőrzés: mindkét § tartalmazza az új bejegyzést
- [x] 3.3 `import_tracker.md` sorok a betöltésre (status=done, rows_in_db, notes) + `docs/file-index.md` sor a `scripts/fetch_groundwater.py`-ra — ellenőrzés: mindkét fájl tartalmazza az új sort

## 4. Oldalgenerátor export

- [x] 4.1 Havi aggregálás + JSON export `generate_site.py`-ban (Europe/Budapest hónap-bucket, hiányzó hónap = rés, mindkét mód, DATA_VERSION) — ellenőrzés: exportált fájl létezik, egy spot-check havi átlag egyezik egy kézi SQL-lel
- [x] 4.2 Tó-sorozat Balti-dátumban (monthly_station_obs atlag_cm + COALESCE(nullpont_mBf, 102.62)) az overlay chart JSON-jába — ellenőrzés: 2022-es havi minimum ≈ 103,1–103,3 m.a.f. sávban

## 5. Chartok és forrásoldal

- [x] 5.1 Chart A a klima oldalon (tó szint + talajvíz-kutak m.a.f., 2019–2022 aszályárnyékolás, magyar felirat, provenance-sor) — ellenőrzés: generált klima.html-ben a panel látszik, mindkét sorozat hydrate-elődik
- [x] 5.2 Chart B az adattár oldalon (7 kútos small-multiple, Relativ cm, mélység lefelé nő, havi átlag) — ellenőrzés: generált adattar.html-ben mind a 7 kút neve megjelenik
- [x] 5.3 Forrás oldal: OVF VRA (data.vizugy.hu) forrásbejegyzés a kutakkal és időablakkal, utolsó letöltési dátum, „változatlanul átvett értékek" megjegyzés, valamint a vizugy nyílt-adat licencfeltétele feltüntetése („a forrás (Országos Vízügyi Főigazgatóság, vagy a területileg illetékes Vízügyi Igazgatóság) feltüntetése mellett szabadon, ingyenesen felhasználhatók" — data.vizugy.hu letöltőfelület) — ellenőrzés: forras.html tartalmazza a linket, a dátumot és a licencmondatot
- [x] 5.4 `docs/climate-charts-plan.md` kiegészítés a két új chart sorával — ellenőrzés: fájl tartalmazza

## 6. Ismert problémák és végső ellenőrzés

- [x] 6.1 `docs/known-issues.md` display-megjegyzések (Relativ referenciapont-ambiguitás, Agárd-3 szennyvíztelep, 2018 telemetria-váltás, utolsó ~1 év VRA-adat feldolgozatlan / tájékoztató jellegű) — ellenőrzés: a chartok felirata alatt megjelennek
- [x] 6.2 Teljes build és commit-ellenőrzés (`python3 scripts/generate_site.py`, `git status --short output/` csak a DB-t mutatja) — ellenőrzés: site újraépül, coverage/friss változatbélyeg megvan
