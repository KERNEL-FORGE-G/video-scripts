"""Rendu image par image de « Le Plateau UniFlow » — 1920x1080 / 25 i/s.

Les décors sont fournis en 2048x1152 (espace-monde). La caméra y prélève une
fenêtre qu'elle ramène au cadre ; les mascottes sont calées sur le sol du monde
(ombre de contact, reflet, halo) et suivent donc le mouvement de caméra.
L'habillage d'antenne (loquet, cartouche, sous-titre, incrustation) se dessine
par-dessus, dans l'espace du cadre.

    python3 build/render.py                     # -> out/video_only.mp4
    python3 build/render.py --stills 4 78 200   # -> work/still_*.png
    python3 build/render.py --seconds 30        # rendu d'amorçage
    python3 build/render.py --720p --debut 0 --fin 150 --out work/part_000.mp4

La construction complète, reprenable partie par partie, est pilotée par
`bash run.sh` à la racine du dossier.
"""
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS, KEYS, OUT, WORK = ROOT / "assets", ROOT / "keyframes", ROOT / "out", ROOT / "work"
W, H, FPS = 1920, 1080, 25
# Le cadre de dessin reste le 1080 : toute l'habillage est calibré pour lui.
# --720p ne change que la sortie, l'image est réduite après composition, ce qui
# divise par deux le coût du grain et le poids du fichier sans déplacer un pixel
# de la mise en page déjà contrôlée.
SW, SH = W, H
WW, WH = 2048, 1152
NAVY, CYAN, ORANGE, WHITE = (30, 58, 138), (56, 214, 255), (249, 130, 38), (255, 255, 255)
INK = (7, 12, 30)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
XFADE = 0.24
SUB_PX = 43

# ------------------------------------------------------------------- les plans
# a / b = (qui, x du pied, y du sol, taille) — coordonnées du décor
SHOTS = {
    # Chaque plaque a sa ligne de sol, lisible dans build_decors.py : les pieds
    # des deux personnages s'y posent exactement. Un pied plus haut que la
    # plateforme, et la mascotte flotte ; plus bas, elle s'y enterre.
    "wide": dict(plate="plate_wide.webp", vy=1.0,
                 a=("ARCHLORD", 455, 930, 415), b=("UNI", 1690, 930, 380),
                 cam=(1.030, 1.085)),
    # « med » est la même plaque que « wide » : plateau identique, deux caméras.
    # Les zooms d'avant (1,035 contre 1,030) ne différenciaient les deux plans
    # que de trente-cinq pixels de monde — le cut se lisait comme une erreur.
    "med": dict(plate="plate_wide.webp", vy=1.0,
                a=("ARCHLORD", 620, 930, 540), b=("UNI", 1430, 930, 495),
                cam=(1.300, 1.380)),
    "demo": dict(plate="plate_demo.webp", vy=1.0,
                 a=("ARCHLORD", 455, 968, 555), b=("UNI", 1420, 968, 515),
                 cam=(1.030, 1.090)),
    "campus": dict(plate="plate_campus.webp", vy=1.0, scrim=60,
                   a=("ARCHLORD", 500, 1000, 515), b=("UNI", 1450, 1000, 475),
                   cam=(1.020, 1.075)),
    "compare": dict(plate="plate_compare.webp", vy=1.0,
                    a=("ARCHLORD", 545, 1010, 540), b=("UNI", 1360, 1010, 500),
                    cam=(1.030, 1.090)),
    "audience": dict(plate="plate_audience.webp", vy=1.0,
                     a=("ARCHLORD", 620, 1035, 425), b=("UNI", 1330, 1035, 395),
                     cam=(1.020, 1.065)),
    "backstage": dict(plate="plate_backstage.webp", vy=1.0,
                      a=("ARCHLORD", 560, 985, 515), b=("UNI", 1450, 985, 475),
                      cam=(1.025, 1.085)),
    "outro": dict(plate="plate_outro.webp", vy=1.0, scrim=40,
                  a=("ARCHLORD", 530, 930, 400), b=("UNI", 1610, 930, 360),
                  cam=(1.030, 1.045)),
    # Les six scènes neuves. Le y à None se lit dans le décor : une plaque
    # redessinée entraîne ses personnages au lieu de les laisser flotter.
    "amphi": dict(plate="plate_amphi.webp", vy=1.0, tech="right",
                  a=("ARCHLORD", 430, None, 500), b=("UNI", 1620, None, 460),
                  cam=(1.030, 1.090)),
    "portail": dict(plate="plate_portail.webp", vy=1.0, scrim=55,
                    a=("ARCHLORD", 690, None, 505), b=("UNI", 1400, None, 465),
                    cam=(1.020, 1.075)),
    "reseau": dict(plate="plate_reseau.webp", vy=1.0, tech="left",
                   a=("ARCHLORD", 380, None, 500), b=("UNI", 1180, None, 460),
                   cam=(1.030, 1.090)),
    "sentinelle": dict(plate="plate_sentinelle.webp", vy=1.0, tech="right",
                       a=("ARCHLORD", 470, None, 500), b=("UNI", 1620, None, 460),
                       cam=(1.025, 1.085)),
    # « avenir » n'a pas de ligne de sol : la scène monte en gradins, et la
    # profondeur se dit justement en posant Uni sur un palier plus haut.
    "avenir": dict(plate="plate_avenir.webp", vy=1.0, scrim=50, tech="left",
                   a=("ARCHLORD", 280, 900, 500), b=("UNI", 1330, 694, 400),
                   cam=(1.060, 1.140)),
    "forum": dict(plate="plate_forum.webp", vy=1.0, scrim=25, tech="right",
                  a=("ARCHLORD", 480, None, 500), b=("UNI", 1690, None, 460),
                  cam=(1.025, 1.085)),
}
FLIP = {"uni_pointing": True}   # Uni est à droite : il doit montrer Archlord
# Le check de poing est calibré sur « wide » (470 px pour un Archlord de 415) :
# le facteur suit l'échelle de chaque plan au lieu de la contredire.
DUAL = dict(pose="archlord_uni_fistbump", k=470 / 415)

# uni_headset est écarté des poses de plateau : c'est un buste sans jambes,
# toutes les autres silhouettes sont entières et se posent au sol de la même façon.
LISTEN = {"ARCHLORD": "archlord_thinking", "UNI": "uni_thinking"}


def _reglage():
    """Raccorde les plans au décor qui les a produits.

    La ligne de sol est écrite deux fois par construction — une fois dans
    build_decors.py sous la forme m.sol(y), une fois ici sous la forme du y d'un
    tuple (qui, x, y, taille). C'est de la dérive en attente : un pied plus haut
    que la plateforme et la mascotte flotte pendant quatre-vingt-seize minutes.
    Le sidecar fait foi ; un y écrit « None » ici se voit remplacer celui du
    décor, un y chiffré qui le contredit arrête le rendu au lieu de le laisser
    partir avec un défaut visible.
    """
    f = KEYS / "decors.json"
    if not f.exists():
        return {}
    d = json.loads(f.read_text())
    for cle, spec in SHOTS.items():
        ent = d.get(spec["plate"][len("plate_"):-len(".webp")])
        if not ent or ent.get("sol") is None:
            continue
        spec.setdefault("tech", ent.get("tech", "left"))
        for cot in ("a", "b"):
            qui, x, y, h = spec[cot]
            if y is None:
                spec[cot] = (qui, x, ent["sol"], h)
            elif y != ent["sol"]:
                raise SystemExit(f"plan « {cle} » : render.py pose les pieds à y={y}, "
                                 f"le décor « {spec['plate']} » dit {ent['sol']}")
    return d


DECORS = _reglage()

_c, _BGC = {}, {}
_BGN = 0


# ------------------------------------------------------------------- fabriques
def font(path, size):
    k = ("fnt", path, size)
    if k not in _c:
        _c[k] = ImageFont.truetype(path, size)
    return _c[k]


def load(d, name, mode="RGB"):
    k = (mode, str(d / name))
    if k not in _c:
        _c[k] = Image.open(d / name).convert(mode)
    return _c[k]


def mascot(pose):
    k = ("mas", pose)
    if k not in _c:
        im = load(ASSETS, f"{pose}.png", "RGBA")
        im = im.crop(im.getchannel("A").getbbox())
        if FLIP.get(pose):
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        _c[k] = im
    return _c[k]


def sized(pose, h):
    """Mascotte à la hauteur voulue — palier de 6 px pour que le cache tienne."""
    h = max(16, int(round(h / 6.0) * 6))
    k = ("sz", pose, h)
    if k not in _c:
        im = mascot(pose)
        _c[k] = im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)
    return _c[k]


def dimmed(im, dim):
    """Celui qui écoute : éteint et teinté du bleu de la scène."""
    k = ("dm", id(im), round(dim, 3))
    if k in _c:
        return _c[k]
    if dim > 0.998:
        _c[k] = im
        return im
    a = np.asarray(im).astype(np.float32)
    rgb = a[..., :3] * dim + np.array(NAVY, np.float32) * (1 - dim) * 0.55
    _c[k] = Image.fromarray(np.dstack([np.clip(rgb, 0, 255), a[..., 3]]).astype("uint8"), "RGBA")
    return _c[k]


def fainted(im, alpha):
    k = ("fa", id(im), round(alpha, 2))
    if k in _c:
        return _c[k]
    out = im.copy()
    out.putalpha(out.getchannel("A").point(lambda v: int(v * alpha)))
    _c[k] = out
    return out


def contact(w_px, h_px):
    k = ("ct", w_px, h_px)
    if k not in _c:
        m = Image.new("L", (w_px * 2, h_px * 2), 0)
        ImageDraw.Draw(m).ellipse([int(w_px * .22), int(h_px * .85),
                                   int(w_px * 1.78), int(h_px * 1.75)], fill=175)
        _c[k] = m.filter(ImageFilter.GaussianBlur(max(2, h_px // 3)))
    return _c[k]


def mirror(im):
    k = ("mr", id(im))
    if k not in _c:
        r = im.transpose(Image.FLIP_TOP_BOTTOM).copy()
        a = r.getchannel("A").point(lambda v: int(v * 0.22))
        g = Image.new("L", r.size, 0)
        d = ImageDraw.Draw(g)
        for y in range(r.height):
            d.line([(0, y), (r.width, y)], fill=int(255 * (1 - y / r.height) ** 2.2))
        r.putalpha(Image.composite(a, Image.new("L", r.size, 0), g))
        _c[k] = r.filter(ImageFilter.GaussianBlur(1.6))
    return _c[k]


def halo(h_px, color):
    k = ("hl", h_px, color)
    if k not in _c:
        s = int(h_px * 1.3) | 1
        m = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        ImageDraw.Draw(m).ellipse([s * .2, s * .2, s * .8, s * .8], fill=color + (58,))
        _c[k] = m.filter(ImageFilter.GaussianBlur(s // 10))
    return _c[k]


def vignette_map():
    k = ("vg",)
    if k not in _c:
        y, x = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((x - W / 2) / (W * .56)) ** 2 + ((y - H / 2) / (H * .62)) ** 2)
        _c[k] = (np.clip((d - 0.58) / 0.72, 0, 1) ** 1.7 * 0.40)[..., None]
    return _c[k]


def scrim_map():
    """Voiles haut et bas : les clartés du plateau ne mangent pas l'habillage."""
    k = ("sc",)
    if k not in _c:
        col = np.zeros((H, 1), np.float32)
        yy = np.arange(H, dtype=np.float32)
        top = 0.42 * np.clip(1 - yy / 175, 0, 1) ** 1.6
        bot = 0.48 * np.clip((yy - (H - 360)) / 360, 0, 1) ** 1.7
        col[:, 0] = np.maximum(top, bot)
        _c[k] = np.repeat(col, W, axis=1)[..., None]
    return _c[k]


def grade(bg, scrim):
    a = np.asarray(bg, np.float32)
    dark = 1.0 - np.maximum(vignette_map(), scrim_map())
    if scrim:
        dark = dark * (1.0 - scrim / 255.0)
    return Image.fromarray(np.clip(a * dark, 0, 255).astype("uint8"), "RGB")


GRAIN = None


def grain_tiles():
    global GRAIN
    if GRAIN is None:
        t = []
        for s in range(4):
            n = np.random.default_rng(1000 + s).standard_normal((SH // 2, SW // 2)) * 2.6
            n = np.repeat(np.repeat(n, 2, 0), 2, 1) + 128.0
            t.append(Image.fromarray(np.clip(n, 0, 255).astype("uint8"), "L"))
        GRAIN = t
    return GRAIN


def dust():
    k = ("dust",)
    if k not in _c:
        r = np.random.default_rng(7)
        _c[k] = np.stack([r.random(26) * SW, r.random(26) * SH,
                          0.35 + r.random(26) * 1.5, r.random(26) * 6.28], -1)
    return _c[k]


def ease(x):
    return x * x * (3 - 2 * x) if 0 <= x <= 1 else min(1.0, max(0.0, x))


def back_out(x, s=1.70158):
    x -= 1
    return 1 + x * x * ((s + 1) * x + s)


# ------------------------------------------------------------------- caméra
def view(spec, prog, bias):
    z0, z1 = spec["cam"]
    z = z0 + (z1 - z0) * prog
    ww, wh = WW / z, WH / z
    return (WW - ww) * 0.5 + bias, (WH - wh) * spec.get("vy", 1.0), ww, wh


def background(spec, vw):
    global _BGN
    x0, y0, ww, wh = vw
    key = (spec["plate"], round(x0 / 4), round(y0 / 4), round(ww / 4))
    if key not in _BGC:
        if _BGN > 36:
            _BGC.clear()
            _BGN = 0
        box = (max(0.0, x0), max(0.0, y0), min(float(WW), x0 + ww), min(float(WH), y0 + wh))
        _BGC[key] = grade(load(KEYS, spec["plate"]).crop(box).resize((W, H), Image.BILINEAR),
                          spec.get("scrim", 0))
        _BGN += 1
    return _BGC[key]


def scale_of(vw):
    return W / vw[2]


# ------------------------------------------------------------------- personnages
def draw_figure(dst, vw, fx, fy, pose, hgt, dim, bob, tilt, tint, alpha=1.0):
    """Un corps posé au sol du monde : halo, reflet, ombre de contact, silhouette."""
    s = scale_of(vw)
    im = sized(pose, hgt * s)
    if alpha < 0.995:
        im = fainted(im, alpha)
    if dim < 0.998:
        im = dimmed(im, dim)
    x = (fx - vw[0]) * s
    y = (fy - vw[1]) * s + bob * s
    if abs(tilt) > 0.06:
        body = im.rotate(tilt, resample=Image.BICUBIC, expand=True)
        dx = -(body.width - im.width) / 2
    else:
        body, dx = im, 0
    if alpha > 0.995 and dim > 0.998:
        g = halo(im.height, tint)
        dst.paste(g, (int(x - g.width / 2), int(y - im.height - g.height * 0.30)), g)
    m = mirror(im)
    dst.paste(m, (int(x - m.width / 2), int(y + 1)), m)
    sh = contact(max(8, int(im.width * 0.5)), max(8, int(im.height * 0.05)))
    dst.paste(Image.new("RGBA", sh.size, (0, 0, 0, 0)),
              (int(x - sh.width / 2), int(y - sh.height * 0.65)), sh)
    dst.paste(body, (int(round(x - body.width / 2 + dx)), int(round(y - body.height))), body)


def motion(t, talking, seed):
    """Respiration, appui et hochement : 0,85 Hz quand on parle, 0,18 Hz quand on écoute."""
    if talking:
        return (3.0 * math.sin(t * 5.34) + 1.1 * math.sin(t * 5.3 + seed),
                1.15 * math.sin(t * 1.55 + seed), 1.026 + 0.006 * math.sin(t * 4.6))
    return (1.5 * math.sin(t * 1.1 + seed * 1.7),
            0.5 * math.sin(t * 0.72 + seed), 1.0 + 0.004 * math.sin(t * 2.4 + seed))


def draw_scene(dst, vw, spec, b, wt, vt, seed):
    for who_, fx, fy, hgt in (spec["a"], spec["b"]):
        tint = CYAN if who_ == "UNI" else ORANGE
        talking = who_ == b["who"]
        bob, tilt, br = motion(wt, talking, seed if talking else seed + 2.1)
        if not talking:
            draw_figure(dst, vw, fx, fy, LISTEN[who_], hgt, 0.88, bob, tilt, tint)
        elif b["voice"] > 2.4 and vt > b["voice"] - 1.0:
            k = ease((vt - (b["voice"] - 1.0)) / 1.0)
            draw_figure(dst, vw, fx, fy, LISTEN[who_], hgt, 1.0, bob, tilt, tint, k)
            draw_figure(dst, vw, fx, fy, b["pose"], hgt * br, 1.0, bob, tilt, tint, 1 - k)
        else:
            draw_figure(dst, vw, fx, fy, b["pose"], hgt * br, 1.0, bob, tilt, tint)


# ------------------------------------------------------------------- habillage
def draw_bug(dst, t, b):
    d = ImageDraw.Draw(dst)
    d.ellipse([W - 246, 44, W - 230, 60],
              fill=(232, 62, 62, int(150 + 105 * abs(math.sin(t * 2.4)))))
    d.text((W - 218, 38), "EN DIRECT", font=font(FB, 19), fill=(232, 236, 244, 210))
    wm = load(ASSETS, "uniflow-wordmark-blanc-net-2400.png", "RGBA")
    if ("wm30",) not in _c:
        _c[("wm30",)] = wm.resize((round(wm.width * 30 / wm.height), 30), Image.LANCZOS)
    mark = _c[("wm30",)]
    dst.paste(mark, (W - mark.width - 38, 68), mark)
    if b.get("blooper"):
        d.text((44, 40), timecode(t), font=font(FB, 24), fill=(238, 238, 238, 180))
        d.text((44, 74), f"PRISE {3 + (int(t) // 47) % 6}", font=font(FB, 17),
               fill=(255, 205, 105, 195))


def timecode(t):
    h_, r = divmod(t, 3600)
    m_, s = divmod(r, 60)
    return f"{int(h_):02d}:{int(m_):02d}:{int(s):02d}:{int((s % 1) * FPS):02d}"


def draw_lower(dst, who, vt, vdur):
    """Cartouche du nom : il entre avec la première phrase, il ne traîne pas."""
    if vt < -0.2 or vt > 4.2:
        return
    label = "ARCHLORD" if who == "ARCHLORD" else "UNI"
    role = "Fondateur : Nghomsi Feukouo Ravel" if who == "ARCHLORD" else "Assistant du projet"
    accent = ORANGE if who == "ARCHLORD" else CYAN
    f1, f2 = font(FB, 33), font(FR, 21)
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    w = max(int(probe.textlength(label, font=f1)), int(probe.textlength(role, font=f2))) + 168
    hgt = 98
    left = 96 if who == "ARCHLORD" else W - 96 - w
    t_in = ease(min(1, (vt + 0.2) / 0.38))
    a = min(t_in, ease(min(1, (4.2 - vt) / 0.55)))
    if a <= 0.02:
        return
    card = Image.new("RGBA", (w, hgt), (0, 0, 0, 0))
    dc = ImageDraw.Draw(card)
    dc.rounded_rectangle([0, 0, w - 1, hgt - 1], 10, fill=(10, 18, 42, 226))
    dc.rectangle([0, 0, 7, hgt - 1], fill=accent + (255,))
    dc.text((34, 15), label, font=f1, fill=(255, 255, 255, 255))
    dc.text((35, 58), role, font=f2, fill=(198, 210, 233, 245))
    em = load(ASSETS, "uniflow-ecusson-net-1024.png", "RGBA")
    if ("em74",) not in _c:
        _c[("em74",)] = em.resize((74, 74), Image.LANCZOS)
    card.alpha_composite(_c[("em74",)], (w - 96, 12))
    dc = ImageDraw.Draw(card)
    dc.line([(w - 116, 16), (w - 116, hgt - 16)], fill=(70, 92, 140, 190), width=2)
    x = left + int((1 - t_in) * (-70 if who == "ARCHLORD" else 70))
    dst.alpha_composite(fainted(card, a), (x, 722))


_LAY = {}


def layout(words):
    """Découpe la réplique en blocs d'une à deux lignes, calés sur l'horodatage."""
    k = id(words)
    if k in _LAY:
        return _LAY[k]
    fnt = font(FB, SUB_PX)
    d = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    maxw = W - 380
    rows, cur, cw = [], [], 0.0
    for i, wd in enumerate(words):
        add = d.textlength((" " if cur else "") + wd["t"], font=fnt)
        if cur and cw + add > maxw:
            rows.append(cur)
            cur, cw = [], 0.0
            add = d.textlength(wd["t"], font=fnt)
        cur.append(i)
        cw += add
    if cur:
        rows.append(cur)
    groups = []
    for i in range(0, len(rows), 2):
        grp = rows[i:i + 2]
        idx = [j for row in grp for j in row]
        groups.append((grp, words[idx[0]]["s"], words[idx[-1]]["e"]))
    _LAY[k] = groups
    return groups


def draw_subs(dst, words, wt):
    """Sous-titre mot à mot : le mot prononcé s'allume, la suite reste en veilleuse."""
    if not words:
        return
    grp = layout(words)
    spoken = sum(1 for w_ in words if w_["s"] <= wt + 0.03)
    n = 0
    for i, (rows, s, e) in enumerate(grp):
        idx = [j for r in rows for j in r]
        if idx[0] < spoken <= idx[-1] + 1:
            n = i
            break
        if s <= wt + 0.2 <= e + 0.2:
            n = i
            break
    else:
        n = len(grp) - 1
    rows, s, e = grp[n]
    a = min(ease(min(1, (wt - s + 0.16) / 0.28)), ease(min(1, (e + 0.34 - wt) / 0.28)))
    if a <= 0.02:
        return
    fnt = font(FB, SUB_PX)
    d = ImageDraw.Draw(dst)
    y = H - 88 - 56 * len(rows)
    for row in rows:
        line = " ".join(words[j]["t"] for j in row)
        x = (W - d.textlength(line, font=fnt)) / 2
        for j in row:
            if j == spoken - 1:
                col = ORANGE
            elif j < spoken:
                col = WHITE
            else:
                col = (166, 180, 206)
            d.text((x, y), words[j]["t"], font=fnt, fill=col + (int(255 * a),),
                   stroke_width=3, stroke_fill=(4, 9, 24, int(220 * a)))
            x += d.textlength(words[j]["t"] + " ", font=fnt)
        y += 56


def draw_tech(dst, w, t, spec):
    """Fiche de données glissée à gauche du plateau. La consigne du propriétaire
    est claire : aucune capture à l'antenne, mais un bloc chiffré de temps en
    temps, pris dans la base de faits vérifiée par build/briefs.py."""
    a = min(ease((t - w["at"]) / 0.5), 1 - ease((t - (w["until"] - 0.5)) / 0.5))
    if a <= 0.01:
        return
    # La boîte est fixe, pas le décor : « tech » dit de quel côté du cadre un
    # plan peut l'accueillir sans qu'un montant ou un drapeau la traverse.
    lg, y0 = 436, 148
    droit = spec.get("tech") == "right"
    x0 = W - lg - 40 if droit else 40
    hgt = 76 + len(w["rows"]) * 46
    glisse = 34 * (1 - a)
    x = int(x0 + glisse) if droit else int(x0 - glisse)
    d = ImageDraw.Draw(dst)
    d.rounded_rectangle([x, y0, x + lg, y0 + hgt], 14,
                        fill=(9, 16, 40, int(230 * a)),
                        outline=CYAN + (int(150 * a),), width=2)
    d.rectangle([x, y0, x + 9, y0 + hgt], fill=ORANGE + (int(255 * a),))
    f1, f2, f3 = font(FB, 22), font(FR, 20), font(FB, 26)
    d.text((x + 28, y0 + 14), w["titre"], font=f1, fill=ORANGE + (int(255 * a),))
    d.line([x + 28, y0 + 50, x + lg - 28, y0 + 50], fill=(58, 82, 136, int(210 * a)))
    for i, (lab, val) in enumerate(w["rows"]):
        yy = y0 + 62 + i * 46
        d.text((x + 28, yy), lab, font=f2, fill=(176, 192, 224, int(230 * a)))
        d.text((x + lg - 28 - d.textlength(val, font=f3), yy - 4), val, font=f3,
               fill=(240, 246, 255, int(255 * a)))


def draw_chapter(dst, b, p, nseg):
    """Carte de chapitre, posée sur le plan qui arrive."""
    e = ease(min(1, p / 0.42)) * (1 - ease(max(0, (p - 0.70) / 0.30)))
    if e <= 0.01:
        return
    head, sep, tail = b["seg"].partition("—")
    if sep:
        lab, seg = head.strip().rstrip(",").strip(), tail.strip()
    else:
        lab, seg = "CHAPITRE", b["seg"].strip()
    band = Image.new("RGBA", (W, 132), (0, 0, 0, 0))
    d = ImageDraw.Draw(band)
    w = int(W * 0.78 * ease(min(1, p / 0.5)))
    d.rounded_rectangle([(W - w) / 2, 0, (W + w) / 2, 131], 6, fill=(9, 16, 40, int(232 * e)))
    d.rectangle([(W - w) / 2, 0, (W - w) / 2 + 10, 131], fill=ORANGE + (int(255 * e),))
    d.rectangle([(W - w) / 2, 126, (W + w) / 2, 131], fill=CYAN + (int(205 * e),))
    f0 = font(FB, 24)
    d.text((W / 2 - d.textlength(lab, font=f0) / 2, 16), lab, font=f0, fill=CYAN + (int(235 * e),))
    f1 = font(FB, 56)
    tw = d.textlength(seg, font=f1)
    while tw > w - 300 and f1.size > 26:
        f1 = font(FB, f1.size - 3)
        tw = d.textlength(seg, font=f1)
    d.text((W / 2 - tw / 2, 44), seg, font=f1, fill=(255, 255, 255, int(255 * e)))
    fin = f"{b['rank']} / {nseg}"
    f2 = font(FB, 22)
    d.text(((W + w) / 2 - 44 - d.textlength(fin, font=f2), 52), fin, font=f2,
           fill=(180, 195, 222, int(215 * e)))
    dst.alpha_composite(band, (0, int(796 - (1 - e) * 18)))


def brand_ground():
    """Sol de marque des cartons : dégradé, grille lumineuse en perspective."""
    k = ("brandbg",)
    if k not in _c:
        y, x = np.mgrid[0:H // 4:1j * (H // 4), 0:W // 4:1j * (W // 4)].astype(np.float32)
        Hq, Wq = y.shape
        g = np.clip(1 - np.sqrt(((x - Wq / 2) / (Wq * .48)) ** 2 +
                                ((y - Hq * .58) / (Hq * .62)) ** 2), 0, 1)
        arr = np.dstack([g * 34 + 6, g * 62 + 13, g * 132 + 40]).astype("uint8")
        im = Image.fromarray(arr, "RGB").resize((W, H), Image.BILINEAR)
        d = ImageDraw.Draw(im)
        for i in range(-16, 17):
            d.line([(W / 2 + i * 165, H), (W / 2 + i * 46, H * 0.44)], fill=(44, 82, 158), width=1)
        for j in range(10):
            yy = int(H * 0.44 + (H * 0.56) * (j / 10) ** 2.1)
            d.line([(0, yy), (W, yy)], fill=(44, 82, 158), width=1)
        dark = np.maximum(vignette_map(), scrim_map())
        _c[k] = Image.fromarray(np.clip(np.asarray(im, np.float32) * (1 - dark), 0, 255)
                                .astype("uint8"), "RGB")
    return _c[k]


def bars():
    """Mire d'accordéur, une seule fois : huit bandes plates de 1920x1080."""
    if ("bars",) not in _c:
        im = Image.new("RGB", (W, H))
        d = ImageDraw.Draw(im)
        cols = [(196, 196, 190), (196, 190, 60), (60, 190, 196), (60, 190, 70),
                (196, 60, 190), (196, 60, 60), (60, 60, 196), (24, 24, 32)]
        for i, col in enumerate(cols):
            d.rectangle([i * W / 8, 0, (i + 1) * W / 8, H], fill=col)
        _c[("bars",)] = im
    return _c[("bars",)]


def mire(t):
    """L'allumage du poste : des bandes de couleur sous un grain qui saute,
    balayées par une barre blanche. Le grain est tiré à chaque image, c'est
    justement ce qui ne doit pas se répéter."""
    fond = bars().resize((W // 3, H // 3), Image.BILINEAR).resize((W, H), Image.NEAREST)
    grain = Image.fromarray(
        (np.random.default_rng(int(t * 1000) % 9999).random((H // 3, W // 3))
         * 90).astype("uint8"), "L").resize((W, H), Image.NEAREST)
    a = np.asarray(fond, np.float32) + np.asarray(grain, np.float32)[:, :, None]
    im = Image.fromarray(np.clip(a, 0, 255).astype("uint8"), "RGB")
    y = int((t / 1.15) * H * 1.6) - H * 0.2
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([0, y, W, y + 26], fill=(255, 255, 255, 120))
    d.rectangle([0, y + 26, W, y + 34], fill=(56, 214, 255, 90))
    return im.convert("RGBA")


def draw_title(dst, t, tl):
    """Générique d'ouverture : le poste s'allume, le micro se déclare, le carton
    se monte en quatre temps. Le bandeau du bas donne la durée réelle de la
    coupe, calculée par le plan de tournage — il ne faut pas qu'il annonce
    quinze minutes sur une heure."""
    if t < 1.2:
        dst.alpha_composite(mire(t), (0, 0))
        dst.alpha_composite(Image.new("RGBA", (W, H), INK + (int(255 * (t / 1.2) ** 2),)),
                            (0, 0))
        return
    dst.paste(brand_ground().convert("RGBA"), (0, 0))
    d = ImageDraw.Draw(dst)
    for i, (yy, sp, al) in enumerate([(0.13, 1.0, 20), (0.27, 0.62, 14), (0.76, 1.35, 16)]):
        a = max(6, int(al + al * math.sin(t * 0.9 + i)))
        dst.alpha_composite(Image.new("RGBA", (W, 2), CYAN + (a,)),
                            (0, int(H * (yy + 0.025 * math.sin(t * .5 + i)))))
    em = load(ASSETS, "uniflow-ecusson-net-1024.png", "RGBA")
    s = int(250 * back_out(min(1, (t - 1.15) / 0.9)))
    if s > 10:
        e2 = em.resize((s, s), Image.LANCZOS)
        dst.alpha_composite(e2, (int(W / 2 - s / 2), int(H * 0.115)))
    tally = ease((t - 1.5) / 0.5)
    if tally > 0.01:
        f = font(FB, 24)
        d.rounded_rectangle([W - 330, 34, W - 40, 88], 10,
                            fill=(24, 12, 14, int(215 * tally)),
                            outline=(255, 90, 90, int(200 * tally)), width=2)
        r = 9 + 4 * abs(math.sin(t * 2.4))
        d.ellipse([W - 312, 52 - r, W - 312 + 2 * r, 52 + r],
                  fill=(255, 70, 70, int(255 * tally)))
        d.text((W - 288, 46), "EN DIRECT", font=f, fill=(255, 226, 226, int(240 * tally)))
    p = ease(min(1, (t - 2.1) / 1.0))
    if p > 0.01:
        f = font(FB, 50)
        tw = d.textlength(tl["title"], font=f)
        d.text(((W - tw) / 2 + (1 - p) * -26, H * 0.455), tl["title"], font=f,
               fill=ORANGE + (int(255 * p),))
    a2 = ease((t - 2.9) / 1.0)
    if a2 > 0.01:
        f2 = font(FR, 29)
        tw2 = d.textlength(tl["subtitle"], font=f2)
        d.text(((W - tw2) / 2, H * 0.545), tl["subtitle"], font=f2,
               fill=(206, 217, 239, int(240 * a2)))
    a3 = ease((t - 3.9) / 0.9)
    if a3 > 0.01:
        f3 = font(FB, 40)
        tw3 = d.textlength(tl["link"], font=f3)
        d.rounded_rectangle([(W - tw3) / 2 - 38, H * 0.70, (W + tw3) / 2 + 38, H * 0.70 + 76],
                            14, fill=ORANGE + (int(34 * a3),), outline=CYAN + (int(215 * a3),), width=3)
        d.text(((W - tw3) / 2, H * 0.70 + 17), tl["link"], font=f3,
               fill=(255, 255, 255, int(255 * a3)))
        f4 = font(FR, 23)
        d.text(((W - d.textlength(tl.get("duree", ""), font=f4)) / 2, H * 0.70 + 90),
               tl.get("duree", ""), font=f4, fill=(178, 194, 224, int(200 * a3)))


def cta(d, t, dt, x, y, titre, ligne):
    """Un carton d'appel, posé à son heure : la consigne du propriétaire est de
    renvoyer le spectateur vers le forum et les groupes WhatsApp, pas seulement
    vers le site."""
    a = ease((t - dt) / 0.55)
    if a <= 0.01:
        return
    f1, f2 = font(FB, 27), font(FR, 22)
    lg = max(d.textlength(titre, font=f1), d.textlength(ligne, font=f2)) + 44
    d.rounded_rectangle([x, y, x + lg, y + 92], 12, fill=(10, 18, 44, int(225 * a)),
                        outline=CYAN + (int(150 * a),), width=2)
    d.text((x + 22, y + 14), titre, font=f1, fill=ORANGE + (int(255 * a),))
    d.text((x + 22, y + 52), ligne, font=f2, fill=(222, 232, 248, int(235 * a)))


def draw_end(dst, t, tl):
    """Générique de fin : le mot de la marque, les chapitres qui montent à
    gauche comme un bandeau, les quatre portes de sortie à droite, l'adresse
    en bas. Neuf secondes ne suffisaient pas à tout poser : la coupe 60 minutes
    lui en donne dix-huit."""
    dst.paste(brand_ground().convert("RGBA"), (0, 0))
    d = ImageDraw.Draw(dst)
    wm = load(ASSETS, "uniflow-wordmark-blanc-net-2400.png", "RGBA")
    s2 = int(130 * back_out(min(1, t / 0.85)))
    if s2 > 10:
        w2 = wm.resize((round(wm.width * s2 / wm.height), s2), Image.LANCZOS)
        dst.alpha_composite(w2, (int(W / 2 - w2.width / 2), int(H * 0.045)))
    for i, (dt, ligne) in enumerate([
            (0.5, "Une maison pour tout le campus"),
            (0.9, "Cours · Horaire · Présences · Notes · Messages"),
            (1.3, "Dix étudiants à Yaoundé — Université de Yaoundé I")]):
        f2 = font(FB if i == 0 else FR, 38 if i == 0 else 26)
        a = int(255 * ease((t - dt) / 0.7))
        if a > 2:
            d.text(((W - d.textlength(ligne, font=f2)) / 2, H * 0.175 + i * 48), ligne,
                   font=f2, fill=(226, 234, 248, a))
    haut = H * 0.34
    a = int(210 * ease((t - 1.8) / 0.6))
    if a > 3:
        d.text((W * 0.06, haut), "AU PROGRAMME", font=font(FB, 22), fill=CYAN + (a,))
        f = font(FR, 24)
        for i, seg in enumerate(tl.get("segs", [])):
            yy = haut + 42 + i * 33 - max(0.0, (t - 3.0)) * 9
            if haut + 34 < yy < H * 0.86:
                d.text((W * 0.06, yy), seg, font=f, fill=(214, 226, 246, int(200 * a / 210)))
    a2 = ease((t - 3.4) / 0.6)
    if a2 > 0.01:
        d.text((W * 0.52, haut), "ET POUR SORTIR DE L'ÉMISSION",
               font=font(FB, 22), fill=CYAN + (int(200 * a2),))
    for dt, i, titre, ligne in [
            (3.8, 0, "POUCE LEVÉ", "si l'heure vous a paru utile"),
            (4.6, 1, "COMMENTAIRE", "une question, une correction, un accord"),
            (5.4, 2, "FORUM UNIFLOW", "vos suggestions entrent par là"),
            (6.2, 3, "WHATSAPP", "+237 6 57 63 56 44 · groupe KERNEL FORGE")]:
        cta(d, t, dt, W * 0.52, haut + 46 + i * 104, titre, ligne)
    a = ease((t - 8.0) / 0.8)
    if a > 0.01:
        f3 = font(FB, 54)
        tw3 = d.textlength(tl["link"], font=f3)
        d.rounded_rectangle([(W - tw3) / 2 - 46, H * 0.875, (W + tw3) / 2 + 46, H * 0.875 + 92],
                            16, fill=ORANGE + (int(240 * a),))
        d.text(((W - tw3) / 2, H * 0.875 + 20), tl["link"], font=f3,
               fill=(255, 255, 255, int(255 * a)))


BROLL_BOX = (700, 392)
BROLL_BOX_TALL = (300, 505)

PAGES = {
    "accueil": "Accueil", "a_propos": "À propos", "connexion": "Connexion",
    "contact": "Contact", "emploi_du_temps": "Emploi du temps", "equipe": "Équipe",
    "forum": "Forum", "inscription": "Inscription", "plateforme": "Plateforme",
    "presences_qr": "Présences QR", "presentation": "Présentation",
    "sentinelle": "Sentinelle", "tarifs": "Tarifs", "telecharger": "Télécharger",
    "tableau_de_bord": "Tableau de bord", "cours": "Mes cours",
    "devoirs": "Devoirs & TP", "messagerie": "Messagerie",
    "notifications": "Notifications", "delegue": "Être délégué",
    "parametres": "Mon profil", "aide": "Centre d'aide", "videos": "Vidéos",
    "tous_ecrans": "Tous les écrans", "admin": "Administration",
    "videotheque": "Vidéothèque", "forum_avis": "Avis vérifiés",
    "contact_equipe": "Contacter l'équipe",
    "hero": "Accueil", "chiffres": "En chiffres",
    "fondateur": "Le mot du fondateur", "vie_fac": "Dans la poche",
    "pourquoi": "Pourquoi UniFlow", "piliers": "Ce qu'il fait",
    "etapes": "Comment ça marche", "appel": "Rejoindre",
    "kernel_forge": "Kernel Forge",
}


PREFIXES = (
    ("live_app_", "UNIFLOW · NAVIGATEUR"),
    ("live_site_", "SITE UNIFLOW"),
    ("mobile_", "SUR UN ÉCRAN DE TÉLÉPHONE"),
    ("desktop_", "SITE UNIFLOW"),
    ("live_", "KERNEL FORGE"),
)


def broll_caption(name):
    """Étiquette courte, vraie pour l'image montrée. Tout ce qui est filmé ici
    vient du WEB : le site, ou l'application dans le navigateur. Rien ne montre
    l'appli Android ni le logiciel de bureau, donc rien ne doit le faire croire."""
    stem = Path(name).name.rsplit(".", 1)[0]
    for pre, head in PREFIXES:
        if stem.startswith(pre):
            tail = PAGES.get(stem[len(pre):], "")
            return f"{head} · {tail}" if tail else head
    return "VUES DU PROJET"


def broll_panel(name):
    """Panneau prêt à coller : l'image entière, jamais recadrée, dans un écran
    aux coins arrondis avec sa légende. Mis en cache, c'est le même à chaque frame."""
    key = ("broll", name)
    if key in _c:
        return _c[key]
    im = load(ASSETS, name).convert("RGBA")
    box = BROLL_BOX_TALL if im.height > im.width else BROLL_BOX
    sc = min(box[0] / im.width, box[1] / im.height)
    w, h = max(1, round(im.width * sc)), max(1, round(im.height * sc))
    big = im.resize((w, h), Image.LANCZOS)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w - 1, h - 1], 18, fill=255)
    big.putalpha(mask)
    d = ImageDraw.Draw(big)
    d.rounded_rectangle([0, 0, w - 1, h - 1], 18, outline=WHITE + (235,), width=4)
    lab, size = broll_caption(name), 20
    while d.textlength(lab, font=font(FB, size)) > w - 58 and size > 14:
        size -= 1
    if d.textlength(lab, font=font(FB, size)) > w - 58:
        lab = lab.split(" · ")[0]
    f = font(FB, size)
    tw = d.textlength(lab, font=f)
    d.rounded_rectangle([14, h - size - 26, 14 + tw + 30, h - 10], 7, fill=(9, 16, 40, 225))
    d.text((29, h - size - 21), lab, font=f, fill=CYAN + (245,))
    _c[key] = big
    return big


def draw_broll(dst, name, p, alpha=1.0):
    """Visuel réel du projet, sur un moniteur suspendu au-dessus du plateau,
    dans le couloir libre entre les deux têtes — jamais sur un personnage."""
    e = ease(min(1, p)) * alpha
    if e <= 0.01:
        return
    g = ease(min(1, p))
    big = broll_panel(name)
    bw, bh = big.width, big.height
    x = (W - bw) // 2
    y = (62 if bh > bw else 74) - int((1 - g) * 40)
    sh = Image.new("RGBA", (bw + 44, bh + 54), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([22, 24, bw + 22, bh + 24], 18, fill=(0, 0, 0, 130))
    dst.alpha_composite(fainted(sh.filter(ImageFilter.GaussianBlur(10)), alpha), (x - 22, y - 18))
    dst.alpha_composite(fainted(big, alpha), (x, y))


def draw_progress(dst, t, total):
    d = ImageDraw.Draw(dst)
    d.rectangle([0, H - 5, W, H], fill=(255, 255, 255, 30))
    d.rectangle([0, H - 5, int(W * t / total), H], fill=ORANGE + (200,))


# ------------------------------------------------------------------- assemblage
LINE_SEED, NSEG, TOTAL = {}, 11, 900.0


def find_beat(beats, t, bi):
    while bi + 1 < len(beats) and beats[bi + 1]["at"] <= t:
        bi += 1
    while bi > 0 and beats[bi]["at"] > t:
        bi -= 1
    return bi


def render_frame(f, tl, beats, bi):
    t = f / FPS
    bi = find_beat(beats, t, bi)
    b = beats[bi]
    kind = b["kind"]
    dst = Image.new("RGBA", (W, H), INK + (255,))

    if kind == "title":
        draw_title(dst, t - b["at"], tl)
    elif kind == "end":
        spec = SHOTS["outro"]
        vw = view(spec, 0.0, 0.0)
        dst.paste(background(spec, vw).convert("RGBA"), (0, 0))
        draw_end(dst, t - b["at"], tl)
    elif kind == "chapter":
        spec = SHOTS[b["shot"]]
        vw = view(spec, 0.0, 0.0)
        dst.paste(background(spec, vw).convert("RGBA"), (0, 0))
        stub = dict(who=b["who"], voice=0.0, pose=b["pose"])
        draw_scene(dst, vw, spec, stub, t - b["at"], -1.0, LINE_SEED.get(b.get("i", 0), 0))
        draw_bug(dst, t, b)
        draw_chapter(dst, b, (t - b["at"]) / b["dur"], NSEG)
    else:
        spec = SHOTS[b["shot"]]
        seed = LINE_SEED.get(b["i"], 0.0)
        bias = 0.0 if b["duo"] else (-16 if b["who"] == "ARCHLORD" else 16) * ease((t - b["at"]) / 2.2)
        vw = view(spec, ease((t - b["at"]) / max(1.0, b["dur"])), bias)
        dst.paste(background(spec, vw).convert("RGBA"), (0, 0))
        wt, vt = t - b["clip_at"], t - b["speech_at"]
        # L'écran du plateau est un élément du décor : il passe derrière les
        # personnages, une main levée peut le traverser sans être coupée.
        if b["broll"]:
            draw_broll(dst, b["broll"], (vt + 0.1) / 0.55,
                       min(1.0, ease((b["voice"] + 0.30 - vt) / 0.5)))
        if b["duo"]:
            bob, tilt, br = motion(wt, True, seed)
            # Les pieds, pas un chiffre en dur : la ligne de sol change d'une
            # plaque à l'autre, et le duo codé à 930 flottait de 38 à 105 px
            # sur les neuf dixièmes du film qui ne se tournent pas dans « wide ».
            draw_figure(dst, vw, (spec["a"][1] + spec["b"][1]) / 2, spec["a"][2],
                        DUAL["pose"],
                        max(spec["a"][3], spec["b"][3]) * DUAL["k"] * br,
                        1.0, bob * 0.55, tilt * 0.35, CYAN)
        else:
            draw_scene(dst, vw, spec, b, wt, vt, seed)
        draw_bug(dst, t, b)
        draw_lower(dst, b["who"], vt, b["voice"])
        draw_subs(dst, b["words"], vt)

    if kind in ("line", "chapter"):
        for w in tl.get("techs", []):
            if w["at"] <= t < w["until"]:
                draw_tech(dst, w, t, spec)
    draw_progress(dst, t, TOTAL)
    return finish(dst, f), bi


def finish(dst, f):
    """Grain et poussière de plateau, en dernier, pour souiller l'image du direct."""
    if (SW, SH) != (W, H):
        dst = dst.convert("RGB").resize((SW, SH), Image.LANCZOS)
    arr = np.asarray(dst.convert("RGB"), np.float32)
    arr += (np.asarray(grain_tiles()[f % 4], np.float32) - 128.0)[:, :, None]
    for px, py, sp, ph in dust():
        yy = int((py - f / FPS * 11 * sp) % SH)
        xx = int((px + 26 * SW / W * math.sin(f / FPS * .5 + ph)) % SW)
        if yy < SH - 3 and xx < SW - 3:
            arr[yy:yy + 3, xx:xx + 3] += 15
    return Image.fromarray(np.clip(arr, 0, 255).astype("uint8"), "RGB")


def stills(tl, beats, times):
    WORK.mkdir(exist_ok=True)
    for s in times:
        f = int(round(s * FPS))
        b = beats[find_beat(beats, f / FPS, 0)]
        img, _ = render_frame(f, tl, beats, 0)
        p = WORK / f"still_{s:07.2f}_{b['kind']}_{b.get('shot', '-')}.png"
        img.save(p)
        print(p.name, flush=True)


def encode(tl, beats, debut, fin, target, audio=None):
    """Encode l'intervalle [debut, fin[ dans `target`.

    Un plan ne dépend que du temps absolu : une partie peut donc être relancée
    seule après une coupure de courant ou de session, sans décaler un pixel de
    l'habillage ni la barre de progression. Les images calculées avant `debut`
    (et jetées) sont l'amorce du fondu : sans elles, un raccord engagé pile à la
    frontière de la partie arrive à l'antenne en coupure franche.
    """
    f0, f1 = int(round(debut * FPS)), int(round(fin * FPS))
    # `out/` n'existe pas dans un clone neuf (git ne stocke pas les dossiers
    # vides) et disk_usage lève une exception sur un chemin absent : la
    # création vient avant la sonde, pas après.
    target.parent.mkdir(parents=True, exist_ok=True)
    besoin = (fin - debut) * (5.2e6 / 8) + 1.2e9
    libre = shutil.disk_usage(target.parent).free
    if libre < besoin:
        sys.exit(f"espace disque insuffisant : {libre / 2**30:.1f} Go libres pour "
                 f"{besoin / 2**30:.1f} Go estimés avant d'écrire {target.name}.")

    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{SW}x{SH}", "-r", str(FPS), "-i", "-"]
    if audio is not None:
        # Le master sort à -21 LUFS, crête à -3,8 dBFS : le seul gain de
        # normalisation le poussait à +1,1 dBFS et 44 523 blocs de trois
        # échantillons collés au plafond ont été mesurés sur la coupe — la voix
        # craque sur chaque syllabe forte. Le limiteur sans niveau automatique
        # tient la PCM à -4 dBFS, et comme l'AAC rend ~3 dB sur une matière déjà
        # bridée, la crête décodée atterrit à -0,9 dBFS, sans un échantillon hors
        # plage. 256k pour ne pas payer en artifacts ce qu'on a gagné en marge.
        cmd += ["-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
                "-af", "volume=4.5dB,"
                       "alimiter=level=disabled:limit=0.63:attack=3:release=120",
                "-c:a", "aac", "-b:a", "256k",
                "-ar", "48000", "-shortest", "-movflags", "+faststart"]
    else:
        cmd += ["-an"]
    # Le grain de plateau coûte très cher à l'encodage : la coupe de quinze
    # minutes sortait à 7 Mbit/s constants en CRF 21, soit 3,2 Go pour une heure
    # à l'heure où le disque en a 5,3 de libres. Le plafond laisse le texte net.
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "23",
            "-maxrate", "5M", "-bufsize", "10M", "-pix_fmt", "yuv420p", str(target)]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    bi, prev_b, prev_rgb = 0, None, None
    t0, ecrites = time.time(), 0
    for f in range(int(round(max(0.0, debut - XFADE) * FPS)), f1):
        t = f / FPS
        nb = beats[find_beat(beats, t, bi)]
        img, bi = render_frame(f, tl, beats, bi)
        if prev_rgb is not None and nb is not prev_b and \
                nb.get("shot") != prev_b.get("shot") and t - nb["at"] < XFADE:
            img = Image.blend(prev_rgb, img, ease((t - nb["at"]) / XFADE))
        prev_b, prev_rgb = nb, img
        if f < f0:
            continue
        try:
            proc.stdin.write(img.tobytes())
        except BrokenPipeError:
            break
        ecrites += 1
        if ecrites % 500 == 0:
            el = max(0.001, time.time() - t0)
            print(f"    {t:7.1f}s   {(f1 - f) / (ecrites / el) / 60:5.1f} min dans la "
                  f"partie   {ecrites / el:4.1f} im/s", flush=True)
    proc.stdin.close()
    code = proc.wait()
    if code or ecrites != f1 - f0:
        sys.exit(f"{target.name} incomplet : {ecrites} images sur {f1 - f0} "
                 f"(ffmpeg code {code}) — relancer la partie.")
    print(f"  {target.name} : {ecrites} images en {(time.time() - t0) / 60:.1f} min",
          flush=True)


def main():
    global SW, SH
    if "--720p" in sys.argv:
        SW, SH = 1280, 720
    tl = json.loads((ROOT / "timeline.json").read_text())
    beats = tl["beats"]
    global TOTAL, NSEG, LINE_SEED
    TOTAL, NSEG = tl["total"], sum(1 for x in beats if x["kind"] == "chapter")
    for n, x in enumerate(b for b in beats if b["kind"] == "line"):
        LINE_SEED[x["i"]] = (n % 7) * 0.9
    for n, x in enumerate([b for b in beats if b["kind"] == "chapter"], 1):
        x["rank"] = n

    if "--stills" in sys.argv:
        k = sys.argv.index("--stills")
        stills(tl, beats, [float(a) for a in sys.argv[k + 1:]])
        return

    limit = None
    if "--seconds" in sys.argv:
        limit = float(sys.argv[sys.argv.index("--seconds") + 1])
    total = tl["total"] if limit is None else min(limit, tl["total"])
    mins = max(1, round(tl["total"] / 60))

    # --debut/--fin : une tranche de l'heure, rendue sans son dans une partie
    # numérotée. Le son n'est posé qu'une fois, au montage final, pour qu'aucune
    # couture de segment ne se voie ni ne s'entende.
    if "--debut" in sys.argv:
        i = sys.argv.index
        encode(tl, beats, float(sys.argv[i("--debut") + 1]),
               min(float(sys.argv[i("--fin") + 1]), total),
               Path(sys.argv[i("--out") + 1]))
    elif "--mux" in sys.argv:
        # Une seule passe vidéo + voix/frise son déjà mixés, avec le gain de
        # normalisation (-21 LUFS mesurés -> -16.5 visés, crête à -2 dBFS).
        encode(tl, beats, 0.0, total,
               OUT / f"UNIFLOW_plateau_{mins:02d}min_{SH}p.mp4",
               ROOT / sys.argv[sys.argv.index("--mux") + 1])
    else:
        encode(tl, beats, 0.0, total,
               OUT / ("video_test.mp4" if limit is not None else "video_only.mp4"))


if __name__ == "__main__":
    main()
