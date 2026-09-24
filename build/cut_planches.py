"""Découpe les planches de sprites de `assets/planches/` en poses isolées.

Deux familles, deux méthodes :

* les planches 5 et 6 (Archlord et Uni, 25 poses chacun) laissent entre deux
  cases une bande de pixels entièrement transparente : la projection des pleins
  la retrouve et la coupe tombe pile dans le creux. La grille arithmétique, elle,
  tronquait les pieds du rang du dessus — mesuré, les lignes vides réelles
  glissent jusqu'à 15 px plus bas que le cinquième théorique ;
* les planches 1 à 4 (« garçon », « robot ») portent un damier de transparence
  PEINT dans l'image et des cases qui se touchent : aucune colonne vide n'y
  existe, seule la composante connexe distingue deux poses voisines.

    python3 build/cut_planches.py          # toutes les planches
    python3 build/cut_planches.py 5 6      # seulement quelques-unes

Écrit `assets/sprites/<plaque>_<rang>_<col>.png` et `assets/sprites/manifeste.json`.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "planches"
OUT = ROOT / "assets" / "sprites"

sys.path.insert(0, str(Path(__file__).parent))
from planche_grille import composants, masque, rangees_groupees  # noqa: E402

PLANCHES = {
    1: ("garcon", "Sprite Sheet 1 - Garçon Sweat Bleu - Poses de Base.png"),
    2: ("garcon", "Sprite Sheet 2 - Garçon Sweat Bleu - Actions.png"),
    3: ("robot", "Sprite Sheet 3 - Robot Astronautique - Poses de Base.png"),
    4: ("robot", "Sprite Sheet 4 - Robot Astronautique - Actions.png"),
    5: ("archlord", "01_Planche_sprites_Archlord.png"),
    6: ("uni", "02_Planche_sprites_Uni.png"),
}
BANDES = {5, 6}
HAUTEUR_MIN = 110          # sous ce seuil : un fragment de halo, pas une pose
MARGE = 3


def bandes(v, soude=6):
    """Intervalles [d,f) où la projection sort du vide, gaps < soude soudés."""
    plein = np.asarray(v) > 0
    out, d = [], None
    for i, p in enumerate(plein):
        if p and d is None:
            d = i
        elif not p and d is not None:
            if out and i - out[-1][1] < soude:
                out[-1] = (out[-1][0], i)
            else:
                out.append((d, i))
            d = None
    if d is not None:
        out.append((d, len(plein)))
    return out


def serre(garde):
    """Boîte [x0,y0,x1,y1] serrée autour du pixel gardé, ou None si la zone est vide."""
    xs = np.flatnonzero(garde.any(0))
    ys = np.flatnonzero(garde.any(1))
    if xs.size == 0 or ys.size == 0:
        return None
    h, w = garde.shape
    return (max(0, int(xs[0]) - MARGE), max(0, int(ys[0]) - MARGE),
            min(w, int(xs[-1]) + 1 + MARGE), min(h, int(ys[-1]) + 1 + MARGE))


def ecrit(a, garde, box, qui, num, j, i):
    x0, y0, x1, y1 = box
    morceau = a[y0:y1, x0:x1].copy()
    # Le masque est binaire ; sur une planche à alpha authentique il ne doit pas
    # écraser les bords adoucis : on le combine au minimum des deux. Sur le damier
    # peint l'alpha d'origine est 255 partout, le masque seul décide.
    ok = np.where(garde[y0:y1, x0:x1], 255, 0).astype(np.uint8)
    morceau[..., 3] = np.minimum(morceau[..., 3], ok)
    ident = f"{num}_{j}_{i}"
    Image.fromarray(morceau, "RGBA").save(OUT / f"{ident}.png")
    return dict(id=ident, planche=num, qui=qui, rang=j, colone=i,
                box=[x0, y0, x1, y1], h=y1 - y0, w=x1 - x0)


def par_bandes(qui, nom, num):
    m = masque(nom)
    a = np.asarray(Image.open(SRC / nom).convert("RGBA"), np.uint8)
    h, w = m.shape
    fiches = []
    for j, (y0, y1) in enumerate(bandes(m.any(1))):
        if y1 - y0 < 40:                      # un liseré, pas une rangée de poses
            continue
        zone = m[y0:y1]
        for i, (x0, x1) in enumerate(bandes(zone.any(0))):
            if x1 - x0 < 30:
                continue
            box = (max(0, x0 - MARGE), max(0, y0 - MARGE),
                   min(w, x1 + MARGE), min(h, y1 + MARGE))
            fiches.append(ecrit(a, m, box, qui, num, j, i))
    return fiches


def par_composantes(qui, nom, num):
    m = masque(nom)
    a = np.asarray(Image.open(SRC / nom).convert("RGBA"), np.uint8)
    boites, etiq, toutes = composants(m)
    # la rangée vient du recouvrement vertical, la colonne de l'abscisse croissante
    rangs = [[b for b in r if b[3] - b[1] >= HAUTEUR_MIN and b[2] - b[0] >= 60]
             for r in rangees_groupees(boites)]
    fiches = []
    for j, rang in enumerate(r for r in rangs if r):
        for i, (x0, y0, x1, y1, n, cle) in enumerate(rang):
            # Une pose ne garde que SON pixel : deux cases voisines se touchent
            # souvent — un bras qui dépasse — et la boîte englobante embarquerait
            # l'épaule du voisin. Les menus détours d'une même case (l'étoile
            # ramassée, les lignes de vitesse) la suivent dès qu'ils tiennent
            # entièrement dans sa boîte.
            garde = etiq == cle
            for t in toutes:
                if t[5] != cle and t[4] < n and t[0] >= x0 and t[1] >= y0 \
                        and t[2] <= x1 and t[3] <= y1:
                    garde |= etiq == t[5]
            b = serre(garde)
            if b:
                fiches.append(ecrit(a, garde, b, qui, num, j, i))
    return fiches


def decoupe(num):
    qui, nom = PLANCHES[num]
    OUT.mkdir(parents=True, exist_ok=True)
    for stale in OUT.glob(f"{num}_*.png"):        # un re-découpage change la grille
        stale.unlink()
    return par_bandes(qui, nom, num) if num in BANDES else par_composantes(qui, nom, num)


if __name__ == "__main__":
    choix = [int(a) for a in sys.argv[1:]] or sorted(PLANCHES)
    tout = []
    for n in choix:
        f = decoupe(n)
        tout += f
        print(f"planche {n} : {len(f)} poses   " +
              "  ".join(f"{x['rang']}.{x['colone']}={x['h']}x{x['w']}" for x in f))
    # un run partiel ne doit pas effacer les poses des autres planches
    garde = []
    if (OUT / "manifeste.json").exists():
        deja = json.loads((OUT / "manifeste.json").read_text())
        faits = {x["id"] for x in tout}
        garde = [x for x in deja if x["id"] not in faits and (OUT / f"{x['id']}.png").exists()]
    tout = sorted(garde + tout, key=lambda x: (x["planche"], x["rang"], x["colone"]))
    (OUT / "manifeste.json").write_text(json.dumps(tout, ensure_ascii=False, indent=1))
    print(f"\n{len(tout)} poses écrites dans {OUT.relative_to(ROOT)}")
