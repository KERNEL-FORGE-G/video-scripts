#!/usr/bin/env python3
"""Extrait le texte reel des pages publiques d'UniFlow, pour que le script de la
video ne prete au produit aucun slogan qu'il n'affiche pas. Lecture seule."""
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LIVE = "https://uniflow.kernelforge.codes"
CHROME = next((p for p in ("/usr/bin/google-chrome", "/usr/bin/google-chrome-stable",
                           "/usr/bin/chromium", "/usr/bin/chromium-browser")
               if Path(p).exists()), None)

PAGES = {
    "accueil": "/#/", "a_propos": "/#/a-propos", "plateforme": "/#/plateforme",
    "sentinelle": "/#/sentinelle", "tarifs": "/#/tarifs", "presentation": "/#/presentation",
    "forum": "/#/forum", "contact": "/#/contact", "telecharger": "/#/telecharger",
    "equipe": "/#/equipe", "connexion": "/#/login",
    "seo_plateforme": "/plateforme-gestion-universitaire/",
    "seo_emploi_du_temps": "/emploi-du-temps-universitaire/",
    "seo_presence_qr": "/presence-qr-code-universite/",
    "seo_tarifs": "/pricing/",
}


class Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__()
        self.out, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.out.append(data.strip())


def dump(url, wait_ms=9000):
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox", "--dump-dom",
           "--virtual-time-budget=%d" % wait_ms, "--window-size=1920,1080", url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.stdout


def main():
    if not CHROME:
        sys.exit("chrome introuvable")
    dest = ROOT / "work" / "dossier_site.txt"
    dest.parent.mkdir(exist_ok=True)
    with dest.open("w", encoding="utf-8") as fh:
        for name, path in PAGES.items():
            html = dump(LIVE + path)
            p = Text()
            p.feed(html)
            seen, lines = set(), []
            for ln in p.out:
                ln = re.sub(r"\s+", " ", ln)
                if ln.lower() not in seen and len(ln) > 1:
                    seen.add(ln.lower())
                    lines.append(ln)
            fh.write(f"\n\n================ {name}  ({LIVE}{path})  {len(lines)} lignes\n")
            fh.write("\n".join(lines) + "\n")
            print(f"{name:<22} {len(lines):4} lignes  {len(html)//1024:5} Ko html")
    print("->", dest)


if __name__ == "__main__":
    main()
