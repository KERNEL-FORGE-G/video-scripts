#!/usr/bin/env python3
"""Génération d'images via l'API Gemini pour la vidéo UniFlow.

Lit video/.env, appelle generativelanguage.googleapis.com, écrit les PNG dans
le dossier demandé. Aucun fichier hors de video/ n'est touché.

  python3 build/gen_images.py --prompt "..." --out work/essai.png [--ref a.png]...
  python3 build/gen_images.py --jobs build/jobs.json
"""
import argparse
import base64
import json
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
# Dans l'ordre de préférence : le premier accessible gagne.
MODELS = ["gemini-2.5-flash-image", "gemini-3.1-flash-image", "gemini-3-pro-image"]
RATIOS = {
    "16:9": "16:9", "9:16": "9:16", "1:1": "1:1", "4:3": "4:3", "3:4": "3:4",
    "21:9": "21:9", "5:4": "5:4", "4:5": "4:5",
}


def load_env(path=ROOT / ".env"):
    """Charge KEY=valeur sans écraser l'environnement déjà présent."""
    env = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def mime_of(p):
    s = p.suffix.lower().lstrip(".")
    return {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp"}.get(s, "image/png")


def generate(key, prompt, refs=(), ratio="16:9", model=None):
    parts = [{"text": prompt + f"\n\nAspect ratio: {ratio}."}]
    for r in refs:
        p = pathlib.Path(r)
        parts.append({"inline_data": {"mime_type": mime_of(p),
                                      "data": base64.b64encode(p.read_bytes()).decode()}})
    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"],
                                 "imageConfig": {"aspectRatio": ratio}}}
    data = json.dumps(body).encode()
    errs = []
    for m in [model] if model else MODELS:
        req = urllib.request.Request(API.format(model=m), data=data, method="POST",
                                     headers={"Content-Type": "application/json",
                                              "x-goog-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                out = json.loads(r.read())
        except urllib.error.HTTPError as e:
            errs.append(f"{m}: HTTP {e.code} {e.read()[:220].decode(errors='replace')}")
            continue
        except Exception as e:
            errs.append(f"{m}: {e}")
            continue
        images = [p["inlineData"] for cand in out.get("candidates", [])
                  for p in cand.get("content", {}).get("parts", [])
                  if "inlineData" in p]
        if not images:
            errs.append(f"{m}: aucune image (réponse: "
                        f"{json.dumps(out)[:220]})")
            continue
        txt = "".join(p.get("text", "") for cand in out.get("candidates", [])
                      for p in cand.get("content", {}).get("parts", []))
        return m, images[0], txt
    return None, None, "\n".join(errs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--ratio", default="16:9", choices=list(RATIOS))
    ap.add_argument("--model", default=None)
    a = ap.parse_args()

    key = load_env().get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY absente de video/.env")
    model, img, txt = generate(key, a.prompt, a.ref, a.ratio, a.model)
    if not img:
        sys.exit(f"Échec:\n{txt}")
    dest = pathlib.Path(a.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(base64.b64decode(img["data"]))
    print(f"OK  {model} -> {dest} ({dest.stat().st_size // 1024} Ko)")
    if txt.strip():
        print("    " + txt.strip().replace("\n", "\n    ")[:400])


if __name__ == "__main__":
    main()
