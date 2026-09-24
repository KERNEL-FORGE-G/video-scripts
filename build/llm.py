#!/usr/bin/env python3
"""Appel texte aux modèles disponibles pour écrire / resserrer les répliques.

Lit video/.env. Gemini est la voie qui répond sur ce poste ; Groq est sondé
aussi, au cas où l'accès au compte serait débloqué depuis.

  python3 build/llm.py --brief "..." [--file consigne.txt] [--max 1200]
"""
import argparse
import json
import pathlib
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from gen_images import load_env  # noqa: E402

STYLE = """Tu écris des répliques pour une vidéo publicitaire française, « LE PLATEAU UNIFLOW » :
un décor d'émission télé, deux personnages qui discutent du projet UniFlow.
- UNI : assistant IA du projet, mascotte robot, vif, second degré, phrases courtes.
- ARCHLORD : le fondateur, étudiant-entrepreneur posé, autodérision, calme.
Règles absolues : français uniquement ; aucune parole technique (pas d'« API »,
de « base de données », de « serveur », de « JSON », de « algorithme ») ; pas de
jargon marketing ; humour sec et tendre ; chaque réplique tient dite à voix haute
en moins de douze secondes ; alterner les longueurs ; ne jamais mentir sur ce que
fait le produit. Format de sortie : une ligne par réplique, préfixée par UNI: ou
ARCHLORD:, sans numérotation ni commentaire."""

GEMINI = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GROQ = "https://api.groq.com/openai/v1/chat/completions"


# gemini-2.5-pro est fermé aux nouveaux comptes sur cette clé (HTTP 404) ;
# gemini-2.5-flash coupe ses répliques en plein milieu. Le troisième tient la
# voix des personnages et respecte les interdits de vocabulaire.
DEFAULT_MODEL = "gemini-3-flash-preview"


def gemini(key, prompt, model=DEFAULT_MODEL, max_tokens=6000):
    # gemini-3 est un modèle à raisonnement : sans budget explicite, il brûle
    # maxOutputTokens en réflexion et la réponse arrive coupée au premier vers.
    cfg = {"temperature": 0.95, "maxOutputTokens": max_tokens}
    if model.startswith(("gemini-2.5", "gemini-3")) or "preview" in model:
        cfg["thinkingConfig"] = {"thinkingBudget": 0}
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": STYLE}]},
            "generationConfig": cfg}
    req = urllib.request.Request(GEMINI.format(model=model), data=json.dumps(body).encode(),
                                 method="POST", headers={"Content-Type": "application/json",
                                                         "x-goog-api-key": key})
    with urllib.request.urlopen(req, timeout=180) as r:
        out = json.loads(r.read())
    return "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"])


def groq(key, prompt, model="llama-3.3-70b-versatile", max_tokens=1400):
    body = {"model": model, "max_tokens": max_tokens, "temperature": 0.95,
            "messages": [{"role": "system", "content": STYLE},
                         {"role": "user", "content": prompt}]}
    req = urllib.request.Request(GROQ, data=json.dumps(body).encode(), method="POST",
                                headers={"Content-Type": "application/json",
                                         "Authorization": f"Bearer {key}",
                                         "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", required=True)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--groq", default="")
    ap.add_argument("--max", type=int, default=6000)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    env = load_env()
    if a.groq:
        try:
            text = groq(env["GROQ_API_KEY"], a.brief, a.groq, a.max)
        except urllib.error.HTTPError as e:
            sys.exit(f"Groq {a.groq}: HTTP {e.code} {e.read().decode()[:160]}")
    else:
        try:
            text = gemini(env["GEMINI_API_KEY"], a.brief, a.model, a.max)
        except urllib.error.HTTPError as e:
            sys.exit(f"Gemini {a.model}: HTTP {e.code} {e.read().decode()[:160]}")
    if a.out:
        pathlib.Path(a.out).write_text(text, encoding="utf-8")
        n = sum(1 for ln in text.splitlines() if ln.strip().startswith(("UNI:", "ARCHLORD:")))
        print(f"{a.out}: {n} repliques, {len(text.split())} mots")
    else:
        print(text)


if __name__ == "__main__":
    main()
