"""Plan de synthèse HeyGen : les 775 répliques groupées en blocs par locuteur.

Un appel par réplique ferait 775 allers-retours. On parle donc par bloc de
~2 600 caractères, dans l'ordre du script, une seule voix par appel, et on
sépare chaque réplique par une respiration plus longue que toutes les pauses
naturelles de la phrase. Le découpage se lit ensuite dans le silence mesuré du
fichier audio : rien ne dépend d'un horodatage qui pourrait se perdre.
"""
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from script_data import LINES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / "work" / "heygen"
URLS = WORK / "urls"
CLAIMS = WORK / "claims"
for d in (WORK, URLS, CLAIMS):
    d.mkdir(parents=True, exist_ok=True)

# 1,05 s entre deux répliques : au-dessus de toute pause intraphrase mesurée,
# et HeyGen le rend tel quel — la coupure se retrouve dans le fichier audio.
BREAK = '<break time="1.05s"/>'
# Respiration à la ponctuation forte. Paul et Chloe vont l'un comme l'autre
# ~18 caractères/seconde contre 15 pour l'ancienne voix : rendre le texte d'un
# trait trop vite ferait une émission essoufflée ET une heure creuse.
RESPIRE = '<break time="0.30s"/>'
# 83,1 : une virgule décimale n'est pas une respiration.
VOISINE = re.compile(r"([;,:])(?!\d)\s*")
CAP = 2500          # caractères SSML par appel, lignes entières
# Débits mesurés sur la même réplique : Paul Broadcaster 18,3 car./s à vitesse
# 1,0 (19,7 à 1,32), Chloe 17,8. Soit ~2 670 s de voix nue pour 48 417 car.
VOIX = {
    "ARCHLORD": dict(id="02733a92a0db457aadf63b235d2aa457", nom="Paul - Broadcaster",
                     vitesse=1.00),
    "UNI": dict(id="4b1de1582d2c477485ad2e0c2717f0ff", nom="Chloe", vitesse=1.00),
}


def echappe(t):
    """Seuls ces trois-là sont SIGNIFIANTS en XML ; « » et ' restent tels quels."""
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def paroles(t):
    """Texte prêt pour le SSML : échappé, respiration posée après la ponctuation."""
    return VOISINE.sub(lambda m: m.group(1) + RESPIRE, echappe(t))


def blocs():
    """Découpe chaque locuteur en blocs de CAP caractères, jamais en pleine ligne."""
    out = []
    for who in ("ARCHLORD", "UNI"):
        idx = [i for i, l in enumerate(LINES) if l["who"] == who]
        cur, taille = [], len(BREAK)
        for i in idx:
            n = len(paroles(LINES[i]["text"])) + len(BREAK) + 1
            if cur and taille + n > CAP:
                out.append((who, cur))
                cur, taille = [], len(BREAK)
            cur.append(i)
            taille += n
        if cur:
            out.append((who, cur))
    return out


def main():
    plan = []
    for b, (who, ids) in enumerate(blocs()):
        v = VOIX[who]
        # HeyGen refuse le SSML sans enveloppe : « Invalid SSML format ».
        texte = f"<speak>{BREAK.join(paroles(LINES[i]['text']) for i in ids)}</speak>"
        plan.append({"id": f"{who[0]}{b:02d}", "who": who, "voiceId": v["id"],
                     "voice": v["nom"], "speed": v["vitesse"], "lines": ids,
                     "ssml": texte, "chars": len(texte), "n": len(ids)})
    (WORK / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    tot = sum(len(re.split(r"\s+", LINES[i]["text"])) for p in plan for i in p["lines"])
    print(f"{len(plan)} appels   répliques : {sum(p['n'] for p in plan)}   mots : {tot}")
    for who in ("ARCHLORD", "UNI"):
        s = [p for p in plan if p["who"] == who]
        print(f"  {who:9s} {len(s):2d} appels, {sum(p['n'] for p in s):3d} répliques, "
              f"{max(p['chars'] for p in s)} car. au plus long")


def show(bloc):
    p = next(x for x in json.loads((WORK / "plan.json").read_text()) if x["id"] == bloc)
    print(f"VOICEID {p['voiceId']}\nSPEED {p['speed']}\n---\n{p['ssml']}")


def _url_f(bloc):
    return URLS / f"{bloc}.txt"


def _claim_f(bloc):
    return CLAIMS / f"{bloc}"


def _lu(bloc):
    f = _url_f(bloc)
    if not f.exists():
        return None
    url, _, dur = f.read_text().partition("\t")
    return url, float(dur or 0)


def next_bloc():
    """La prochaine réplique à jouer, et la réclame à l'exclusivité.

    Les blocs sont pris dans un fichier par appel : plusieurs voix peuvent donc
    tourner en parallèle sans jamais taper deux fois sur le même bloc.
    """
    for p in json.loads((WORK / "plan.json").read_text()):
        if _lu(p["id"]) or _claim_f(p["id"]).exists():
            continue
        try:
            fd = os.open(_claim_f(p["id"]), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            continue
        os.close(fd)
        print(f"BLOC {p['id']}   {p['who']}   {p['voice']}   {p['n']} répliques")
        print(f"VOICEID {p['voiceId']}")
        print(f"SPEED {p['speed']}")
        print("---SSML---")
        print(p["ssml"])
        print("---FIN---")
        return
    print("PLUS RIEN À JOUER")


def note(bloc, url, duree="0"):
    """L'URL suffit : le découpage se lit dans les respirations du fichier."""
    _url_f(bloc).write_text(f"{url}\t{duree}")
    _claim_f(bloc).unlink(missing_ok=True)
    fait = len(list(URLS.glob("*.txt")))
    total = len(json.loads((WORK / "plan.json").read_text()))
    print(f"{bloc} noté   {fait}/{total}")


def etat():
    plan = json.loads((WORK / "plan.json").read_text())
    faits = [p["id"] for p in plan if _lu(p["id"])]
    reclames = [p["id"] for p in plan
                if not _lu(p["id"]) and _claim_f(p["id"]).exists()]
    reste = [p["id"] for p in plan if p["id"] not in faits + reclames]
    d = sum(_lu(i)[1] for i in faits)
    print(f"faits {len(faits)}/{len(plan)}   réclamés {len(reclames)}   "
          f"restants {len(reste)}   durée cumulée {d/60:.1f} min")
    if reste:
        print("RESTE :", " ".join(reste))
    if reclames:
        print("EN COURS :", " ".join(reclames))


def fetch():
    """Télécharge les blocs annoncés et rend compte de ce qui manque encore."""
    import urllib.request
    plan = json.loads((WORK / "plan.json").read_text())
    bloques = WORK / "blocks"
    bloques.mkdir(exist_ok=True)
    manque = []
    for p in plan:
        u = _lu(p["id"])
        if not u:
            manque.append(p["id"])
            continue
        cible = bloques / f"{p['id']}.wav"
        if cible.exists() and cible.stat().st_size > 50000:
            continue
        req = urllib.request.Request(u[0], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=180) as r, open(cible, "wb") as fh:
            fh.write(r.read())
        print(f"{p['id']}  {cible.stat().st_size/1e6:.2f} Mo")
    if manque:
        print("EN ATTENTE :", " ".join(manque))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        main()
    elif a[0] == "show":
        show(a[1])
    elif a[0] == "note":
        note(a[1], a[2], a[3] if len(a) > 3 else "0")
    elif a[0] == "next":
        next_bloc()
    elif a[0] == "etat":
        etat()
    elif a[0] == "fetch":
        fetch()
    else:
        main()
