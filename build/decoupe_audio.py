"""Découpe les blocs HeyGen en une piste par réplique, puis rebâtit timings.json.

Un bloc est une suite de répliques séparées par `<break time="1.05s"/>`. La
coupure se lit dans le silence MESURÉ du fichier, jamais dans les horodatages
rendus par l'API : ils sont trop volumineux pour être conservés, et une coupe
au milieu d'un mot se voit et s'entend immédiatement.

    python3 build/decoupe_audio.py

Seuil de respiration : 1,05 s imposés par le SSML contre 0,30 s au point-virgule
et moins de 0,3 s à la ponctuation faible. Une fenêtre à 0,62 s ne peut donc
attraper que les vraies fin de réplique — et si un bloc s'en écarte, on retombe
sur les fentes les plus larges, puis sur une répartition proportionnelle.
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from script_data import LINES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "heygen"
BLOCS = WORK / "blocks"
AUDIO = ROOT / "audio"

SR = 48000
FENETRE = 0.62        # une respiration de réplique, au sens du SSML


def rms_env(s, ms=10):
    n = int(SR * ms / 1000)
    p = len(s) // n * n
    return np.sqrt((s[:p].reshape(-1, n) ** 2).mean(1) + 1e-12)


def decode(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le",
                        "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).copy()


def fentes(env, pas):
    """Indices de fenêtre où le niveau reste sous le seuil sur toute la fente."""
    fort = np.percentile(env, 95)
    seuil = max(0.0045, 0.11 * fort)
    muet = env < seuil
    out = []
    i = 0
    while i + pas <= len(muet):
        if muet[i:i + pas].all():
            j = i
            while j + pas <= len(muet) and muet[j:j + pas].all():
                j += 1
            out.append(((i + j) / 2 * pas, j * pas))
            i = j + pas
        else:
            i += 1
    return out


def ecrit(path, s):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(s, -1, 1) * 32767).astype("<i2").tobytes())


def main():
    plan = json.loads((WORK / "plan.json").read_text())
    choisis = [a for a in sys.argv[1:] if not a.startswith("-")]
    partiel = bool(choisis)
    if partiel:
        plan = [p for p in plan if p["id"] in choisis]
    AUDIO.mkdir(exist_ok=True)
    if not partiel:
        for f in AUDIO.glob("line_*.wav"):
            f.unlink()
    manquent = [p["id"] for p in plan if not (BLOCS / f"{p['id']}.wav").exists()]
    if manquent:
        sys.exit(f"{len(manquent)} blocs absents : {' '.join(manquent)}")

    minuterie = {}
    recoupe = 0
    for p in plan:
        s = decode(BLOCS / f"{p['id']}.wav")
        env = rms_env(s)
        pas = int(FENETRE * 1000 / 10)
        fentes = [(a, b) for a, b in fentes(env, pas)]
        n = len(p["lines"])
        want = n - 1
        if len(fentes) > want:                       # respirations trop marquées
            fentes = sorted(fentes, key=lambda z: -(z[1] - z[0]))[:want]
            fentes.sort()
        if len(fentes) == want:
            coupe = [0.0] + [a / 1000 for a, b in fentes] + [len(s) / SR]
        else:
            # pas assez de silence mesuré : on répartit au prorata des
            # caractères, en cherchant le point le plus calme autour de la
            # frontière théorique.
            recoupe += 1
            tot = sum(len(LINES[i]["text"]) for i in p["lines"])
            coupe = [0.0]
            for k in range(1, n):
                cible = len(s) / SR * (sum(len(LINES[i]["text"])
                                           for i in p["lines"][:k]) / tot)
                fen = int(cible * 1000)
                lo, hi = max(0, fen - 90), min(len(env) - pas, fen + 90)
                mieux = min(range(lo, max(lo + 1, hi + pas)), key=lambda i: env[i:i + pas].mean())
                coupe.append(mieux / 1000)
            coupe.append(len(s) / SR)
        for k, idx in enumerate(p["lines"]):
            a = coupe[k]
            b = coupe[k + 1]
            troncon = s[int(a * SR):max(int(a * SR) + 1, int(b * SR))]
            muet = np.abs(troncon) < 0.006
            i = int(np.argmax(~muet)) if (~muet).any() else 0
            j = len(troncon) - int(np.argmax(~muet[::-1])) if (~muet).any() else len(troncon)
            morceau = troncon[max(0, i - int(0.03 * SR)):min(len(troncon), j + int(0.10 * SR))]
            minuterie[idx] = dict(i=idx, who=LINES[idx]["who"], file=f"line_{idx:02d}.wav",
                                  dur=round(len(morceau) / SR, 3), words=[],
                                  text=LINES[idx]["text"])
            ecrit(AUDIO / f"line_{idx:02d}.wav", morceau)

    minuterie = [minuterie[i] for i in sorted(minuterie)]
    nue = sum(m["dur"] for m in minuterie)
    if not partiel:
        if len(minuterie) != len(LINES):
            sys.exit(f"{len(minuterie)} pistes pour {len(LINES)} répliques")
        (AUDIO / "timings.json").write_text(json.dumps(minuterie, ensure_ascii=False))
    print(f"{len(minuterie)} pistes   parole nue {nue/60:.1f} min   "
          f"blocs retranchés à la proportionnelle : {recoupe}")
    courtes = [m["i"] for m in minuterie if m["dur"] < 0.45]
    if courtes:
        print("SUSPECTES (<0,45 s) :", courtes[:20])


if __name__ == "__main__":
    main()
