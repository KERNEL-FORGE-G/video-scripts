"""Découpe les planches de sprites en silhouettes isolées.

Deux familles de planches, deux fonds : les unes portent une vraie alpha, les
autres un damier « transparence » peint dans l'image. Le damier touche le bord,
les blancs du dessin (dents, lacets) jamais : une inondation depuis le contour
retire l'un sans manger les autres.

Le repérage des cases se fait par composantes connexes, pas par projection. La
projection échoue ici : les cycles de marche sont dessinés si serrés qu'une
rangée entière se touche, et une colonne vide n'y existe jamais.
"""
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "assets" / "planches"


def masque(n):
    """Pixels à garder : alpha authentique, ou fond neutre retiré par inondation."""
    a = np.asarray(Image.open(P / n).convert("RGBA"), np.uint8)
    al = a[..., 3]
    if al.min() == 0:
        return al > 24
    v = a[..., :3].astype(np.int16)
    # Seuls les neutres CLAIRS sont du fond : le damier est fait de deux gris
    # pâles. Y mêler les sombreurs ferait manger le pantalon marine du garçon,
    # qui est un neutre foncé et touche le damier — la jambe disparaîtrait.
    cand = np.ascontiguousarray(((v.max(2) - v.min(2)) < 30) & (v.mean(2) > 150))
    h, w = cand.shape
    retir = np.zeros_like(cand)
    q = deque()

    def arrose(y, x):
        if cand[y, x] and not retir[y, x]:
            retir[y, x] = True
            q.append((y, x))

    for x in range(w):
        arrose(0, x)
        arrose(h - 1, x)
    for y in range(h):
        arrose(y, 0)
        arrose(y, w - 1)
    while q:
        y, x = q.popleft()
        if y:
            arrose(y - 1, x)
        if y + 1 < h:
            arrose(y + 1, x)
        if x:
            arrose(y, x - 1)
        if x + 1 < w:
            arrose(y, x + 1)
    return ~retir


def _segments(ligne):
    xs = np.flatnonzero(ligne)
    if xs.size == 0:
        return []
    out, d, f = [], int(xs[0]), int(xs[0])
    for x in map(int, xs[1:]):
        if x == f + 1:
            f = x
            continue
        out.append((d, f))
        d = f = x
    out.append((d, f))
    return out


def composants(m, pixels_min=900):
    """Boîtes [x0,y0,x1,y1,n,étiquette] des composantes connexes, triées ligne à ligne,
    et l'image d'étiquette qui va avec.

    Étiquetage par fusion de segments : une passe par rangée, jamais par pixel.
    L'étiquette est indispensable au découpage : deux poses voisines se touchent
    souvent (un bras qui dépasse), et la boîte englobante du sprite d'à côté
    embarque alors un morceau de son voisin. Seul le masque d'étiquette sait
    distinguer les deux.
    """
    parent, segments, prev = [], [], []

    def racine(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for y in range(m.shape[0]):
        cur = []
        for x0, x1 in _segments(m[y]):
            lab = len(parent)
            parent.append(lab)
            ret = {racine(p) for px0, px1, p in prev if px0 <= x1 and x0 <= px1}
            if ret:
                k = min(ret)
                parent[lab] = k
                for t in ret:
                    if t != k:
                        parent[max(t, k)] = min(t, k)
                lab = k
            cur.append((x0, x1, lab))
            segments.append((y, x0, x1, lab))
        prev = cur

    boites = {}
    for y, x0, x1, lab in segments:
        r = racine(lab)
        b = boites.get(r)
        if b is None:
            boites[r] = [x0, y, x1, y, x1 - x0 + 1, r]
        else:
            b[0] = min(b[0], x0)
            b[1] = min(b[1], y)
            b[2] = max(b[2], x1)
            b[3] = max(b[3], y)
            b[4] += x1 - x0 + 1
    toutes = sorted(boites.values(), key=lambda b: (b[1] // 90, b[0]))
    gros = [b for b in toutes if b[4] >= pixels_min]
    etiq = np.full(m.shape, -1, np.int32)
    for y, x0, x1, lab in segments:
        etiq[y, x0:x1 + 1] = racine(lab)
    return gros, etiq, toutes


def rangees_groupees(boites, tol=0.45):
    """Regroupe par rangée : deux boîtes sont de la même si elles se chevauchent
    assez en vertical — les sprites montent et descendent, l'index brut y ment."""
    groupes = []
    for b in sorted(boites, key=lambda z: z[1]):
        h = b[3] - b[1] + 1
        for g in groupes:
            commun = min(g[2], b[3]) - max(g[1], b[1])
            if commun > tol * min(h, g[2] - g[1]):
                g[0].append(b)
                g[1] = min(g[1], b[1])
                g[2] = max(g[2], b[3])
                break
        else:
            groupes.append([[b], b[1], b[3]])
    out = []
    for g in sorted(groupes, key=lambda z: z[1]):
        g[0].sort(key=lambda z: z[0])
        out.append(g[0])
    return out


def rangees(boites, tol=0.45):
    return [b for rang in rangees_groupees(boites, tol) for b in rang]
