#!/usr/bin/env python3
"""
vision_read.py — transcribe scanned PDF table pages via Z.AI GLM-4.6V vision model.

Built for Z.AI document processing: uses the Z.AI Coding Plan endpoint
(https://api.z.ai/api/coding/paas/v4) with the glm-4.6v vision model, which is
included in the Coding Plan (the pay-as-you-go /paas/v4 endpoint rejects the
plan key with error 1113).

Pipeline role: EXTRACTION_GUIDE.md one-table-per-turn flow for scanned numeric
tables where OCR (document_parse/docling) produces garbled output. Use
scripts/render_page.py first to get a 300dpi PNG, then:

  python3 scripts/vision_read.py <png_path> [prompt]

Default prompt transcribes a hydrological monthly table to TSV
(rows=stations, cols=months + Évi/annual col), preserving Hungarian decimal
commas and dashes for missing values.

Auth: reads key from ~/.pi/agent/auth.json ["zai"]["key"].
Output: model answer on stdout. Exit 1 on API error.
"""
import base64
import json
import sys
import urllib.request
from pathlib import Path

CODING_URL = "https://api.z.ai/api/coding/paas/v4/chat/completions"
MODEL = "glm-4.6v"

DEFAULT_PROMPT = """This is a scanned Hungarian hydrological table page.
Transcribe the numeric table into TSV (tab-separated):
- First line: column headers as printed (month abbreviations, station name column, annual total column e.g. "Évi" or "Éves").
- One row per station: station name exactly as printed, then monthly values.
- Preserve Hungarian decimal commas exactly (e.g. 0,085 stays 0,085).
- Use "-" for missing/dash cells. Do not compute, correct, or verify values.
- Read each cell once; if a cell is unreadable write "?".
Output ONLY the TSV, no commentary."""


def main():
    if len(sys.argv) < 2:
        sys.exit(f"usage: {sys.argv[1:0]} vision_read.py <png_path> [prompt_file_or_text]")

    png = Path(sys.argv[1])
    if not png.exists():
        sys.exit(f"error: PNG not found: {png}")

    prompt = DEFAULT_PROMPT
    if len(sys.argv) > 2:
        p = Path(sys.argv[2])
        prompt = p.read_text() if p.exists() else sys.argv[2]

    auth_path = Path.home() / ".pi/agent/auth.json"
    key = json.loads(auth_path.read_text())["zai"]["key"]

    b64 = base64.b64encode(png.read_bytes()).decode()
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]}],
        "max_tokens": 8000,
    }).encode()

    req = urllib.request.Request(
        CODING_URL, data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    last_err = None
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=420) as r:
                out = json.loads(r.read())
            print(out["choices"][0]["message"]["content"].strip())
            return
        except urllib.error.HTTPError as e:
            sys.exit(f"API error {e.code}: {e.read().decode()[:300]}")
        except (TimeoutError, TimeoutError) as e:
            last_err = e
            print(f"attempt {attempt} timed out, retrying...", file=sys.stderr)
    sys.exit(f"error: timed out twice: {last_err}")


if __name__ == "__main__":
    main()
