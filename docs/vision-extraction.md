# Vision Extraction — Z.AI GLM-4.6V Document Processing

Scanned numeric tables unreadable by OCR (docling/document_parse garbles dense digits). Text-only agent models cannot view PNGs. Solution: Z.AI GLM-4.6V vision model reads rendered page images, agent inserts results.

Built for Z.AI document processing. Uses Z.AI Coding Plan.

## Components

| Piece | Path | Role |
|---|---|---|
| Renderer | `render_page.py` | pdftoppm → 300dpi PNG, optional crop/zoom |
| Vision reader | `vision_read.py` | PNG → GLM-4.6V → TSV transcription on stdout |
| Auth | `~/.pi/agent/auth.json` | key `zai` → `["zai"]["key"]` |
| Target | `output/vizmerleg.db` | sole target, see EXTRACTION_GUIDE.md §5 |

## Endpoint

```
https://api.z.ai/api/coding/paas/v4/chat/completions
model: glm-4.6v  (glm-4.5v also works)
```

- Coding Plan path = `api/coding/paas/v4`. Pay-as-you-go path `/api/paas/v4` rejects plan key: error 1113 "Insufficient balance".
- pi model catalog lists GLM models as `input: ["text"]` — vision works only via direct API call, not via pi model wiring.
- Image input: `image_url` + base64 data URL.
- Set `"thinking": {"type": "disabled"}` — faster, avoids empty-content responses when reasoning tokens consume budget.

## Usage

```bash
# 1. render page
python3 scripts/render_page.py "<pdf>" <page> --out-dir scratchpad/<year>
# 2. transcribe (default prompt = hydrological monthly table → TSV)
python3 scripts/vision_read.py scratchpad/<year>/p<N>-<NN>.png
# custom prompt: pass as 2nd arg or prompt file
```

Full-page transcription ≈ 1–4 min. Timeout 420s, 2 retries built in.

## Validation Protocol (mandatory)

1. **Two-pass read.** Row-major + column-major prompts on same PNG. Values must match exactly. Mismatch → crop suspect region, third read, human decision if still unclear.
2. **Header mapping never trusted from single read.** Vision model misassigns station names (observed: 7 names for 6 columns, off-by-one). Resolve via:
   - digital-era doc ToC (2024 PDF has text layer — exact station order),
   - DB magnitude cross-check (station Átlag values vs adjacent years),
   - hydrology logic (release-driven spikes belong on Császár-víz stations).
3. **Rule B/D still apply** inside each read: read once, `?` if unreadable, no value derivation.

## Known Limits

- Empty content responses: intermittent. `thinking: disabled` + retry fixes.
- Header/label strips: less reliable than digits. Always verify against precedent.
- Landmark crops (blind x,y guessing) mostly wasted calls. Prefer full-page + targeted prompts.

## Proven

2001 tbl3 (Velencei-tó vízmérleg, 2001.pdf p8): 6 stations × 13 values, two-pass exact agreement, magnitudes consistent with 2004-06 DB values. 78 rows inserted.
