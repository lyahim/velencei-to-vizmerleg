#!/usr/bin/env python3
"""Render one PDF page at 300dpi and rotate it 90 deg CW, for the landscape scans whose
pages carry /Rotate 270 (pdfinfo shows "Page rot: 270" -- all of era A/B so far).

pdftoppm emits those pages as a portrait PNG with the table lying on its side, which makes
--crop coordinates nearly impossible to aim and costs legibility. Rotating once first gives a
natural landscape image: read it whole, and crop it in ordinary left-to-right coordinates.
See EXTRACTION_GUIDE.md 4b.

Usage:
  python3 scripts/render_rot.py <pdf> <page> --out-dir scratchpad/<year> [--crop x0,y0,x1,y1] [--zoom N]

Crop coords are in ROTATED image space (landscape, 3516x2481 at 300dpi for A4).
Both the base render and the rotated copy are cached, so re-running for a crop is cheap.
"""
import argparse
import subprocess
from pathlib import Path

from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument("pdf")
ap.add_argument("page", type=int)
ap.add_argument("--out-dir", default=".")
ap.add_argument("--crop", help="x0,y0,x1,y1 in rotated-image pixel coords")
ap.add_argument("--zoom", type=int, default=2)
a = ap.parse_args()

out = Path(a.out_dir)
out.mkdir(parents=True, exist_ok=True)

base = out / f"p{a.page}-{a.page:02d}.png"
if not base.exists():
    subprocess.run(["pdftoppm", "-f", str(a.page), "-l", str(a.page), "-r", "300",
                    "-png", a.pdf, str(out / f"p{a.page}")], check=True)
    if not base.exists():                      # pdftoppm pads the suffix by page count
        cands = sorted(out.glob(f"p{a.page}-*.png"))
        if not cands:
            raise SystemExit("error: pdftoppm produced no PNG")
        base = cands[0]

rot = out / f"p{a.page}_rot.png"
if not rot.exists():
    Image.open(base).rotate(-90, expand=True).save(rot)
print(f"rotated: {rot}  size={Image.open(rot).size}")

if a.crop:
    x0, y0, x1, y1 = (int(v) for v in a.crop.split(","))
    im = Image.open(rot).crop((x0, y0, x1, y1))
    if a.zoom != 1:
        im = im.resize((im.width * a.zoom, im.height * a.zoom))
    p = out / f"p{a.page}_rot_crop_{x0}_{y0}_{x1}_{y1}.png"
    im.save(p)
    print(f"crop:    {p}")
