# Földalatti (talajvíz) adatsorok letöltése az OVF VRA API-ból.
# Kimenet: SQL INSERT OR IGNORE blokk (BEGIN/COMMIT) a stdoutra vagy argv[1] fájlba.
# Sosem ír adatbázist — a blokkot operátornak kell alkalmazni. Lásd docs/vra-api.md.
import json
import ssl
import sys
import urllib.request
from datetime import date, datetime, timedelta

TSZ_LIST = [825, 826, 143969, 143970, 667, 582, 587]  # regisztrált kút-kör (7 kút)
ADAT_FAJTA_KOD = 69  # Talajvízállás
START = "1990-01-01T00:00:00"
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE  # data.vizugy.hu tanúsítványlánc e gépről hibás (curl -k párja)


def http(method, url, headers, body=None):
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(req, context=CTX, timeout=120) as r:
        return r.read()


def fetch_series(token, value_filter):
    body = json.dumps({
        "torzsszamList": TSZ_LIST,
        "adatFajtaKod": ADAT_FAJTA_KOD,
        "adatTipusKod": 100,
        "startTime": START,
        "endTime": (date.today() + timedelta(days=1)).isoformat() + "T00:00:00",
        "dataExtFilter": 0,
        "valueFilter": value_filter,
        "amKodFilter": [0],
    }).encode()
    out = http("POST", "https://vmservice.vizugy.hu/vraquery/TS/TsShortList", {
        "Authorization": "Bearer " + token,
        "Origin": "https://data.vizugy.hu",
        "Content-Type": "application/json",
    }, body)
    return json.loads(out)


def main():
    token = json.loads(http("GET", "https://data.vizugy.hu/AuthApi/auth/token",
                            {"Origin": "https://data.vizugy.hu"}))["access_token"]
    now = datetime.now()
    fetch_day = now.strftime("%Y-%m-%d")
    doc_filename = "VRA földalatti " + fetch_day
    lines = [
        "BEGIN;",
        "INSERT OR IGNORE INTO documents (year, year_part, filename, source_type, pages, prepared_date, processed_at)",
        f"VALUES ({now.year}, NULL, '{doc_filename}', 'digital', NULL, NULL, '{now.strftime('%Y-%m-%d %H:%M')}');",
    ]
    for mode, value_filter in (("relativ", "Relativ"), ("balti", "Balti")):
        for st in fetch_series(token, value_filter):
            tsz = st["ItemId"]
            if tsz not in TSZ_LIST:
                sys.exit(f"VÁRATLAN törzsszám a válaszban: {tsz} — nem töltöm be")
            for p in st.get("TsItemList") or []:
                if p.get("Adat") is None:
                    continue
                lines.append(
                    f"INSERT OR IGNORE INTO groundwater_obs (ts_utc, well_tsz, mode, value, source_doc_id) "
                    f"SELECT '{p['UTCTime']}', {tsz}, '{mode}', {repr(p['Adat'])}, id "
                    f"FROM documents WHERE filename = '{doc_filename}';")
    lines.append("COMMIT;")
    out = "\n".join(lines) + "\n"
    if len(sys.argv) > 1:
        open(sys.argv[1], "w").write(out)
    else:
        sys.stdout.write(out)
    n = sum(1 for l in lines if l.startswith("INSERT OR IGNORE INTO groundwater_obs"))
    print(f"-- {n} megfigyelési pont, forrásdokumentum: {doc_filename}", file=sys.stderr)


if __name__ == "__main__":
    main()
