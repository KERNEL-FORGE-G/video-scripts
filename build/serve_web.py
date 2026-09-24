#!/usr/bin/env python3
"""Sert le build web d'UniFlow en lecture seule, avec repli SPA.

Les fichiers de uniflow-we/dist ne sont jamais modifiés : seule la réponse HTTP
tombe sur index.html quand une route applicative (/app/…, /forum) n'existe pas
sur le disque. Utile pour prendre de vraies captures d'écran.

  python3 build/serve_web.py [--port 8123] [--root <chemin dist>]
"""
import argparse
import http.server
import os
import pathlib
import socketserver
import sys
from urllib.parse import unquote, urlparse

DEFAULT = pathlib.Path("/home/ravel/Documents/Projet KERNEL FORGE/uniflow-we/dist")


class Handler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        root = pathlib.Path(self.server.root).resolve()
        rel = unquote(urlparse(path).path).lstrip("/")
        target = (root / rel).resolve()
        if not str(target).startswith(str(root)):
            target = root
        if target.is_dir() and (target / "index.html").exists():
            return str(target / "index.html")
        if not target.exists() and target.suffix == "":
            alt = (root / f"{rel.rstrip('/')}.html").resolve()
            if str(alt).startswith(str(root)) and alt.is_file():
                return str(alt)
            return str(root / "index.html")
        return str(target)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8123)
    ap.add_argument("--root", default=str(DEFAULT))
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()
    if not (root / "index.html").exists():
        sys.exit(f"pas de index.html dans {root}")
    os.chdir(root)
    with Server(("127.0.0.1", a.port), Handler) as httpd:
        httpd.root = str(root)
        print(f" UniFlow web (lecture seule) http://127.0.0.1:{a.port}/  racine={root}", flush=True)
        httpd.serve_forever()


if __name__ == "__main__":
    main()
