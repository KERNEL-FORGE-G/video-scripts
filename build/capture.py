#!/usr/bin/env python3
"""Captures réelles du site UniFlow via Chrome headless.

Ne touche qu'aux fichiers de video/assets/captures/. Le serveur local
(build/serve_web.py) doit tourner sur le port indiqué.

  python3 build/capture.py                 # desktop + mobile, toutes les pages
  python3 build/capture.py --only about    # filtre par substring
"""
import argparse
import json
import pathlib
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "captures"
CHROME = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")

PAGES = {
    "accueil": "/",
    "a_propos": "/about/",
    "tarifs": "/pricing/",
    "presentation": "/presentation/",
    "forum": "/forum",
    "contact": "/contact",
    "telecharger": "/download",
    "plateforme": "/plateforme-gestion-universitaire/",
    "emploi_du_temps": "/emploi-du-temps-universitaire/",
    "presences_qr": "/presence-qr-code-universite/",
    "assistant": "/assistant/",
    "connexion": "/login",
    "inscription": "/register",
}
VIEWPORTS = {"desktop": (1920, 1080), "mobile": (412, 915)}

# En production le routeur travaille sur l'ancre : /#/forum, pas /forum.
# Un curl sur /forum renvoie le 404 de Vercel alors que la page existe.
# Ces routes viennent de la barre de menu du site en ligne, relue le
# 2026-09-23 : les précédentes (#/a-propos, #/equipe, #/plateforme) étaient
# devinées et ne produisaient que l'écran 404 d'Uni.
LIVE = "https://uniflow.kernelforge.codes"
LIVE_PAGES = {
    "accueil": "/#/",
    "forum": "/#/forum",
    "connexion": "/#/login",
    "contact": "/#/contact",
    "telecharger": "/#/download",
    "a_propos": "/#/about",
    "equipe": "/#/teams",
    "sentinelle": "/#/sentinelle",
    "tarifs": "/#/pricing",
    "presentation": "/#/presentation",
}


def shoot(base, name, path, w, h, wait_ms):
    dest = OUT / f"{name}.png"
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--hide-scrollbars", "--force-device-scale-factor=1",
           f"--window-size={w},{h}", f"--virtual-time-budget={wait_ms}",
           f"--screenshot={dest}", base.rstrip("/") + path]
    subprocess.run(cmd, capture_output=True, timeout=180)
    if not dest.exists():
        return None
    a = np.asarray(Image.open(dest).convert("RGB"), dtype=np.int16)
    return {"file": dest.name, "size": list(a.shape[:2])[::-1], "std": round(float(a.std()), 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="")
    ap.add_argument("--live", action="store_true", help="capturer la production (routes en ancre)")
    ap.add_argument("--only", default="")
    ap.add_argument("--wait", type=int, default=18000, help="budget de temps virtuel en ms")
    a = ap.parse_args()
    if not CHROME:
        sys.exit("Chrome/Chromium introuvable")
    pages = LIVE_PAGES if a.live else PAGES
    base = a.base or (LIVE if a.live else "http://127.0.0.1:8123")
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for vp, (w, h) in VIEWPORTS.items():
        for name, path in pages.items():
            if a.only and a.only not in name and a.only not in path:
                continue
            tag = f"{vp}_{name}"
            try:
                r = shoot(base, tag, path, w, h, a.wait)
            except subprocess.TimeoutExpired:
                r = {"file": tag, "error": "timeout"}
            rows.append(r or {"file": tag, "error": "aucun fichier"})
            print(f"  {tag:32} {rows[-1]}", flush=True)
    bad = [r for r in rows if r.get("std", 0) < 12 or r.get("error")]
    print(f"\n{len(rows)} captures, {len(bad)} suspectes (page blanche ou erreur) :")
    for r in bad:
        print("   ", json.dumps(r, ensure_ascii=False))
    (OUT / "index.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
