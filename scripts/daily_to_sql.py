import re
import sys

if len(sys.argv) < 4:
    print("usage: python3 scripts/daily_to_sql.py <values_txt> <station_id> <source_doc_id> [out_sql]")
    sys.exit(1)

values_txt, station_id, source_doc_id = sys.argv[1], sys.argv[2], sys.argv[3]
out_sql = sys.argv[4] if len(sys.argv) > 4 else None

pattern = re.compile(r"^(\d{4})-(\d{2})-(\d{2})\s*=\s*(\S+)\s*$")
rows = []
for line in open(values_txt, encoding="utf-8"):
    m = pattern.match(line.strip())
    if not m:
        continue
    year, month, day, val = m.groups()
    val = "NULL" if val in ("None", "null", "NULL") else val
    rows.append((int(year), int(month), int(day), val))

lines = ["BEGIN;", "", "INSERT INTO daily_obs (year, month, day, station_id, value, source_doc_id) VALUES"]
value_lines = [
    f"({y},{mo},{d},'{station_id}',{v},{source_doc_id})" for (y, mo, d, v) in rows
]
lines.append(",\n".join(value_lines) + ";")
lines.append("")
lines.append("COMMIT;")
sql = "\n".join(lines)

if out_sql:
    with open(out_sql, "w", encoding="utf-8") as f:
        f.write(sql)
    print(f"wrote {len(rows)} rows -> {out_sql}")
else:
    print(sql)
