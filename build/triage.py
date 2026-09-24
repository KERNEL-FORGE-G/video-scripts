#!/usr/bin/env python3
"""Planches de tri pour les captures recentes (date encodee dans le nom du fichier)."""
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "captures_src"
OUT = ROOT / "work" / "triage"

DATE_RE = re.compile(r"(2026-\d\d-\d\d)[ _](\d\d)-(\d\d)-(\d\d)")


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main(days):
    items = []
    for p in sorted(SRC.iterdir()):
        m = DATE_RE.search(p.name)
        if not m or m.group(1) not in days:
            continue
        try:
            with Image.open(p) as im:
                items.append((p, m.group(1), f"{m.group(2)}:{m.group(3)}:{m.group(4)}", im.size))
        except Exception as exc:  # noqa: BLE001
            print(f"illisible: {p.name}: {exc}")

    print(f"{len(items)} captures sur {', '.join(days)}")
    for p, d, t, sz in items:
        print(f"  {d} {t}  {sz[0]}x{sz[1]}  {p.name}")

    cols, rows, tw = 3, 2, 620
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("t_*.png"):
        old.unlink()

    f, fs = font(22), font(18)
    per = cols * rows
    for sheet, start in enumerate(range(0, len(items), per)):
        group = items[start:start + per]
        th = int(tw * 9 / 16)
        pad, cap = 10, 30
        W = cols * (tw + pad) + pad
        Hh = rows * (th + cap + pad) + pad
        canvas = Image.new("RGB", (W, Hh), (16, 16, 20))
        dr = ImageDraw.Draw(canvas)
        for i, (p, d, t, sz) in enumerate(group):
            n = start + i
            cx = pad + (i % cols) * (tw + pad)
            cy = pad + (i // cols) * (th + cap + pad)
            with Image.open(p) as im:
                im = im.convert("RGB")
                sc = min(tw / im.width, th / im.height)
                small = im.resize((max(1, round(im.width * sc)), max(1, round(im.height * sc))))
            canvas.paste(small, (cx, cy + cap))
            dr.text((cx + 2, cy + 4), f"[{n:02d}] {t} {sz[0]}x{sz[1]}", font=f, fill=(120, 220, 255))
            dr.rectangle([cx, cy + cap - 2, cx + tw, cy + cap + th], outline=(60, 60, 70))
        dest = OUT / f"t_{sheet:02d}.png"
        canvas.save(dest)
        print(f"planche {dest.name}: [{start:02d}]..[{start + len(group) - 1:02d}]")


if __name__ == "__main__":
    main(sys.argv[1:] or ["2026-09-21", "2026-09-22", "2026-09-23"])
