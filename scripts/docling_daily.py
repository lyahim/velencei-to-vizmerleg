import re
import sys
from docling.document_converter import DocumentConverter

MONTHS = ["Jan", "Feb", "Marc", "Apr", "Maj", "Jun", "Jul", "Aug", "Sze", "Okt", "Nov", "Dec"]


def clean_num(s, min_plausible=None):
    s = s.strip()
    if s in ("", "-", "."):
        return None
    # drop quality flags (A/P letters) and stray OCR punctuation
    s = re.sub(r"[A-Za-z]", "", s)
    s = s.strip().strip(".")
    if s == "":
        return None
    try:
        v = float(s.replace(",", "."))
    except ValueError:
        return None
    # OCR sometimes inserts a stray decimal point into a 3-digit integer
    # (e.g. "1.54" meant to read "154") -- only relevant for tables whose
    # real values are always >= min_plausible (e.g. cm water levels)
    if min_plausible is not None and 0 < v < min_plausible and "." in s:
        stripped = s.replace(".", "")
        try:
            v2 = float(stripped)
            if v2 >= min_plausible:
                return v2
        except ValueError:
            pass
    return v


def extract_daily_grid(pdf_path, page, table_index, min_plausible=None, valid_range=None):
    conv = DocumentConverter()
    result = conv.convert(pdf_path, page_range=(page, page))
    doc = result.document
    t = doc.tables[table_index]
    df = t.export_to_dataframe(doc)
    rows = df.values.tolist()

    daily = {m: {} for m in MONTHS}
    for r in rows:
        idx_cell = str(r[0]).strip()
        # stop once we hit the summary block
        if idx_cell.lower().startswith(("minim", "nap", "ora", "atlag", "maxim", "jeges", "cra")):
            continue
        if not idx_cell:
            continue
        day_nums = re.findall(r"\d+", idx_cell)
        if not day_nums:
            continue
        if len(day_nums) == 1:
            day_list = [int(day_nums[0])]
            month_cells = r[1:13]
        else:
            # merged-row quirk: index cell has 2 day numbers, each month cell
            # also contains 2 space-separated values
            day_list = [int(d) for d in day_nums]
            month_cells = r[1:13]

        if len(day_list) == 1:
            for mi, cell in enumerate(month_cells):
                v = clean_num(str(cell), min_plausible)
                if v is not None:
                    daily[MONTHS[mi]][day_list[0]] = v
        else:
            for mi, cell in enumerate(month_cells):
                parts = re.split(r"\s+(?=\d)", str(cell).strip())
                # re-split respecting the flag letters glued to numbers, e.g. "141 A 141 A"
                nums = re.findall(r"\d+(?:[.,]\d+)?\s*[AP]?", str(cell))
                if len(nums) == len(day_list):
                    for d, nv in zip(day_list, nums):
                        v = clean_num(nv, min_plausible)
                        if v is not None:
                            daily[MONTHS[mi]][d] = v

    if valid_range is not None:
        lo, hi = valid_range
        flagged = []
        for m in MONTHS:
            for d in list(daily[m]):
                v = daily[m][d]
                if v is not None and not (lo <= v <= hi):
                    flagged.append((m, d, v))
                    daily[m][d] = None
        if flagged:
            print(f"# WARNING: {len(flagged)} value(s) outside valid_range {valid_range}, set to None:", file=sys.stderr)
            for m, d, v in flagged:
                print(f"#   {m} day {d}: {v}", file=sys.stderr)
    return daily


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python3 scripts/docling_daily.py <pdf_path> <page> [table_index=1] [min_plausible] [valid_min valid_max]")
        sys.exit(1)
    pdf_path = sys.argv[1]
    page = int(sys.argv[2])
    table_index = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    min_plausible = None if len(sys.argv) <= 4 or sys.argv[4].lower() == "none" else float(sys.argv[4])
    valid_range = None
    if len(sys.argv) > 6:
        valid_range = (float(sys.argv[5]), float(sys.argv[6]))
    grid = extract_daily_grid(pdf_path, page, table_index, min_plausible, valid_range)
    for mi, m in enumerate(MONTHS, start=1):
        vals = [v for v in grid[m].values() if v is not None]
        n = len(vals)
        avg = sum(vals) / n if n else 0
        print(f"{m} ({mi:02d}): n={n} avg={avg:.1f} min={min(vals) if n else None} max={max(vals) if n else None}")
    print()
    for mi, m in enumerate(MONTHS, start=1):
        for d in sorted(grid[m]):
            print(f"2010-{mi:02d}-{d:02d} = {grid[m][d]}")
