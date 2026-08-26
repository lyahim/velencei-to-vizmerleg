#!/usr/bin/env python3
"""
Render a single PDF page to a PNG for direct visual reading, with optional
crop+zoom on a sub-region. Fallback for when docling produces garbled output
(see EXTRACTION_GUIDE.md 4b) -- at 300dpi these dense daily-grid tables are
fully legible to read directly, often more reliably than docling's OCR pass.

Usage:
  python3 scripts/render_page.py <pdf_path> <page> [--dpi 300] [--out-dir DIR]
  python3 scripts/render_page.py <pdf_path> <page> --crop x0,y0,x1,y1 [--zoom 2] [--out-dir DIR]

Examples:
  python3 scripts/render_page.py "pdfs/Velencei-to vizmerleg, 2007.pdf" 16
  python3 scripts/render_page.py "pdfs/Velencei-to vizmerleg, 2007.pdf" 16 --crop 240,1750,2350,1990 --zoom 2
"""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_path")
    ap.add_argument("page", type=int)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out-dir", default=None, help="defaults to a 'scratchpad' subfolder next to the PDF, or cwd")
    ap.add_argument("--crop", default=None, help="x0,y0,x1,y1 in rendered-image pixel coords")
    ap.add_argument("--zoom", type=int, default=2, help="integer upscale factor applied to --crop output")
    args = ap.parse_args()

    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        sys.exit(f"error: PDF not found: {pdf_path}")

    out_dir = Path(args.out_dir) if args.out_dir else Path.cwd()
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = out_dir / f"p{args.page}"

    subprocess.run(
        ["pdftoppm", "-f", str(args.page), "-l", str(args.page),
         "-r", str(args.dpi), "-png", str(pdf_path), str(prefix)],
        check=True,
    )
    rendered = prefix.parent / f"{prefix.name}-{args.page}.png"
    if not rendered.exists():
        # single-page docs sometimes get suffix-less output
        candidates = sorted(out_dir.glob(f"{prefix.name}*.png"))
        if not candidates:
            sys.exit("error: pdftoppm did not produce a PNG")
        rendered = candidates[0]

    print(f"rendered: {rendered}")

    if args.crop:
        from PIL import Image
        x0, y0, x1, y1 = (int(v) for v in args.crop.split(","))
        img = Image.open(rendered)
        crop = img.crop((x0, y0, x1, y1))
        if args.zoom and args.zoom != 1:
            crop = crop.resize((crop.width * args.zoom, crop.height * args.zoom))
        crop_path = rendered.parent / f"{rendered.stem}_crop_{x0}_{y0}_{x1}_{y1}.png"
        crop.save(crop_path)
        print(f"crop:     {crop_path}")


if __name__ == "__main__":
    main()
