import sys
from docling.document_converter import DocumentConverter

if len(sys.argv) < 4:
    print("usage: python3 scripts/docling_scan.py <pdf_path> <start_page> <end_page>")
    sys.exit(1)

pdf_path = sys.argv[1]
start, end = int(sys.argv[2]), int(sys.argv[3])
conv = DocumentConverter()
result = conv.convert(pdf_path, page_range=(start, end))
doc = result.document

for i, t in enumerate(doc.tables):
    page_no = t.prov[0].page_no if t.prov else "?"
    df = t.export_to_dataframe(doc)
    print(f"=== table {i} | page {page_no} | shape {df.shape} ===")
    # print first row (often header/label) and first col (row labels) to help identify
    print("first row:", df.iloc[0].tolist()[:6] if len(df) else None)
    print("col0 sample:", df.iloc[:6, 0].tolist() if len(df) else None)
    print()
