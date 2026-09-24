#!/usr/bin/env python3
"""Génération d'images Gemini par SDK — un appel, une image, sans copier-coller.

  ./build/generer_image.py --prompt "..." --out work/essai.png [--ratio 16:9] [--ref a.png]
  ./build/generer_image.py --planches build/planches.json          (58 scènes d'un coup)

Le SDK est installé pour ça ; `generate_images` est réservé à la plateforme
entreprise et refuse Developer API, on passe donc par `generate_content` avec
un modèle image — même résultat, même clé que build/gen_images.py (REST, sans
dépendance). Les deux écrivent dans video/work/ et ne touchent à rien d'autre.
"""
import argparse
import json
import pathlib
import sys
import warnings

# Le SDK gémit à chaque appel sur l'appel de fonctions automatique ; une ligne
# de commande propre vaut mieux que ce conseil non demandé.
warnings.filterwarnings("ignore", message=".*automatic function calling.*")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen_images import ROOT, load_env, mime_of  # même .env, mêmes formats

# Premier qui répond gagne ; tous logent à la même enseigne côté quota.
MODELS = ["gemini-3.1-flash-image", "gemini-2.5-flash-image", "gemini-3-pro-image"]
RATIOS = ["16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "5:4", "4:5"]


def generate(client, prompt, out, ratio="16:9", refs=(), model=None):
    from google import genai
    from google.genai import types

    parts = [{"text": prompt}]
    for r in refs:
        p = pathlib.Path(r)
        parts.append({"inline_data": {"mime_type": mime_of(p),
                                      "data": p.read_bytes()}})
    cfg = types.GenerateContentConfig(
        response_modalities=["IMAGE", "TEXT"],
        image_config=types.ImageConfig(aspect_ratio=ratio))
    errs = []
    for m in [model] if model else MODELS:
        try:
            rep = client.models.generate_content(model=m, contents=parts, config=cfg)
        except Exception as e:
            errs.append(f"  {m}: {str(e).splitlines()[-1][:150]}")
            continue
        pics = [p for cand in (rep.candidates or [])
                for p in (cand.content.parts or []) if getattr(p, "inline_data", None)]
        if not pics:
            errs.append(f"  {m}: réponse sans image")
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(pics[0].inline_data.data)
        txt = "".join(p.text for p in (rep.candidates[0].content.parts or [])
                      if getattr(p, "text", None))
        return m, out, txt
    print("Échec :\n" + "\n".join(errs), file=sys.stderr)
    return None, None, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prompt")
    ap.add_argument("--out")
    ap.add_argument("--planches", help="fichier JSON: [{ref, prompt, ratio, out}, ...]")
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--ratio", default="16:9", choices=RATIOS)
    ap.add_argument("--model", default=None)
    a = ap.parse_args()

    if bool(a.prompt) == bool(a.planches):
        ap.exit(2, "une seule des deux options : --prompt/--out ou --planches")

    key = load_env().get("GEMINI_API_KEY")
    if not key:
        sys.exit("GEMINI_API_KEY absente de video/.env")

    from google import genai
    client = genai.Client(api_key=key)

    if a.planches:
        jobs = json.loads(pathlib.Path(a.planches).read_text())
        deja_vues = sum(1 for j in jobs if pathlib.Path(j["out"]).exists())
        if deja_vues:
            print(f"déjà {deja_vues}/{len(jobs)} planche(s) sur le disque")
        faites = 0
        for j in jobs:
            if not pathlib.Path(j["out"]).exists():
                m, _, _ = generate(client, j["prompt"], pathlib.Path(j["out"]),
                                   j.get("ratio", "16:9"), j.get("refs", ()), a.model)
                if not m:
                    sys.exit(f"arrêt à {j['ref']} — le reste attend la même réinitialisation")
                faites += 1
        print(f"{faites} planche(s) de plus dans {pathlib.Path(jobs[0]['out']).parent}")
        return

    model, out, txt = generate(client, a.prompt, pathlib.Path(a.out),
                               a.ratio, a.ref, a.model)
    if not model:
        sys.exit(1)
    print(f"OK  {model} -> {out} ({out.stat().st_size // 1024} Ko)")
    if txt.strip():
        print("    " + txt.strip().replace("\n", "\n    ")[:400])


if __name__ == "__main__":
    main()
